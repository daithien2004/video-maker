"""Thu thập reply từ trang chi tiết comment; chỉ đọc, không đăng hoặc gửi trả lời."""
from __future__ import annotations

import re
from collections import deque
from urllib.parse import urlsplit


def post_id(value) -> str:
    url = value.get("url") if isinstance(value, dict) else value
    match = re.search(r"/post/([\w-]+)", url or "")
    return match.group(1) if match else ""


def safe_thread_url(url: str) -> bool:
    try:
        parsed = urlsplit(url or "")
        return (parsed.scheme == "https" and parsed.netloc in (
            "www.threads.com", "threads.com", "www.threads.net", "threads.net")
            and bool(post_id(url)))
    except ValueError:
        return False


def focused_replies(url, items):
    """Chỉ card dưới bài đang mở, bỏ tổ tiên phía trên và bài gợi ý."""
    target = post_id(url)
    if not target:
        return None
    relevant = [c for c in items if "related" not in (c.get("pagelet") or "").lower()]
    focused = next((i for i, c in enumerate(relevant) if post_id(c) == target), None)
    if focused is None:
        return None
    focus_area = relevant[focused].get("pagelet") or ""
    return [c for c in relevant[focused + 1:]
            if post_id(c) != target and (
                (c.get("pagelet") or "").startswith("threads_post_page")
                if focus_area.startswith("threads_post_page")
                else not focus_area or c.get("pagelet") == focus_area)]


def _cycle(child, parent, records):
    visited = {child}
    while parent and parent in records:
        if parent in visited:
            return True
        visited.add(parent)
        parent = records[parent].get("parent_id")
    return False


def _ancestor(ancestor, node, records):
    seen = set()
    while node and node in records and node not in seen:
        if node == ancestor:
            return True
        seen.add(node)
        node = records[node].get("parent_id")
    return False


def collect(roots, original_post, read_thread, *, max_depth=2, max_pages=20,
            max_replies=100, progress=None, min_likes=0, per_parent=None):
    """read_thread(url) -> cards hoặc None nếu không tìm được comment đang mở.

    Quan hệ parent_id là ngữ cảnh của trang chi tiết đã quan sát, không suy đoán từ like.
    read_thread được tiêm để kiểm thử mà không cần đăng nhập hay mạng.
    """
    root_id = post_id(original_post)
    records, order = {}, []
    for index, item in enumerate(roots):
        key = post_id(item) or f"local-{index}"
        if key not in records:
            records[key] = {**item, "id": key, "parent_id": root_id or None,
                            "parent_url": original_post.get("url"), "depth": 1,
                            "relation": "post_context"}
            order.append(key)
    pending = deque((key, 0) for key in order if records[key].get("replies"))
    visited = set()
    stats = dict(pages=0, replies_added=0, failures=0, skipped_no_url=0,
                 limited=False, depth_limit=False, disabled=False,
                 min_likes=min_likes, per_parent=per_parent, replies_below_min_likes=0)
    while pending and stats["pages"] < max_pages:
        parent, level = pending.popleft()
        if parent in visited:
            continue
        visited.add(parent)
        source = records[parent]
        level = max(level, source.get("depth", 1) - 1)
        if level >= max_depth:
            stats["depth_limit"] = True
            continue
        if not safe_thread_url(source.get("url")):
            stats["skipped_no_url"] += 1
            continue
        if progress:
            progress(stats["pages"], max_pages, source)
        stats["pages"] += 1
        try:
            items = read_thread(source["url"])
        except Exception:
            stats["failures"] += 1
            continue
        if items is None:
            stats["failures"] += 1
            continue
        candidates = {}
        for item in items:
            child = post_id(item)
            if not child or child in (root_id, parent) or _cycle(child, parent, records):
                continue
            if child not in candidates or (item.get("likes") or 0) > (candidates[child].get("likes") or 0):
                candidates[child] = item
        eligible = []
        for item in candidates.values():
            if (item.get("likes") or 0) < min_likes:
                stats["replies_below_min_likes"] += 1
            else:
                eligible.append(item)
        eligible.sort(key=lambda c: (c.get("likes") or 0, c.get("replies") or 0), reverse=True)
        if per_parent is not None:
            eligible = eligible[:max(0, per_parent)]
        for item in eligible:
            child = post_id(item)
            if (not child or child in (root_id, parent) or _cycle(child, parent, records)):
                continue
            fresh = child not in records
            if fresh and stats["replies_added"] >= max_replies:
                stats["limited"] = True
                break
            previous = records.get(child, {})
            # Một card xuất hiện ở nhiều trang: giữ ngữ cảnh cha cụ thể hơn nếu quan sát được.
            parent_id = previous.get("parent_id")
            if (parent_id and parent_id != root_id and parent_id != parent
                    and not _ancestor(parent_id, parent, records)):
                continue
            merged = {**previous, **item, "id": child, "parent_id": parent,
                      "parent_url": source["url"], "parent_handle": source.get("handle"),
                      "depth": source.get("depth", 1) + 1,
                      "relation": "comment_thread_context"}
            merged["datetime"] = item.get("datetime") or previous.get("datetime")
            merged["likes"] = max(item.get("likes") or 0, previous.get("likes") or 0)
            if len(previous.get("text") or "") > len(item.get("text") or ""):
                merged["text"] = previous["text"]
            records[child] = merged
            if fresh:
                order.append(child)
                stats["replies_added"] += 1
            if merged.get("replies") and child not in visited:
                pending.append((child, level + 1))
        if stats["limited"]:
            break
    stats["limited"] = stats["limited"] or bool(pending)
    return [records[key] for key in order], stats


# Chỉ nút mở hội thoại, không khớp nút soạn/gửi "Reply / Trả lời".
EXPAND_REPLIES = re.compile(
    r"^(?:view|see|show|xem|hiển thị)\b.*(?:repl(?:y|ies)|trả lời|phản hồi|chuỗi)", re.I)


def expand_reply_buttons(page, limit=8):
    controls = page.get_by_role("button", name=EXPAND_REPLIES)
    for index in reversed(range(min(controls.count(), limit))):
        try:
            control = controls.nth(index)
            if control.is_visible():
                control.click(timeout=1500)
                page.wait_for_timeout(350)
        except Exception:
            continue
