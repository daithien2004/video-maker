"""Sinh caption Facebook Reels theo skill `facebook-reels-caption` (không cần mạng/LLM).

Skill quy định: hook ≤ ~125 ký tự đứng một mình vẫn hiểu, thân ngắn 2–5 dòng, đúng
một CTA, 0–5 hashtag cụ thể (tránh #viral #reels #xuhuong…), kèm 1–2 dòng chữ overlay.

Ở đây chỉ dùng lại chính chữ trong bài gốc — không bịa số liệu, giá, cam kết. Ba phương
án khác nhau ở cách mở đầu và CTA, đúng định dạng đầu ra của skill.
"""
from __future__ import annotations

import re
import unicodedata

HOOK_LIMIT = 125
MAX_TAGS = 5
FIXED_TAGS = ("fyp", "xuhuong", "funny")

# Hashtag chung chung: skill khuyên bỏ, chỉ giữ tag cụ thể của ngách/nội dung.
GENERIC_TAGS = {
    "viral", "virals", "viralvideo", "reels", "reel", "reelsfb", "fb", "facebook",
    "fyp", "foryou", "foryoupage", "explore", "xuhuong", "xuhuong2026", "thinhhanh",
    "trend", "trending", "trendingreels", "threads", "thread", "videoviral",
    "facebookreels", "fbreels", "reelsfacebook", "video", "highlight",
    "hay", "hot", "moinhat", "shorts", "shortvideo", "content", "creator",
}
GENERIC_TAGS.difference_update(FIXED_TAGS)

CTA_COMMENT = [
    "Bạn nghĩ sao về điều này? Comment cho mình biết 👇",
    "Bạn đã từng gặp chuyện này chưa?",
    "Bạn đồng ý không? Nói mình nghe ở dưới 👇",
]
CTA_SHARE = [
    "Gửi cho người cần thấy điều này.",
    "Lưu lại để xem khi cần.",
]
CTA_DEBATE = [
    "Bạn đồng ý hay thấy khác? Comment cho mình biết 👇",
    "Bạn nghĩ sao? Tranh luận vui ở dưới nhé 👇",
]

_CONTRAST = re.compile(
    r"\b(nhưng|tuy nhiên|thay vì|không phải|chưa chắc|sự thật|bí mật|sai lầm|"
    r"hầu hết|đa số|ngược lại|ít ai|không ai)\b", re.I)
_NUMBER = re.compile(r"\d")
_LEAD = re.compile(r"^(mình|tôi|tớ|tui|em|anh|chị|ông|bà)\b", re.I)

TOPICS = {
    "Ẩm thực": ("ẩm thực|món ăn|món ngon|nấu ăn|ăn vặt|quán ăn|nhà hàng|đồ ăn|cà phê",
                "amthuc monngon reviewdoanuong", "Món này có hợp khẩu vị của bạn không?"),
    "Du lịch": ("du lịch|chuyến đi|khách sạn|phượt|checkin|check-in|tham quan",
                "dulich checkin dulichvietnam", "Bạn muốn ghé nơi này cùng ai?"),
    "Thời trang / làm đẹp": ("thời trang|làm đẹp|trang điểm|skincare|makeup|phối đồ|dưỡng da",
                "thoitrang lamdep", "Bạn thích phong cách nào nhất?"),
    "Fitness / sức khỏe": ("sức khỏe|tập gym|thể hình|yoga|giảm cân|tập luyện|workout|dinh dưỡng",
                "suckhoe", "Bạn quan tâm nhất đến điều gì khi chăm sóc sức khỏe?"),
    "Bán hàng / kinh doanh": ("bán hàng|kinh doanh|khởi nghiệp|marketing|khách hàng|doanh nghiệp",
                "kinhdoanh marketing", "Theo bạn, điều gì quan trọng nhất trong câu chuyện này?"),
    "Hài / giải trí": ("hài hước|gây cười|buồn cười|giải trí|meme|chuyện cười",
                "haihuoc giaitri", "Chi tiết nào khiến bạn thấy thú vị nhất?"),
    "Mẹo / kiến thức": ("mẹo|kiến thức|hướng dẫn|khoa học|lịch sử|vật lý|ánh sáng|vì sao|phát minh|sinh vật|oxy|quang hợp|thiên nhiên|trái đất",
                "kienthuc hocmoingay", "Bạn muốn tìm hiểu thêm điều gì về chủ đề này?"),
    "Thú cưng": ("thú cưng|con mèo|chú mèo|mèo con|con chó|chú chó|cún|pets|nuôi mèo|nuôi chó",
                "thucung pets", "Thú cưng nhà bạn có từng làm vậy chưa?"),
    "Gia đình / cuộc sống": ("gia đình|cuộc sống|tâm sự|nuôi con|em bé|vợ chồng|cha mẹ|tình yêu|hàng xóm",
                "giadinh cuocsong", "Bạn đã từng có trải nghiệm tương tự chưa?"),
}
TOPIC_CHOICES = ["Tự nhận diện", *TOPICS]


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
                   if unicodedata.category(c) != "Mn")


def detect_topic(text: str, topic: str = "Tự nhận diện") -> str:
    if topic in TOPICS:
        return topic
    plain = _plain(text)
    scores = {name: sum(bool(re.search(r"\b" + re.escape(_plain(word)) + r"\b", plain))
                        for word in rule[0].split("|")) for name, rule in TOPICS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "Chưa rõ chủ đề"


# --------------------------------------------------------------------------- cắt câu
def units(text: str) -> list[str]:
    """Tách bài thành từng đơn vị câu/đoạn ngắn, bỏ dòng trống và ký tự trang trí."""
    out: list[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        for part in re.split(r"(?<=[.!?…])\s+", line):
            part = part.strip(" -–—•*_")
            if len(part) >= 2:
                out.append(part)
    return out


def shorten(text: str, limit: int = HOOK_LIMIT) -> str:
    """Cắt ở ranh giới từ, thêm '…' nếu bị cắt. Bỏ dấu hai chấm cuối câu teaser."""
    s = " ".join((text or "").split())
    s = re.sub(r"\s*/\s*", " / ", s).strip()
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-–—") + "…"
    return s.rstrip(" :;,.-–—") or s


def _score(unit: str) -> int:
    s = 0
    if _NUMBER.search(unit):
        s += 3
    if _CONTRAST.search(unit):
        s += 2
    if "?" in unit:
        s += 1
    if 30 <= len(unit) <= HOOK_LIMIT:
        s += 2
    elif len(unit) > HOOK_LIMIT:
        s += 1
    if unit.isupper():
        s -= 2
    return s


def pick(us: list[str], used: set[int] | None = None) -> int | None:
    """Chỉ số câu 'đáng làm hook' nhất trong các câu chưa dùng."""
    used = used or set()
    order = [i for i in sorted(range(len(us)), key=lambda i: (-_score(us[i]), i))
             if i not in used]
    return order[0] if order else None


# --------------------------------------------------------------------------- hashtag
def tag_list(tags: str) -> list[str]:
    out: list[str] = []
    for raw in re.split(r"[\s,;]+", tags or ""):
        t = raw.strip().lstrip("#")
        if not t or not re.fullmatch(r"\w+", t) or len(t) > 24:
            continue
        if t.lower() not in {o.lower() for o in out}:
            out.append(t)
    return out


def generic_tag(tag: str) -> bool:
    return tag.lstrip("#").lower() in GENERIC_TAGS


def hashtags(content: str, text: str, tags: str, limit: int = MAX_TAGS,
             topic: str = "Tự nhận diện") -> str:
    """Tag do người dùng nhập, tag nguồn và tag chủ đề; không dùng slug thư mục."""
    out: list[str] = list(FIXED_TAGS)
    for t in tag_list(tags):
        if not generic_tag(t):
            out.append(t)
    for t in tag_list(" ".join("#" + m for m in re.findall(r"#(\w+)", text or ""))):
        if not generic_tag(t):
            out.append(t)
    # Tên thư mục xuất thường chứa timestamp; không dùng làm hashtag.
    rule = TOPICS.get(detect_topic(text, topic))
    if rule:
        out.extend(tag_list(rule[1]))
    seen: list[str] = []
    for t in out:
        if t.lower() not in {s.lower() for s in seen}:
            seen.append(t)
    return " ".join("#" + t for t in seen[:limit])


# --------------------------------------------------------------------------- 3 phương án
def _block(*parts: str) -> str:
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def make_options(text: str, content: str = "", tags: str = "",
                 extra: list[str] | None = None, topic: str = "Tự nhận diện") -> list[dict]:
    """3 phương án caption theo skill: ngắn gọn · kể chuyện · câu hỏi/tranh luận.

    `extra` là các comment nổi bật (nếu bài gốc quá ngắn) để có thêm chất liệu —
    vẫn chỉ dùng chữ có thật trong video, không bịa.
    """
    def clean(value):
        return re.sub(r"#\w+", "", value or "").strip()

    main = units(clean(text))
    alts = [u for u in units(clean("\n".join(extra or []))) if u not in main]
    if not main and not alts:
        return []
    detected = detect_topic(text, topic)
    tags_line = hashtags(content, text, tags, topic=topic)
    cta = (TOPICS[detected][2] if detected in TOPICS
           else "Điều gì trong câu chuyện này khiến bạn chú ý nhất?")
    used: set[int] = set()

    i1 = pick(main) if main else None
    if i1 is not None:
        used.add(i1)
        hook1 = shorten(main[i1])
    else:
        i1, hook1 = None, shorten(alts[0])

    i2 = pick(main, used)
    if i2 is not None:
        used.add(i2)
    alt_pool = [a for a in alts if shorten(a) != hook1]
    alt2 = alt_pool[0] if alt_pool else ""
    opener2 = first_clause(alt2, 180) if alt2 else (shorten(main[i2]) if i2 is not None else hook1)
    body2 = hook1 if opener2 != hook1 else ""

    i3 = pick(main, used)
    core3 = shorten(main[i3], 100) if i3 is not None else ""
    if not core3:
        core3 = shorten(alt_pool[1], 100) if len(alt_pool) > 1 else ""
    if not core3:
        core3 = hook1
    hook3 = core3

    def lead(unit: str) -> str:
        """Bỏ 'Mình/Tôi…' ở đầu để câu không bị lệch giọng khi lên Page."""
        return _LEAD.sub("", unit).strip() or unit

    options = [
        {
            "title": "1. Ngắn gọn, đi thẳng vào ý",
            "caption": _block(hook1, "" if "?" in hook1 else cta, tags_line),
            "body": hook1,
        },
        {
            "title": "2. Kể chuyện / đồng cảm",
            "caption": _block(lead(opener2), short_body(body2),
                              "" if "?" in opener2 + body2 else CTA_SHARE[0], tags_line),
            "body": opener2,
        },
        {
            "title": "3. Câu hỏi / tranh luận nhẹ",
            "caption": _block(lead(hook3), "" if "?" in hook3 else CTA_DEBATE[0], tags_line),
            "body": hook3,
        },
    ]
    for o in options:
        o["topic"] = detected
        o["overlay"] = overlay(o["body"])
        o["check"] = checklist(o["caption"])
    return options


def short_body(text: str) -> str:
    """Dòng thân: giữ nguyên ý, chỉ rút gọn nếu quá dài."""
    return first_clause(text, 220)


def first_clause(text: str, limit: int = 220) -> str:
    """Rút gọn nhưng cắt ở dấu câu (ưu tiên cuối câu) để không đứt giữa ý."""
    s = " ".join((text or "").split())
    if len(s) <= limit:
        return s
    cut = s[:limit]
    for m in reversed(list(re.finditer(r"[.!?…,;:]", cut))):
        if m.start() >= limit // 2:
            return cut[:m.start()].rstrip(" ,;:.-–—") + "…"
    return cut.rsplit(" ", 1)[0].rstrip(" ,;:.-–—") + "…"


def overlay(body: str) -> str:
    """1 dòng chữ hiển thị trên video: 8–10 từ đầu của hook, không viết hoa toàn bộ."""
    words = " ".join((body or "").split()).split()
    line = " ".join(words[:9]).rstrip(" ,;:.-–—…")
    return line[:48].rstrip()


def checklist(caption: str) -> dict:
    """Tự kiểm tra theo bước 7 của skill."""
    first = next((ln for ln in (caption or "").splitlines() if ln.strip()), "")
    tags = re.findall(r"#\w+", caption or "")
    low = (caption or "").lower()
    return {
        "hook_len": len(first),
        "hook_ok": 0 < len(first) <= 140,
        "tags": len(tags),
        "tags_ok": len(tags) <= MAX_TAGS,
        "has_cta": "?" in (caption or "") or any(
            w in low for w in ("comment", "gửi cho", "lưu lại", "theo dõi")),
        "generic": [t for t in tags if generic_tag(t)],
    }


def report(opt: dict) -> str:
    """Markdown: chữ overlay + checklist + cảnh báo."""
    c = opt.get("check") or {}
    bits = [f"**Chủ đề:** {opt.get('topic') or '—'}",
            f"**Chữ overlay gợi ý:** {opt.get('overlay') or '—'}"]
    warn: list[str] = []
    if not c.get("hook_ok"):
        warn.append(f"hook {c.get('hook_len')} ký tự — nên ≤ 140")
    if not c.get("tags_ok"):
        warn.append(f"{c.get('tags')} hashtag — skill khuyên ≤ {MAX_TAGS}")
    if c.get("generic"):
        warn.append("hashtag chung chung: " + " ".join(c["generic"]))
    if not c.get("has_cta"):
        warn.append("chưa thấy CTA/câu hỏi")
    bits.append("✅ Hook ngắn, có CTA, hashtag gọn." if not warn
                else "⚠ " + "; ".join(warn))
    return "\n\n".join(bits)
