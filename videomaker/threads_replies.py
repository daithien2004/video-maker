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


class ThreadPage(list):
    """Reply cards plus the explicit ancestor strip of a comment detail page."""
    def __init__(self, replies, ancestors=()):
        super().__init__(replies)
        self.ancestors = list(ancestors)


def observed_thread(url, items, original_post):
    replies = focused_replies(url, items)
    if replies is None:
        return None
    target = post_id(url)
    focus = next(item for item in items if post_id(item) == target)
    index = items.index(focus)
    # Threads puts the parent chain in pagelet_0, the focused comment in pagelet_1.
    # Do not treat arbitrary cards above the focus as ancestors on unfamiliar layouts.
    ancestors = [item for item in items[:index] if item.get('pagelet') == 'threads_post_page_0']
    if (not ancestors or post_id(ancestors[0]) != post_id(original_post) or
            focus.get('pagelet') != 'threads_post_page_1'):
        ancestors = []
    return ThreadPage(replies, ancestors + [focus] if ancestors else [])


INDENT_REPLY_MIN = 8   # reply thụt vào ~40px so với card cha; 8px đủ để bỏ qua lệch vẽ


def mark_parents(cards):
    """Gắn `parent_hint` cho từng card dựa vào thụt lề trên trang bài gốc.

    Threads thụt reply vào so với card cha, nên card lùi vào là con của card gần nhất
    phía trên có thụt lề nhỏ hơn. Chỉ là gợi ý lúc gom card; bước đọc trang chi tiết
    vẫn chỉnh lại quan hệ nếu trang đó nói khác.
    """
    lefts = [c['left'] for c in cards if isinstance(c.get('left'), (int, float))]
    if not lefts:
        return
    base = min(lefts)
    stack: list[tuple[float, str]] = []
    for card in cards:
        card['parent_hint'] = None
        left = card.get('left')
        if not isinstance(left, (int, float)):
            continue
        indent = left - base
        while stack and stack[-1][0] >= indent:
            stack.pop()
        key = post_id(card)
        if indent >= INDENT_REPLY_MIN and stack:
            card['parent_hint'] = stack[-1][1]
        if key:
            stack.append((indent, key))


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


def select_conversations(comments, original_post, *, top=20, per_parent=2, max_depth=1):
    """Giữ thứ tự Threads đang hiển thị, chỉ cắt số lượng.

    Comment chính lấy `top` mục đầu tiên theo thứ tự trên trang, mỗi cha lấy
    `per_parent` reply đầu tiên; reply đứng ngay sau cha nó. Không xếp lại theo like
    hay thời gian — Threads đã sắp sẵn.
    """
    root_id = post_id(original_post)
    by_id = {item['id']: item for item in comments}
    children = {}
    roots = []
    for item in comments:
        parent = item.get('parent_id')
        if not parent or parent == root_id or parent not in by_id:
            roots.append(item)
        else:
            children.setdefault(parent, []).append(item)
    if top > 0:
        roots = roots[:top]
    result, visited = [], set()
    def visit(item, depth):
        if item['id'] in visited:
            return
        visited.add(item['id'])
        result.append({**item, 'depth': depth + 1})
        if depth >= max_depth:
            return
        replies = children.get(item['id'], [])
        if per_parent is not None:
            replies = replies[:max(0, per_parent)]
        for reply in replies:
            visit(reply, depth + 1)
    for root in roots:
        visit(root, 0)
    return result


def collect(roots, original_post, read_thread, *, max_depth=2, max_pages=20,
            max_replies=100, progress=None, per_parent=None, root_limit=None):
    """read_thread(url) -> cards hoặc None nếu không tìm được comment đang mở.

    Quan hệ parent_id là ngữ cảnh của trang chi tiết đã quan sát, không suy đoán từ like.
    read_thread được tiêm để kiểm thử mà không cần đăng nhập hay mạng.
    """
    root_id = post_id(original_post)
    records, order = {}, []
    for index, item in enumerate(roots):
        key = post_id(item) or f"local-{index}"
        if key in records:
            continue
        hint = item.get("parent_hint")
        parent = records.get(hint) if hint and hint != key else None
        if parent:
            records[key] = {**item, "id": key, "parent_id": hint,
                            "parent_url": parent.get("url") or original_post.get("url"),
                            "parent_handle": parent.get("handle"),
                            "depth": parent.get("depth", 1) + 1,
                            "relation": "post_page_indent"}
        else:
            records[key] = {**item, "id": key, "parent_id": root_id or None,
                            "parent_url": original_post.get("url"), "depth": 1,
                            "relation": "post_context"}
        order.append(key)
    # Đọc trang chi tiết comment chính trước rồi mới tới reply: ngân sách trang có hạn.
    pending = deque(sorted(
        ((key, records[key].get("depth", 1) - 1) for key in order
         if root_limit is not None or records[key].get("replies")),
        key=lambda entry: entry[1]))
    visited = set()
    stats = dict(pages=0, replies_added=0, failures=0, skipped_no_url=0,
                 limited=False, depth_limit=False, disabled=False,
                 per_parent=per_parent)
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
        ancestry = getattr(items, 'ancestors', [])
        for ancestor, child_item in zip(ancestry, ancestry[1:]):
            ancestor_id, child_id = post_id(ancestor), post_id(child_item)
            if not ancestor_id or not child_id or child_id == root_id or _cycle(child_id, ancestor_id, records):
                continue
            previous = records.get(child_id, {})
            records[child_id] = {**child_item, **previous, 'id': child_id,
                                 'parent_id': ancestor_id, 'parent_url': ancestor.get('url'),
                                 'parent_handle': ancestor.get('handle'),
                                 'depth': records.get(ancestor_id, {}).get('depth', 0) + 1,
                                 'relation': 'detail_ancestry'}
            if child_id not in order:
                order.append(child_id)
                if records[child_id].get('replies'):
                    pending.append((child_id, max(0, records[child_id]['depth'] - 1)))
        source = records[parent]
        level = max(level, source.get('depth', 1) - 1)
        if level >= max_depth:
            stats['depth_limit'] = True
            continue
        candidates = {}
        for item in items:
            child = post_id(item)
            if not child or child in (root_id, parent) or _cycle(child, parent, records):
                continue
            if child not in candidates or (item.get("likes") or 0) > (candidates[child].get("likes") or 0):
                candidates[child] = item
        # Correct every known card's parent before enforcing final selection quotas.
        # Otherwise replies already visible on the main page stay mislabeled as roots.
        existing = []
        eligible = []
        for item in candidates.values():
            if post_id(item) in records:
                existing.append(item)
            else:
                eligible.append(item)
        # Giữ thứ tự card trên trang: Threads đã sắp sẵn, không xếp lại theo like.
        if per_parent is not None:
            eligible = eligible[:max(0, per_parent)]
        for item in existing + eligible:
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
            if previous.get('relation') == 'detail_ancestry' and parent_id != parent:
                continue
            if (parent_id and parent_id != root_id and parent_id != parent
                    and not _ancestor(parent_id, parent, records)):
                continue
            merged = {**previous, **item, "id": child, "parent_id": parent,
                      "parent_url": source["url"], "parent_handle": source.get("handle"),
                      "depth": source.get("depth", 1) + 1,
                      "relation": previous.get('relation') if previous.get('relation') == 'detail_ancestry' else "comment_thread_context"}
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
    result = [records[key] for key in order]
    if root_limit is not None:
        result = select_conversations(result, original_post, top=root_limit,
                                      per_parent=per_parent, max_depth=max_depth)
        initial_ids = {post_id(item) for item in roots}
        stats['replies_added'] = sum(item['id'] not in initial_ids and item['depth'] > 1 for item in result)
        stats['selected_roots'] = sum(item['depth'] == 1 for item in result)
        stats['selected_replies'] = sum(item['depth'] > 1 for item in result)
    return result, stats


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
