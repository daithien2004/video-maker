"""Quản lý bản nháp thứ tự comment, không sửa dữ liệu hay xóa file nguồn."""
from __future__ import annotations

import math
from copy import deepcopy
from datetime import datetime, timezone, timedelta


def comment_time(comment: dict) -> float | None:
    value = comment.get("datetime")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        date = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def chronological(comments, newest=False):
    def key(comment):
        stamp = comment_time(comment)
        return (stamp is None, (-stamp if newest else stamp) if stamp is not None else 0)
    ordered = sorted(comments, key=key)
    ids = {c.get("id") for c in comments if c.get("id")}
    children = {}
    for index, comment in enumerate(ordered):
        parent = comment.get("parent_id")
        children.setdefault(parent if parent in ids else None, []).append((index, comment))
    out, seen = [], set()
    def visit(index, comment):
        if index in seen:
            return
        seen.add(index)
        out.append(comment)
        for child_index, child in children.get(comment.get("id"), []) if comment.get("id") else []:
            visit(child_index, child)
    for index, comment in children.get(None, []):
        visit(index, comment)
    for index, comment in enumerate(ordered):  # dữ liệu cũ/lỗi chu trình không làm mất comment
        visit(index, comment)
    return out


def display_time(comment):
    stamp = comment_time(comment)
    return (datetime.fromtimestamp(stamp, timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M")
            if stamp is not None else "—")


def table_rows(result: dict) -> list[list]:
    return [[i, False, i, "@" + c.get("handle", "?"), c.get("likes") or 0,
             c.get("text") or "", display_time(c)]
            for i, c in enumerate(result.get("comments") or [], 1)]


def validate_rows(rows, count: int) -> list[list]:
    rows = rows or []
    if len(rows) != count:
        raise ValueError("Danh sách vừa thay đổi. Hãy tải lại bảng comment.")
    seen = set()
    for row in rows:
        if len(row) != 7:
            raise ValueError("Bảng comment không đúng định dạng.")
        try:
            identity, rank = float(row[0]), float(row[2])
        except (TypeError, ValueError):
            raise ValueError("Thứ tự phải là số lớn hơn 0.") from None
        if (not math.isfinite(identity) or not identity.is_integer()
                or not 1 <= identity <= count or int(identity) in seen):
            raise ValueError("Mã comment không hợp lệ hoặc bị trùng.")
        if not math.isfinite(rank) or rank <= 0:
            raise ValueError("Thứ tự phải là số lớn hơn 0.")
        if not isinstance(row[1], bool):
            raise ValueError("Dùng ô đánh dấu để chọn comment cần bỏ.")
        seen.add(int(identity))
    return sorted([list(r) for r in rows], key=lambda r: float(r[2]))


def move_row(rows, selected, direction: int) -> list[list]:
    ordered = validate_rows(rows, len(rows or []))
    index = next((i for i, row in enumerate(ordered) if row[0] == selected), None)
    if index is None:
        raise ValueError("Bấm vào hàng comment muốn di chuyển trước.")
    other = index + direction
    if 0 <= other < len(ordered):
        ordered[index], ordered[other] = ordered[other], ordered[index]
    for rank, row in enumerate(ordered, 1):
        row[2] = rank
    return ordered


def sort_likes(rows) -> list[list]:
    ordered = validate_rows(rows, len(rows or []))
    ordered.sort(key=lambda r: -float(r[4] or 0))
    for rank, row in enumerate(ordered, 1):
        row[2] = rank
    return ordered


def sort_time(result, rows, newest=False):
    comments = result.get("comments") or []
    ordered = validate_rows(rows, len(comments))
    decorated = [{**comments[int(row[0]) - 1], "_row": row} for row in ordered]
    ordered = [comment["_row"] for comment in chronological(decorated, newest)]
    for rank, row in enumerate(ordered, 1):
        row[2] = rank
    return ordered


def apply_draft(result: dict, rows) -> dict:
    comments = result.get("comments") or []
    ordered = validate_rows(rows, len(comments))
    updated = deepcopy(result)
    updated["comments"] = [deepcopy(comments[int(r[0]) - 1]) for r in ordered if not r[1]]
    wanted = [result["post"].get("image")] + [c.get("image") for c in updated["comments"]]
    images = {item.get("rel"): item for item in updated.get("images") or []}
    updated["images"] = [images[rel] for rel in wanted if rel in images]
    updated["stats"] = {**updated.get("stats", {}), "comments_used": len(updated["comments"])}
    return updated
