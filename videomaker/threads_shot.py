"""Chụp post Threads + comment nhiều like thành ảnh minh họa cho video.

Ví dụ:
    python -m videomaker.threads_shot "https://www.threads.com/@uidasoda/post/De9Ttiem_12" --content la-phoi-trai-dat --tag post --top 5

Kết quả trong assets/illus/<content>/<tag>/:
    01-post-uidasoda.png                  card bài gốc
    02-cmt-<handle>.png                   comment nhiều like (số like nằm trong json)
    threads.json                          text + like + link để viết kịch bản đọc lại
    script.txt                            kịch bản đọc lại, mỗi nhịp đã gắn đúng ảnh

Hai chế độ ảnh (--mode):
    shot  ảnh chụp nguyên card của Threads (thật, nhưng chỉ ~638px nên hơi mềm khi lên 1080)
    card  tự dựng lại card ở đúng 1080px từ dữ liệu đã bóc (nét, sạch, không nút thừa)
    auto  post có ảnh/clip -> shot, post chỉ có chữ -> card (mặc định)

Nếu bị chặn đăng nhập / muốn thấy reply lồng dưới comment: bấm nút
"🔑 Đăng nhập Threads" trong tab Threads của app (hoặc chạy `--login`), đăng nhập tay
trong cửa sổ vừa mở — app tự phát hiện và lưu phiên ở work/threads_state.json.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import time
import unicodedata
from . import comment_manager as cm
from . import threads_replies as tr
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .paths import APP_DIR, configure_browser_temp
ILLUS_DIR = APP_DIR / "assets" / "illus"
FONT_DIR = APP_DIR / "assets" / "fonts"
WORK_DIR = APP_DIR / "work"
STATE_FILE = WORK_DIR / "threads_state.json"
TMP_DIR = WORK_DIR / "threads_tmp"   # ảnh chụp tạm, dọn sau mỗi lần chạy

# console Windows mặc định cp1252 khi bị pipe -> in tiếng Việt sẽ lỗi
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OUT_W = 1080
VIEW_W = 1280
VIEW_H = 1600
SCROLL_PX, SCROLL_WAIT = 1400, 900

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

# Chữ giao diện Threads, không phải nội dung bài viết
UI_NOISE = {
    "author", "tác giả", "follow", "theo dõi", "see translation", "xem bản dịch",
    "translate", "dịch", "more", "xem thêm", "edited", "đã chỉnh sửa", "·", "pinned", "đã ghim",
    "this content is unavailable", "nội dung này không khả dụng",
    "bạn không xem được nội dung này", "you can't view this content",
}

# Khi đã đăng nhập, Threads chèn thêm nút giao diện vào đúng vùng chữ của card:
# "Hàng đầu" (kiểu sắp xếp), "Xem hoạt động", "Trả lời <tên>..." (ô soạn reply)…
# Nếu không lọc, mấy chữ này bị đọc lên như nội dung bài.
UI_NOISE_RE = re.compile(
    r"^(?:"
    r"hàng đầu|mới nhất|phổ biến|xem hoạt động|sắp xếp|xem thêm|xem bớt|"
    r"xem bản dịch|xem bản gốc|ẩn bản dịch|"
    r"viết bình luận|thêm bình luận|tạo thread mới|tạo bài viết|"
    r"theo dõi|đang theo dõi|đã chỉnh sửa|chỉnh sửa|"
    r"trả lời\s+@?[\w.]*\s*\.\.\.|trả lời(?: bài viết)?"
    r")\s*$",
    re.I)

# Comment rác / seeding: có link quảng cáo thì bỏ
JUNK = re.compile(r"(https?://|www\.|\.com\b|\.vn\b|\.net\b|t\.me/|zalo|telegram)", re.I)

# Dải gợi ý của Threads khi bài gắn thẻ Meta AI ("Nhắc đến @meta.ai trong bài viết
# để nhận câu trả lời ngay tại đây", bản EN "Mention @meta …") — chữ nền tảng chèn
# kèm card, không phải lời tác giả; lọc ở khâu bóc dữ liệu.
META_AI_HINT_RE = re.compile(
    r"^(?:nhắc đến|mention)\s*@?meta(?:\.ai)?\b.{0,120}$", re.I | re.S)

COUNT_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*([KMB])?$", re.I)
AGE_RE = re.compile(
    r"^(?:·\s*)?\d+\s*(?:giây|phút|giờ|ngày|tuần|tháng|năm|s|m|h|d|w|y)$", re.I)

# "26 thg 10", "26/10/2026", "26-10", "26 tháng 10, 2026", "Oct 26, 2026", "Thứ Hai"
_MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|thg|tháng)"
DATE_RE = re.compile(
    rf"^(?:·\s*)?(?:"
    rf"\d{{1,2}}\s*[/.\-]\s*\d{{1,2}}(?:\s*[/.\-]\s*\d{{2,4}})?"
    rf"|\d{{1,2}}\s*{_MONTHS}\s*\d{{0,2}}(?:,?\s*\d{{4}})?"
    rf"|{_MONTHS}\s*\d{{1,2}}(?:,?\s*\d{{4}})?"
    rf"|\d{{4}}-\d{{2}}-\d{{2}}"
    rf"|\d{{1,2}}:\d{{2}}(?:\s*[APap][Mm])?"
    rf"|(?:thứ\s*(?:hai|ba|tư|năm|sáu|bảy)|chủ\s*nhật|mon|tue|wed|thu|fri|sat|sun)"
    rf")$",
    re.I)

EXTRACT_JS = r"""
() => {
  const SEL = '[data-pressable-container="true"]';
  // chỉ card ngoài cùng, bỏ card lồng bên trong (bài được quote / reply kèm)
  const cards = [...document.querySelectorAll(SEL)]
    .filter(c => !c.parentElement || !c.parentElement.closest(SEL));
  const clean = s => (s || '').replace(/\u200b/g, '').trim();
  // chỉ lấy phần tử thuộc đúng card này, không lấy của card lồng bên trong
  const own = (el, c) => el.closest(SEL) === c;

  cards.forEach((c, i) => c.setAttribute('data-shot', String(i)));

  return cards.map(c => {
    const hrefs = [...c.querySelectorAll('a[href^="/@"]')].filter(a => own(a, c))
      .map(a => a.getAttribute('href') || '');
    const timeEl = [...c.querySelectorAll('time')].find(t => own(t, c));
    const timeLink = timeEl ? timeEl.closest('a') : null;
    const avatar = [...c.querySelectorAll('img')]
      .find(i => own(i, c) && /profile picture|ảnh đại diện/i.test(i.alt || ''));
    // emoji của Threads cũng là <img> nhưng rất nhỏ -> chỉ tính ảnh/clip thật
    const media = [...c.querySelectorAll('img, video')].filter(m => own(m, c) && (
      m.tagName === 'VIDEO' ||
      ((m.naturalWidth >= 120 || m.getBoundingClientRect().width >= 120)
       && m !== avatar && !/profile picture|ảnh đại diện|emoji/i.test(m.alt || ''))));
    const readSpan = s => {
      if (!s.querySelector('img[alt]')) return clean(s.innerText);
      const copy = s.cloneNode(true);
      copy.querySelectorAll('img[alt]').forEach(img =>
        img.replaceWith(document.createTextNode(img.getAttribute('alt') || '')));
      copy.querySelectorAll('br').forEach(br => br.replaceWith(document.createTextNode('\n')));
      return clean(copy.textContent);
    };
    const spanNodes = [...c.querySelectorAll('span[dir="auto"]')].filter(s => own(s, c));
    const spans = spanNodes.map(readSpan);
    const bodySpans = spanNodes.filter(s => {
      const action = s.closest('button,[role="button"]');
      const link = s.closest('a[href]');
      const profile = link && /^\/@[^/]+\/?$/.test(link.getAttribute('href') || '');
      return (!action || action === c || !c.contains(action)) && !s.closest('time') && !profile
        && !(timeLink && timeLink.contains(s)) && !(timeEl && s.contains(timeEl));
    }).map(readSpan);

    return {
      handle: (hrefs[0] || '').replace('/@', ''),
      postHref: hrefs.find(h => h.includes('/post/')) || '',
      // vùng chứa: "threads_post_page_*" = bài đang mở + reply của nó;
      // "…related…" = post khác do Threads gợi ý ở cuối trang (không phải comment)
      pagelet: (c.closest('[data-pagelet]') || {getAttribute: () => ''}).getAttribute('data-pagelet') || '',
      datetime: timeEl ? timeEl.getAttribute('datetime') : null,
      spans,
      body_spans: bodySpans,
      isPinned: spans.some(s => /^(pinned|đã ghim)$/i.test(s)),
      btns: [...c.querySelectorAll('[role="button"]')].filter(b => own(b, c))
        .map(b => clean(b.innerText)).filter(Boolean),
      avatar: avatar ? avatar.src : null,
      media: media.length,
      media_urls: [...new Set(media.filter(m => m.tagName === 'IMG')
        .map(m => m.currentSrc || m.src).filter(Boolean))],
      isAuthor: spans.some(s => /^(·\s*)?(Author|Tác giả)$/i.test(s)),
    };
  });
}
"""

CLEAN_JS = r"""
css => {
  document.querySelectorAll('[role="dialog"]').forEach(d => d.remove());
  const s = document.createElement('style');
  s.textContent = css;
  document.head.appendChild(s);
}
"""

CLEAN_CSS = """
[role="banner"], header, nav, [role="navigation"], [role="dialog"] { display: none !important; }
html, body { background: #ffffff !important; }
* { scrollbar-width: none !important; }
*::-webkit-scrollbar { display: none !important; }
"""

# Lớp phủ "đăng nhập để xem tiếp": một div rgba(0,0,0,.7) trùm kín màn hình. Nó không
# phải dialog nên CLEAN_CSS không dẹp được -> ảnh chụp card bị tối/đen thui.
# Escape đóng hộp thoại, đoạn JS dưới dọn nốt lớp phủ nếu còn.
OVERLAY_JS = r"""
() => {
  const W = innerWidth, H = innerHeight;
  let n = 0;
  for (const el of document.querySelectorAll('div, section, aside')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'absolute') continue;
    const r = el.getBoundingClientRect();
    if (r.width < W * 0.9 || r.height < H * 0.9) continue;
    const m = cs.backgroundColor.match(/^rgba?\(([^)]+)\)/);
    if (!m) continue;
    const p = m[1].split(',').map(Number);
    const a = p.length > 3 ? p[3] : 1;
    if (a >= 0.35 && p[0] < 80 && p[1] < 80 && p[2] < 80) { el.remove(); n++; }
  }
  document.querySelectorAll('[role="dialog"]').forEach(d => d.remove());
  return n;
}
"""


# --------------------------------------------------------------------------- tiện ích
def parse_count(s: str | None) -> int:
    """'4.1K' -> 4100, '55,6K' -> 55600, '1.2M' -> 1200000."""
    m = COUNT_RE.match((s or "").strip().replace(",", "."))
    if not m:
        return 0
    mult = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[(m.group(2) or "").upper()]
    try:
        return int(float(m.group(1).replace(",", ".")) * mult)
    except ValueError:
        return 0


def is_count(s: str) -> bool:
    return bool(COUNT_RE.match((s or "").strip().replace(",", ".")))


def is_dateish(s: str, iso: str | None = None) -> bool:
    """Chuỗi này là ngày giờ / tuổi bài (đã hiện ở header card, không đọc lên)."""
    t = (s or "").strip().strip("·").strip()
    if not t:
        return False
    if AGE_RE.match(t) or DATE_RE.match(t):
        return True
    if re.match(r"^(?:·\s*)?(?:hôm qua|hôm nay|vừa xong|vừa đây|just now|yesterday|today)$", t, re.I):
        return True
    if iso:
        try:
            from datetime import datetime
            d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            return False
        day, month, year = d.day, d.month, d.year
        forms = {
            f"{day}/{month}/{year}", f"{day}/{month}/{year % 100}", f"{day:02d}/{month:02d}/{year}",
            f"{day:02d}/{month:02d}/{year % 100}", f"{day}-{month}-{year}", f"{year}-{month:02d}-{day:02d}",
            f"{day} thg {month}", f"{day} tháng {month}", f"{day} thg {month}, {year}",
            f"{day} tháng {month}, {year}", f"{month}/{day}/{year}",
        }
        return t.lstrip("· ").strip() in forms
    return False


def slug(s: str, limit: int = 24) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:limit] or "x"


def vn_int(n: int) -> str:
    return f"{n:,}".replace(",", ".") if n else "0"


def reading_minutes(text: str) -> float:
    """Đọc tiếng Việt ~180 từ/phút, để biết một post dài bao nhiêu giây hình."""
    return round(len(text.split()) / 180, 1)


def card_from_raw(raw: dict) -> dict | None:
    """Biến dữ liệu thô của một card thành {handle, text, likes, replies, ...}."""
    handle = raw.get("handle") or ""
    if not handle:
        return None

    nums = [parse_count(b) for b in (raw.get("btns") or []) if is_count(b)][:4]
    likes = nums[0] if nums else 0
    replies = nums[1] if len(nums) > 1 else 0
    reposts = nums[2] if len(nums) > 2 else 0
    shares = nums[3] if len(nums) > 3 else 0

    # bỏ handle / tuổi bài / số đếm / chữ giao diện, phần còn lại là nội dung
    body: list[str] = []
    structured_body = "body_spans" in raw
    for s in (raw.get("body_spans") if structured_body else raw.get("spans")) or []:
        t = (s or "").strip()
        if not t or t.lower() in UI_NOISE or UI_NOISE_RE.match(t) or META_AI_HINT_RE.match(t):
            continue
        if t.lstrip("@").lower() == handle.lower():
            continue
        if not structured_body and AGE_RE.match(t):
            continue
        if not structured_body and is_dateish(t, raw.get("datetime")):
            continue
        if not structured_body and is_count(t) and t in (raw.get("btns") or []):
            continue
        body.append(t)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(body)).strip()
    # Threads chèn số trang ("1 / 2") vào cuối khối chữ của bài nằm trong thread /
    # carousel — không phải nội dung, không đọc lên và không vẽ vào card.
    text = re.sub(r"(?:\u00a0|\s*\n\s*)\d{1,3}\s*\n?\s*/\s*\n?\s*\d{1,3}\s*$", "", text).strip()
    # Một số client gửi Unicode dạng TỔ HỢP (chữ + dấu rời, NFD) — Pillow vẽ dấu thành
    # ký tự riêng ("Mo`" thay vì "Mờ"). Ghép về dạng dựng sẵn (NFC) trước khi vẽ/đọc.
    text = unicodedata.normalize("NFC", text)
    if not text and not raw.get('media'):
        return None

    return {
        "handle": handle,
        "text": text,
        "likes": likes,
        "replies": replies,
        "reposts": reposts,
        "shares": shares,
        "datetime": raw.get("datetime"),
        "url": f"https://www.threads.com{raw['postHref']}" if raw.get("postHref") else None,
        "has_media": bool(raw.get("media")),
        "media_urls": raw.get('media_urls') or [],
        "is_author": bool(raw.get("isAuthor")),
        "is_pinned": bool(raw.get("isPinned")),
        "avatar": raw.get("avatar"),
        "pagelet": raw.get("pagelet") or "",
    }


def is_junk(text: str) -> bool:
    t = text.strip().lower()
    if t in {"this content is unavailable", "nội dung này không khả dụng",
             "bạn không xem được nội dung này"}:
        return True
    # Không loại câu ngắn/emoji/link ở bước lấy nguồn: chúng có thể có nghĩa trong hội thoại.
    return False


def split_post(url: str, items: list[dict]) -> tuple[dict | None, list[dict]]:
    """Tách bài đang mở khỏi reply của nó.

    Trang post của Threads còn hiện các post khác ("gợi ý cho bạn", `data-pagelet` chứa
    `related`). Nếu gom hết card trên trang thì sẽ lẫn comment của bài khác — chỉ giữ
    card nằm trong vùng `threads_post_page_*` (bài đang mở + reply bên dưới).
    """
    post_id = url.rstrip("/").split("/post/")[-1].split("?")[0]

    def related(i: dict) -> bool:
        return "related" in (i.get("pagelet") or "")

    pool = [i for i in items if (i.get("pagelet") or "").startswith("threads_post_page")]
    if not pool:                      # Threads đổi tên vùng -> dùng tất cả, trừ post gợi ý
        pool = items
    pool = [i for i in pool if not related(i)] or pool

    post = next((i for i in pool if post_id and post_id in (i.get("url") or "")), None)
    if post is None and pool:
        post = pool[0]

    seen: set[tuple[str, str]] = set()
    comments: list[dict] = []
    for c in pool:
        if c is post or is_junk(c["text"]):
            continue
        key = (c["handle"], c["text"][:80] or tr.post_id(c) or str(c.get("media_urls")))
        if key in seen:
            continue
        seen.add(key)
        comments.append(c)
    comments.sort(key=lambda c: c["likes"], reverse=True)
    return post, comments


# --------------------------------------------------------------------------- dựng card bằng Pillow
def _font(size: int, bold: bool = False):
    from PIL import ImageFont
    names = (["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold
             else ["segoeui.ttf", "arial.ttf"])
    for folder in (FONT_DIR, Path(r"C:\Windows\Fonts")):
        for n in names:
            p = folder / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if cur and draw.textlength(trial, font=font) > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def _heart(draw, x: float, y: float, s: float, color):
    r = s * 0.28
    draw.ellipse([x, y, x + 2 * r, y + 2 * r], fill=color)
    draw.ellipse([x + s - 2 * r, y, x + s, y + 2 * r], fill=color)
    draw.polygon([(x, y + r * 1.2), (x + s, y + r * 1.2), (x + s / 2, y + s)], fill=color)


def _bubble(draw, x: float, y: float, s: float, color):
    draw.rounded_rectangle([x, y, x + s, y + s * 0.72], radius=s * 0.22, fill=color)
    draw.polygon([(x + s * 0.18, y + s * 0.66), (x + s * 0.34, y + s * 0.66),
                  (x + s * 0.12, y + s * 0.95)], fill=color)


def _fmt_date(iso: str | None) -> str:
    """'2026-10-26T12:42:26.000Z' -> '26/10/2026' (chuỗi khác giữ nguyên)."""
    t = (iso or "").strip()
    if not t:
        return ""
    try:
        from datetime import datetime
        d = datetime.fromisoformat(t.replace("Z", "+00:00"))
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    except ValueError:
        return t[:10]


def download_card_media(request, urls):
    """Download image attachments with the same authenticated browser context."""
    from PIL import Image, ImageOps
    from urllib.parse import urlsplit
    photos = []
    for url in list(dict.fromkeys(urls))[:10]:
        if not isinstance(url, str):
            continue
        parsed = urlsplit(url)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or not any(host == domain or host.endswith('.' + domain)
                for domain in ('fbcdn.net', 'cdninstagram.com', 'fbsbx.com', 'threads.com', 'threads.net')):
            continue
        try:
            response = request.get(url, timeout=15_000)
            if not response.ok:
                continue
            payload = response.body()
            if len(payload) > 20_000_000:
                continue
            with Image.open(io.BytesIO(payload)) as photo:
                if photo.width * photo.height > 40_000_000:
                    continue
                photo = ImageOps.exif_transpose(photo).convert('RGB')
                photo.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                photo.save(output, format='PNG')
                photos.append(output.getvalue())
        except Exception:
            continue
    return photos


def render_card(item: dict, out: Path, canvas: tuple[int, int] | None,
                avatar_png: bytes | None, max_chars: int = 900,
                ident: str = "full") -> Path:
    """Vẽ card phong cách Threads, nền trắng, rộng 1080.

    `canvas = (1080, H)` → card đúng H, chữ tự co giãn cho vừa (chế độ cũ).
    `canvas = None`      → card cao theo nội dung: chữ ~52px cố định, khung ngắn
    lại khi bài ngắn, tối đa 900px khi bài dài.

    `ident`: avatar  = ảnh đại diện + chữ "Threads" (mặc định) ·
    full    = avatar + tên tài khoản · no-avatar = ẩn ảnh đại diện, giữ tên ·
    anon    = ẩn cả avatar lẫn tên (chỉ ghi "Bài đăng/Bình luận trên Threads").
    """
    from PIL import Image, ImageDraw
    from .threads_text import EmojiDraw, prepare_emojis
    prepare_emojis([item['text'], item.get('handle', '')])

    pad, head = 56, 100
    inner_w = OUT_W - pad * 2
    f_name, f_small = _font(44, True), _font(32)
    show_avatar = ident in {"full", "avatar"}
    probe = EmojiDraw(ImageDraw.Draw(Image.new("RGB", (10, 10))))
    text = item["text"]
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].rstrip() + "…"

    ch = canvas[1] if canvas else 0
    header_top = pad
    body_top = header_top + head + 44
    footer_h = 40
    footer_top = (ch - pad - footer_h) if ch else 0

    def metrics(txt: str, size: int) -> tuple[list[str], int, int, int]:
        """Trả về (dòng, chiều cao dòng, lệch đỉnh mực, chiều cao mực thật).

        Canh giữa theo MỰC CHỮ chứ không theo hộp dòng — nếu không, phần leading
        dưới dòng cuối bị tính vào và card trông lệch xuống.
        """
        f = _font(size)
        lines = _wrap(probe, txt, f, inner_w)
        lh = int(size * 1.38)
        tops, bots = [], []
        for i, ln in enumerate(lines):
            if not ln.strip():
                continue
            bb = probe.textbbox((0, 0), ln, font=f)
            tops.append(i * lh + bb[1])
            bots.append(i * lh + bb[3])
        if not tops:
            return lines, lh, 0, size
        return lines, lh, min(tops), max(bots) - min(tops)

    if ch:
        avail = max(80, footer_top - 44 - body_top)
        # Chọn cỡ chữ LỚN NHẤT còn vừa khung: bài ngắn -> chữ to lấp đầy card,
        # bài dài -> tự hạ dần. Trước đây lấy mốc đầu tiên vừa nên bài ngắn bị
        # chữ nhỏ + trống trên dưới.
        size = 36
        lines, line_h, ink_top, ink_h = metrics(text, size)
        for cand in (36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84,
                     88, 92, 98, 104, 110, 118, 126, 136, 146, 158):
            l, lh, t, h = metrics(text, cand)
            if h > avail:
                break
            size, lines, line_h, ink_top, ink_h = cand, l, lh, t, h
        while ink_h > avail and len(text) > 160:
            text = text[: int(len(text) * 0.9)].rsplit(" ", 1)[0].rstrip() + "…"
            lines, line_h, ink_top, ink_h = metrics(text, size)
        # còn thừa nhiều thì giãn dòng (tối đa +0.40 cỡ chữ) cho đỡ trống
        if len(lines) > 1:
            delta = min(int(size * 0.40), max(0, avail - ink_h) // (len(lines) - 1))
            if delta > 0:
                line_h += delta
                ink_h += delta * (len(lines) - 1)
        y = body_top + max(0, (avail - ink_h) // 2) - ink_top
    else:                     # canvas = none: card thấp đúng theo nội dung
        # Khung không còn cố định 1080×900 nữa: chữ giữ cỡ ~52px (dễ đọc, đồng đều
        # giữa các card), card cao bao nhiêu thì cắt bấy nhiêu. Bài dài quá 900px
        # mới hạ cỡ chữ, cuối cùng mới cắt bớt.
        cap = 640
        size = 52
        lines, line_h, ink_top, ink_h = metrics(text, size)
        ch = body_top + ink_h + 44 + footer_h + pad
        while ch > cap and size > 30:
            size -= 2
            lines, line_h, ink_top, ink_h = metrics(text, size)
            ch = body_top + ink_h + 44 + footer_h + pad
        while ch > cap and len(text) > 160:
            text = text[: int(len(text) * 0.9)].rsplit(" ", 1)[0].rstrip() + "…"
            lines, line_h, ink_top, ink_h = metrics(text, size)
            ch = body_top + ink_h + 44 + footer_h + pad
        footer_top = ch - pad - footer_h
        y = body_top - ink_top

    photos = []
    for payload in item.get('_media_pngs', []):
        with Image.open(io.BytesIO(payload)) as photo:
            from PIL import ImageOps
            photo = ImageOps.exif_transpose(photo).convert('RGB')
            ratio = min(inner_w / photo.width, 600 / photo.height)
            photos.append(photo.resize((max(1, round(photo.width * ratio)),
                                        max(1, round(photo.height * ratio))), Image.Resampling.LANCZOS))
    media_y = footer_top
    if photos:
        extra = sum(photo.height + 24 for photo in photos)
        ch += extra
        footer_top += extra
    img = Image.new("RGB", (OUT_W, ch), (255, 255, 255))
    d = EmojiDraw(ImageDraw.Draw(img))
    f_body = _font(size)

    # header: avatar (hoặc vòng tròn trung tính) + nhãn + ngày
    ax, ay = pad, header_top
    d.ellipse([ax, ay, ax + head, ay + head], fill=(238, 238, 238))
    if show_avatar and avatar_png:
        try:
            av = Image.open(io.BytesIO(avatar_png)).convert("RGB").resize((head, head))
            mask = Image.new("L", (head, head), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, head - 1, head - 1], fill=255)
            img.paste(av, (int(ax), int(ay)), mask)
        except Exception:
            pass
    if not (show_avatar and avatar_png):
        glyph = "@"
        gf = _font(54, True)
        gw = d.textlength(glyph, font=gf)
        d.text((ax + (head - gw) / 2, ay + head / 2 - 36), glyph, font=gf, fill=(150, 150, 150))

    tx = ax + head + 26
    if ident == "avatar":
        name, name_fill = "Threads", (150, 150, 150)
    elif ident == "anon":
        name = "Bài đăng trên Threads" if item.get("kind") == "post" else "Bình luận trên Threads"
        name_fill = (0, 0, 0)
    else:
        name, name_fill = item["handle"], (0, 0, 0)
    d.text((tx, ay + 2), name, font=f_name, fill=name_fill)
    d.text((tx, ay + 58), _fmt_date(item.get("datetime")), font=f_small, fill=(115, 115, 115))

    for line in lines:
        d.text((pad, y), line, font=f_body, fill=(0, 0, 0))
        y += line_h

    for photo in photos:
        img.paste(photo, ((OUT_W - photo.width) // 2, media_y))
        media_y += photo.height + 24

    # footer dính mép dưới: like + bình luận
    fy = footer_top
    _heart(d, pad, fy, footer_h, (255, 48, 64))
    d.text((pad + 54, fy - 4), vn_int(item["likes"]), font=f_small, fill=(115, 115, 115))
    bx = pad + 54 + d.textlength(vn_int(item["likes"]), font=f_small) + 56
    _bubble(d, bx, fy + 2, 36, (115, 115, 115))
    d.text((bx + 50, fy - 4), vn_int(item["replies"]), font=f_small, fill=(115, 115, 115))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def _hook(draw, x: float, y: float, s: float, color):
    """Mũi tên ↳ vẽ tay: đứng xuống rồi rẽ phải — đánh dấu "đang trả lời cái này"."""
    w = max(4, round(s * 0.14))
    drop = s * 0.62
    draw.line([(x, y), (x, y + drop)], fill=color, width=w)
    draw.line([(x, y + drop), (x + s * 0.72, y + drop)], fill=color, width=w)
    draw.polygon([(x + s * 0.66, y + drop - s * 0.20), (x + s * 0.66, y + drop + s * 0.20),
                  (x + s, y + drop)], fill=color)


def reply_context(source: dict, image: str) -> str:
    """The exact parent snippet used in both Threads frame previews and video beats."""
    comments = source.get('comments') or []
    item = next((comment for comment in comments if comment.get('image') == image), None)
    if not item or (item.get('depth') or 1) < 2:
        return ''
    items = [source.get('post') or {}] + list(comments)
    by_id = {record['id']: record for record in items if record.get('id')}
    parent = by_id.get(item.get('parent_id')) or {}
    handle = parent.get('handle') or item.get('parent_handle') or ''
    if not handle:
        return ''
    snippet = ' '.join((parent.get('text') or '').split())
    return f'@{handle}: {snippet[:200]}' if snippet else f'@{handle}'


def has_media(source: dict, image: str) -> bool:
    """Mục này có ảnh đính kèm không: bài gốc hoặc comment kèm ảnh."""
    entry = next((i for i in source.get('images') or [] if i.get('rel') == image), None)
    if entry and entry.get('kind') == 'post':
        return bool((source.get('post') or {}).get('media_urls'))
    comment = next((c for c in source.get('comments') or [] if c.get('image') == image), None)
    return bool(comment and comment.get('media_urls'))


def parse_context(context: str) -> tuple[str, str]:
    """'@cha: trích đoạn' -> ('cha', 'trích đoạn'); không mở đầu bằng '@' thì cả chuỗi là trích."""
    s = " ".join((context or "").split())
    if s.startswith("@"):
        handle, sep, rest = s.partition(":")
        return handle.lstrip("@").strip(), rest.strip() if sep else ""
    return "", s


def style_card(clip: Path, radius: int, shadow: int, out: Path, *, padding: int = 0,
               padding_sides: tuple | None = None) -> Path:
    """Bo góc và thêm bóng đổ cho ảnh card Threads trước khi ghép vào preview/video."""
    sides = tuple(max(0, min(200, int(value))) for value in
                  (padding_sides if padding_sides is not None else (padding,) * 4))
    if radius <= 0 and shadow <= 0 and not any(sides):
        return clip
    from PIL import Image, ImageDraw, ImageFilter
    src = Image.open(clip).convert("RGBA")
    if any(sides):
        top, right, bottom, left = sides
        # Border-box padding: preserve the card's bounds and the image's aspect ratio.
        left, right = min(left, (src.width - 1) // 2), min(right, (src.width - 1) // 2)
        top, bottom = min(top, (src.height - 1) // 2), min(bottom, (src.height - 1) // 2)
        inner_w, inner_h = src.width - left - right, src.height - top - bottom
        scale = min(inner_w / src.width, inner_h / src.height)
        content = src.resize((max(1, round(src.width * scale)), max(1, round(src.height * scale))), Image.Resampling.LANCZOS)
        padded = Image.new("RGBA", src.size, "white")
        padded.alpha_composite(content, (left + (inner_w - content.width) // 2,
                                         top + (inner_h - content.height) // 2))
        src = padded
    if radius > 0:
        mask = Image.new("L", src.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, src.width - 1, src.height - 1), radius=radius, fill=255)
        src.putalpha(mask)

    if shadow <= 0:
        out.parent.mkdir(parents=True, exist_ok=True)
        src.save(out)
        return out

    strength = max(0.0, min(1.0, shadow / 100))
    blur = 4 + round(strength * 20)
    offset_y = 3 + round(strength * 15)
    # Blur on the full transparent canvas, so the rounded silhouette has a soft
    # falloff outside the card instead of being clipped to a rectangular tile.
    pad = blur * 3 + offset_y
    canvas_size = (src.width + pad * 2, src.height + pad * 2)
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

    silhouette = src.getchannel("A")
    for spread, shift, opacity in (
        (blur, offset_y, round(30 + strength * 65)),
        (max(1, blur // 3), max(1, offset_y // 3), round(15 + strength * 30)),
    ):
        shadow_mask = Image.new("L", canvas_size, 0)
        shadow_mask.paste(silhouette, (pad, pad + shift))
        shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(spread))
        shadow_mask = shadow_mask.point(lambda value: round(value * opacity / 255))
        shadow_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        shadow_layer.putalpha(shadow_mask)
        canvas = Image.alpha_composite(canvas, shadow_layer)
    canvas.alpha_composite(src, (pad, pad))

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


def context_card(clip: Path, context: str, out: Path, *, box_w: int = OUT_W,
                 max_h: int = 640) -> Path:
    """Ghép khung ngữ cảnh cha (↳ + tối đa 2 dòng trích) lên TRÊN ảnh reply.

    Video ẩn danh (card không hiện tên tài khoản) nên khung chỉ vẽ mũi tên ↳ với
    trích đoạn comment cha, KHÔNG vẽ tên — phần '@tên:' trong ngữ cảnh bị bỏ qua.
    Ảnh cha và con vẫn được lưu riêng; khung này chỉ ghép lúc dựng video, nên bỏ bớt
    reply hay đổi comment cha đều không phải chụp lại ảnh. Ảnh reply quá cao được thu
    lại cho cả cụm vừa khung `max_h` (đáy ảnh vẫn nằm ở cùng một đường như card thường).
    """
    from PIL import Image, ImageDraw

    _handle, snippet = parse_context(context)
    if not snippet:
        return clip                 # chỉ có tên / rỗng -> không có gì để nối ↳
    reply = Image.open(clip).convert("RGB")
    if reply.width != box_w:
        reply = reply.resize((box_w, max(1, round(reply.height * box_w / reply.width))),
                             Image.LANCZOS)

    indent, gap, pad = 72, 20, 26          # thụt lề trái như reply trong app Threads
    f_text = _font(34)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    card_w = box_w - indent - 16
    hook_w, line_h = 44, int(34 * 1.32)

    text_w = card_w - pad * 2 - hook_w
    wrapped = _wrap(probe, snippet, f_text, text_w)
    shown = wrapped[:2]
    if len(wrapped) > 2 and shown:
        shown[-1] = shown[-1].rstrip() + "…"
    card_h = pad + line_h * len(shown) + 24

    avail = max(80, max_h - card_h - gap)  # cụm quá cao thì co ảnh reply, giữ đáy card
    if reply.height > avail:
        reply = reply.resize((max(1, round(reply.width * avail / reply.height)),
                              max(1, avail)), Image.LANCZOS)

    canvas = Image.new("RGB", (box_w, card_h + gap + reply.height), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([indent, 0, indent + card_w, card_h], radius=18, fill=(241, 243, 245))
    tx = indent + pad
    ty = pad
    _hook(d, tx, ty + (line_h - 30) // 2 + 2, 30, (110, 115, 125))
    for ln in shown:
        d.text((tx + hook_w, ty), ln, font=f_text, fill=(70, 70, 70))
        ty += line_h

    canvas.paste(reply, ((box_w - reply.width) // 2, card_h + gap))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


# Ảnh chụp nguyên card vẫn lộ tên tài khoản ở header. Với --ident avatar (mặc định) ta
# ẩn đúng link tên, giữ avatar và giờ đăng; nội dung + avatar vẫn là ảnh thật.
HIDE_NAME_JS = r"""
() => {
  const SEL = '[data-pressable-container="true"]';
  const own = (el, c) => el.closest(SEL) === c;
  const dateish = t => /^(?:·\s*)?(?:(\d+\s*(?:giây|phút|giờ|ngày|tuần|tháng|năm|s|m|h|d|w|y))\b|\d{1,2}\s*[/.\-]\s*\d{1,2}|(?:thg|tháng)\s*\d+|(?:hôm qua|hôm nay|vừa xong|yesterday|today)\b)/i.test(t);
  let n = 0;
  for (const c of document.querySelectorAll('[data-shot]')) {
    for (const a of c.querySelectorAll('a[href^="/@"]')) {
      if (!own(a, c) || a.querySelector('img')) continue;
      const t = (a.innerText || '').replace(/\s+/g, ' ').trim();
      if (!t || dateish(t)) continue;
      if (t.length <= 40) { a.style.display = 'none'; n++; }
      break;                      // chỉ tên ở header; mention trong nội dung giữ nguyên
    }
  }
  return n;
}
"""


# Trang bài post nhét thêm thanh sắp xếp ("Hàng đầu · Xem hoạt động") và ô soạn trả lời
# của chính mình vào card -> ảnh chụp lộ chúng. Ẩn hai khối đó, giữ nguyên khung card.
HIDE_POST_CHROME_JS = r"""
(el) => {
  const inner = el.firstElementChild || el;
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const SORT = /^(?:Hàng đầu|Top|Sắp xếp|Xem hoạt động|For you|Following)\b/i;
  const COMPOSER = /Trường văn bản trống|Empty text field|Đính kèm file phương tiện|Thêm ảnh GIF|Mở rộng công cụ soạn|Attach media|Add a GIF|Expand composer/i;
  let n = 0;
  for (const kid of [...inner.children]) {
    const txt = norm(kid.innerText);
    const meta = [...kid.querySelectorAll('[aria-label],[title],[placeholder]')]
      .map(x => (x.getAttribute('aria-label') || '') + ' ' + (x.getAttribute('title') || '')
                + ' ' + (x.getAttribute('placeholder') || '')).join(' | ');
    const isSort = !kid.querySelector('img[srcset],video') && SORT.test(txt) && txt.length < 60;
    const isComposer = COMPOSER.test(meta) || /^(?:Trả lời|Reply)\s/i.test(txt);
    if (isSort || isComposer) { kid.style.display = 'none'; n++; }
  }
  // dải gợi ý Meta AI ("Nhắc đến @meta.ai … ngay tại đây") chèn dưới card -> ẩn trước khi chụp
  for (const el of inner.querySelectorAll('div,span')) {
    const t = norm(el.innerText);
    if (!t || t.length > 160) continue;
    if (!/^(?:nhắc đến|mention)\s*@?meta(?:\.ai)?\b/i.test(t)) continue;
    el.style.display = 'none';
    n++;
  }
  // "1 / 2" của carousel / thread: hộp nhỏ nằm cạnh chữ hoặc đè lên ảnh
  for (const el of inner.querySelectorAll('div,span')) {
    const t = norm(el.innerText);
    if (!/^\d{1,3}\s*\/\s*\d{1,3}$/.test(t)) continue;
    const r = el.getBoundingClientRect();
    if (r.width > 160 || r.height > 48) continue;
    if (el.querySelector('img,video')) continue;
    const p = el.parentElement;
    const beside = p && norm(p.innerText).length > t.length + 2;
    const overMedia = !!el.closest('div,span') &&
      !!el.parentElement?.querySelector('img,video');
    if (beside || overMedia) { el.style.display = 'none'; n++; }
  }
  return n;
}
"""


# --------------------------------------------------------------------------- cào + chụp trong 1 phiên
def dismiss_overlays(page) -> None:
    """Đóng hộp thoại đăng nhập + dẹp lớp phủ tối để ảnh chụp không bị đen."""
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        page.evaluate(OVERLAY_JS)
    except Exception:
        pass


LOGIN_COOKIES = {"sessionid", "sessionid_threads", "ds_user_id"}
# Cookie mà cả khách chưa đăng nhập cũng có -> không tính là phiên
GUEST_COOKIES = {"csrftoken", "ig_did", "dpr", "mid", "datr", "wd", "ps_l", "ps_n"}


def _threads_auth_cookies(cookies) -> list[dict]:
    """Cookie riêng của threads.com mà khách không có = đã đăng nhập.

    Đăng nhập qua popup Instagram chỉ đặt cookie ở .instagram.com — threads.com vẫn là
    khách (bài vẫn hiện "Đăng nhập hoặc đăng ký Threads" và chỉ trả một phần reply).
    """
    return [c for c in cookies
            if c.get("value") and "threads.com" in (c.get("domain") or "")
            and c["name"] not in GUEST_COOKIES]


def _state_cookies() -> list[dict]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("cookies") or []
    except Exception:
        return []


def session_status() -> str:
    """Một dòng trạng thái phiên đăng nhập để hiện trong app / CLI."""
    if not STATE_FILE.exists():
        return ("**Chưa đăng nhập Threads.** Khách chỉ thấy một phần reply — comment "
                "lồng dưới một comment khác sẽ bị ẩn. Bấm **🔑 Đăng nhập Threads** một lần.")
    cookies = _state_cookies()
    n = len(cookies)
    when = datetime.fromtimestamp(STATE_FILE.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
    if not _threads_auth_cookies(cookies):
        return (f"⚠ **Phiên đã lưu ({n} cookie, {when}) nhưng threads.com vẫn là khách** — "
                f"chỉ có cookie Instagram. Bấm **Xoá phiên** rồi **🔑 Đăng nhập Threads** lại, "
                f"đăng nhập **trên chính trang threads.com** và chờ trang quay về feed.")
    return (f"✅ **Đã có phiên đăng nhập Threads** ({n} cookie, lưu {when}) — "
            f"comment lồng sẽ được lấy đủ.")


def _login_prompt(page) -> bool:
    """Trang còn hiện lời mời đăng nhập = vẫn là khách."""
    try:
        return bool(page.evaluate(
            "() => /Đăng nhập hoặc đăng ký Threads|Đăng nhập bằng tên người dùng"
            "|Log in with username|Log in or sign up for Threads/.test(document.body.innerText)"))
    except Exception:
        return False


def wait_for_login(page, ctx, timeout: float = 300, progress=None) -> bool:
    """Chờ đăng nhập *trên threads.com* rồi lưu phiên.

    Đăng nhập qua popup Instagram chỉ đặt cookie ở .instagram.com — phải chờ threads.com
    tự đặt cookie phiên của nó, nếu không bài vẫn bị coi là khách.
    """
    t0 = time.time()
    cookie_since = None
    reloaded = False
    ig_only = False
    while time.time() - t0 < timeout:
        try:
            if page.is_closed():
                return False
            cookies = ctx.cookies()
            if _threads_auth_cookies(cookies):
                if cookie_since is None:
                    cookie_since = time.time()
                if not reloaded:
                    # nạp lại threads.com để chắc chắn phiên đã được nhận
                    reloaded = True
                    try:
                        page.goto("https://www.threads.com/", wait_until="domcontentloaded",
                                  timeout=60_000)
                        page.wait_for_timeout(3500)
                    except Exception:
                        pass
                    cookies = ctx.cookies()
                # phiên thật = trang không còn lời mời đăng nhập (hoặc cookie đã bền 12s)
                if _threads_auth_cookies(cookies) and (
                        not _login_prompt(page) or time.time() - cookie_since > 12):
                    WORK_DIR.mkdir(parents=True, exist_ok=True)
                    ctx.storage_state(path=str(STATE_FILE))
                    if progress:
                        try:
                            progress(1.0, desc="Đã lưu phiên đăng nhập")
                        except Exception:
                            pass
                    return True
            else:
                reloaded = False
            ig_only = any(c["name"] in LOGIN_COOKIES and c.get("value")
                          and "instagram.com" in (c.get("domain") or "") for c in cookies)
            page.wait_for_timeout(1200)
        except Exception:
            return False        # người dùng đóng cửa sổ
        if progress:
            try:
                left = max(0, int(timeout - (time.time() - t0)))
                desc = ("Đã đăng nhập Instagram — chờ threads.com hoàn tất…" if ig_only
                        else f"Chờ đăng nhập… còn {left}s")
                progress(min(0.95, (time.time() - t0) / timeout), desc=desc)
            except Exception:
                pass
    return False


def save_login(timeout: float = 240, progress=None) -> Path:
    """Mở cửa sổ trình duyệt để đăng nhập tay, tự phát hiện và lưu vào work/threads_state.json."""
    configure_browser_temp()
    from playwright.sync_api import sync_playwright

    ok = False
    ig_seen = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--window-size=1280,900"])
        ctx = browser.new_context(no_viewport=True, locale="vi-VN",
                                  color_scheme="light", user_agent=UA)
        page = ctx.new_page()
        try:
            page.goto("https://www.threads.com/", wait_until="domcontentloaded", timeout=60_000)
            ok = wait_for_login(page, ctx, timeout=timeout, progress=progress)
            try:
                ig_seen = any(c["name"] in LOGIN_COOKIES and c.get("value")
                              and "instagram.com" in (c.get("domain") or "")
                              for c in ctx.cookies())
            except Exception:
                pass
        finally:
            try:
                ctx.close()
            except Exception:
                pass
            browser.close()
    if not ok:
        if ig_seen:
            raise RuntimeError(
                "Đã thấy đăng nhập Instagram nhưng **threads.com chưa nhận phiên**. Bấm lại nút "
                "**🔑 Đăng nhập Threads**, rồi bấm **Đăng nhập ngay trên trang threads.com** "
                "(đừng chỉ đăng nhập trong cửa sổ Instagram) và chờ cửa sổ quay về feed Threads.")
        raise RuntimeError("Chưa lưu được phiên đăng nhập (hết thời gian chờ hoặc cửa sổ bị "
                           "đóng). Bấm lại **🔑 Đăng nhập Threads** rồi đăng nhập trong cửa sổ vừa mở.")
    return STATE_FILE


def shot_is_dark(path: Path, min_white: float = 0.15) -> bool:
    """Ảnh chụp card mà gần như không có mảng trắng -> đã bị lớp phủ che, bỏ."""
    try:
        from PIL import Image
        import numpy as np
        with Image.open(path) as im:
            a = np.asarray(im.convert("RGB").resize((180, 180))).astype(int)
        return float((a.min(2) > 240).mean()) < min_white
    except Exception:
        return False


def _merge_comment(acc: dict, c: dict) -> None:
    """Gộp một comment vừa đọc vào kho: giữ like cao nhất, lấy bản chữ dài nhất."""
    k = (c["handle"], c["text"][:60] or tr.post_id(c) or str(c.get("media_urls")))
    old = acc.get(k)
    if old is None:
        acc[k] = dict(c)
        return
    merged = dict(old)
    merged.update({kk: vv for kk, vv in c.items() if kk != "text"})
    for f in ("likes", "replies", "reposts", "shares"):
        merged[f] = max(int(old.get(f) or 0), int(c.get(f) or 0))
    merged["is_author"] = bool(old.get("is_author") or c.get("is_author"))
    merged["has_media"] = bool(old.get("has_media") or c.get("has_media"))
    merged['media_urls'] = list(dict.fromkeys(old.get('media_urls', []) + c.get('media_urls', [])))
    merged["text"] = (c["text"] if len(c["text"]) >= len(old["text"]) else old["text"])
    merged["datetime"] = c.get("datetime") or old.get("datetime")
    acc[k] = merged


def crawl(a, progress=None) -> tuple[dict | None, list[dict], dict, dict, int]:
    """Mở trình duyệt một lần: bóc dữ liệu, chụp card cần chụp, tải avatar.

    Threads dùng danh sách ảo: card bị gỡ khỏi DOM khi cuộn qua và thứ tự comment bị
    xếp lại sau mỗi lượt cuộn. Vì vậy phải gom dần qua từng lượt (đọc một lần ở cuối
    trang sẽ mất đúng những comment nhiều like nhất — chúng nằm ở đầu trang).
    """
    configure_browser_temp()
    from playwright.sync_api import sync_playwright

    # shots / avatars khoá theo (handle, 60 ký tự đầu) — chỉ số DOM đổi sau mỗi lượt cuộn
    shots: dict[tuple[str, str], Path] = {}
    avatars: dict[tuple[str, str], bytes] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not (a.show or a.login))
        kw = dict(viewport={"width": VIEW_W, "height": VIEW_H}, device_scale_factor=2,
                  locale="vi-VN", color_scheme="light", user_agent=UA)
        if STATE_FILE.exists() and not a.login:
            kw["storage_state"] = str(STATE_FILE)
        ctx = browser.new_context(**kw)
        page = ctx.new_page()
        page.goto(a.url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2500)
        dismiss_overlays(page)

        if a.login:
            print("Đăng nhập trong cửa sổ vừa mở — tự phát hiện khi xong…")
            if not wait_for_login(page, ctx):
                page.close(); ctx.close(); browser.close()
                raise RuntimeError("Hết thời gian chờ đăng nhập (5 phút). Chạy lại `--login`.")
            print(f"Đã lưu phiên: {STATE_FILE}")
            page.goto(a.url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(2500)
            dismiss_overlays(page)

        page.wait_for_timeout(1200)
        dismiss_overlays(page)

        # ---- 1. gom dữ liệu qua từng lượt cuộn (card bị gỡ khỏi DOM khi cuộn tiếp)
        acc: dict[tuple[str, str], dict] = {}
        post: dict | None = None
        passes = max(1, a.scrolls + 1)
        for step in range(passes):
            raws = page.evaluate(EXTRACT_JS)
            items = [c for c in (card_from_raw(r) for r in raws) if c]
            p_now, cmts = split_post(a.url, items)
            if p_now:
                if post is None:
                    post = dict(p_now)
                else:
                    post["likes"] = max(post["likes"], p_now["likes"])
                    post["replies"] = max(post["replies"], p_now["replies"])
                    post["reposts"] = max(post["reposts"], p_now["reposts"])
                    if len(p_now["text"]) > len(post["text"]):
                        post["text"] = p_now["text"]
                    post['media_urls'] = list(dict.fromkeys(post.get('media_urls', []) + p_now.get('media_urls', [])))
                    post['has_media'] = bool(post.get('has_media') or p_now.get('has_media'))
            for c in cmts:
                _merge_comment(acc, c)
            if step + 1 < passes:
                page.mouse.wheel(0, SCROLL_PX)
                page.wait_for_timeout(SCROLL_WAIT)
                dismiss_overlays(page)

        if not post:
            page.close(); ctx.close(); browser.close()
            return None, [], {}, {}, 0

        comments = sorted(acc.values(),
                          key=lambda c: (c["likes"], c["replies"]), reverse=True)
        n_found = len(comments)
        chosen = [post] + (comments[:a.top] if a.top > 0 else comments)

        # ---- 1b. mở trang chi tiết từng comment để lấy reply lồng, cùng phiên đăng nhập.
        post["url"] = post.get("url") or a.url
        if getattr(a, "nested_replies", True):
            reply_page = ctx.new_page()
            def read_thread(url):
                reply_page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                reply_page.wait_for_timeout(1000)
                collected = {}
                for _step in range(min(3, max(1, a.scrolls + 1))):
                    dismiss_overlays(reply_page)
                    tr.expand_reply_buttons(reply_page)
                    for raw in reply_page.evaluate(EXTRACT_JS):
                        card = card_from_raw(raw)
                        if card and not is_junk(card["text"]):
                            key = tr.post_id(card) or (card["handle"], card["text"][:60])
                            collected[key] = card
                    reply_page.mouse.wheel(0, SCROLL_PX)
                    reply_page.wait_for_timeout(SCROLL_WAIT)
                return tr.focused_replies(url, list(collected.values()))

            def nested_progress(index, limit, parent):
                if progress is not None:
                    progress(0.40 + 0.1 * index / max(1, limit),
                             desc=f"Lấy reply trong comment @{parent.get('handle', '?')} ({index + 1}/{limit})…")
            try:
                replies, nested_stats = tr.collect(
                    chosen[1:], post, read_thread,
                    max_depth=getattr(a, "reply_depth", 2),
                    max_pages=getattr(a, "reply_pages", 20),
                    max_replies=getattr(a, "reply_limit", 100), progress=nested_progress,
                    min_likes=getattr(a, "reply_min_likes", 10),
                    per_parent=getattr(a, "reply_per_parent", 2))
            finally:
                reply_page.close()
            chosen = [post] + replies
        else:
            roots, nested_stats = tr.collect(chosen[1:], post, lambda _url: [], max_depth=0)
            nested_stats.update(disabled=True, limited=False, depth_limit=False)
            chosen = [post] + roots
        post["_nested_stats"] = nested_stats

        for it in chosen:
            it["shot_key"] = (it["handle"], it["text"][:60] or tr.post_id(it) or str(it.get("media_urls")))
            it["mode"] = a.mode if a.mode != "auto" else ("shot" if it["has_media"] else "card")
            if it.get("depth", 1) > 1:
                it["mode"] = "card"  # reply đã lấy ở trang riêng, không có trong viewport bài gốc
            if it["mode"] == "shot" and getattr(a, "ident", "full") not in {"full", "avatar"}:
                it["mode"] = "card"     # ảnh chụp luôn lộ avatar/tên -> tự dựng card
            it['_media_pngs'] = download_card_media(ctx.request, it.get('media_urls', []))

        # ---- 2. quay lại đầu trang rồi đi xuống: chụp card ngay lúc nó còn trong DOM
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(1200)
        dismiss_overlays(page)
        page.evaluate(CLEAN_JS, CLEAN_CSS)

        ident = getattr(a, "ident", "full")
        want_avatar = ident in {"full", "avatar"}
        for _ in range(max(2, a.scrolls + 2)):
            raws = page.evaluate(EXTRACT_JS)
            if ident == "avatar":
                try:
                    page.evaluate(HIDE_NAME_JS)   # card mới gắn lại vẫn có thể lộ tên
                except Exception:
                    pass
            by_key: dict[tuple[str, str], int] = {}
            avatar_by_key: dict[tuple[str, str], str] = {}
            for i, r in enumerate(raws):
                c = card_from_raw(r)
                if not c:
                    continue
                k = (c["handle"], c["text"][:60] or tr.post_id(c) or str(c.get("media_urls")))
                by_key.setdefault(k, i)
                if r.get("avatar"):
                    avatar_by_key.setdefault(k, r["avatar"])

            for it in chosen:
                k = it["shot_key"]
                if want_avatar and k not in avatars and k in avatar_by_key:
                    try:
                        rr = ctx.request.get(avatar_by_key[k], timeout=15_000)
                        if rr.ok:
                            avatars[k] = rr.body()
                    except Exception:
                        pass
                if it["mode"] != "shot" or k in shots or k not in by_key:
                    continue
                loc = page.locator(f'[data-shot="{by_key[k]}"]')
                if loc.count() != 1:
                    continue
                TMP_DIR.mkdir(parents=True, exist_ok=True)
                tmp = TMP_DIR / f"_raw_{len(shots):02d}.png"
                try:
                    loc.scroll_into_view_if_needed(timeout=4000)
                    page.wait_for_timeout(400)
                    try:
                        loc.evaluate(HIDE_POST_CHROME_JS)   # bỏ thanh "Hàng đầu" + ô soạn trả lời
                        page.wait_for_timeout(200)
                    except Exception:
                        pass
                    loc.screenshot(path=str(tmp))
                    # Keep the avatar away from the top edge of captured posts.
                    from PIL import Image, ImageOps
                    with Image.open(tmp) as shot:
                        extra = max(12, round(shot.width * 24 / OUT_W))
                        padded = ImageOps.expand(shot.convert('RGB'), border=(0, extra, 0, 0), fill='white')
                    padded.save(tmp)
                except Exception:
                    tmp.unlink(missing_ok=True)
                    continue
                if tmp.exists() and not shot_is_dark(tmp):
                    shots[k] = tmp
                else:
                    tmp.unlink(missing_ok=True)
                    it["mode"] = "card"     # ảnh chụp tối / lỗi -> dựng card thay thế

            if not [it for it in chosen
                    if it["mode"] == "shot" and it["shot_key"] not in shots]:
                break
            page.mouse.wheel(0, SCROLL_PX)
            page.wait_for_timeout(SCROLL_WAIT)
            dismiss_overlays(page)

        page.close(); ctx.close(); browser.close()

    return post, chosen[1:], shots, avatars, n_found


def shrink(path: Path) -> None:
    """Ảnh chụp ở 2x (~1276px) -> 1080px cho nhẹ và khớp pipeline."""
    from PIL import Image
    with Image.open(path) as im:
        out = im.convert("RGB")
        if out.width > OUT_W:
            out = out.resize((OUT_W, round(out.height * OUT_W / out.width)), Image.LANCZOS)
        out.save(path)


# --------------------------------------------------------------------------- kịch bản từ bài đã cào
# Từ nối / hư từ: không chọn làm điểm nhấn nếu còn từ khác
_STOPWORDS = set("""
và là của có cho từ với nhưng mà thì khi nếu vì nên để được bị đã sẽ đang vẫn còn chỉ
rất lắm quá hơn nữa những các mỗi mọi này đó kia ấy nào sao thế vậy ạ nhé nha
tôi bạn mình chúng họ nó anh chị em ông bà hắn ai gì đâu đấy
một hai ba bốn năm sáu bảy tám chín mười trăm nghìn ngàn triệu tỷ
người cái con chiếc thứ việc điều chuyện lúc nơi chỗ
không chưa chẳng đừng hãy chứ rồi mới nhiều siêu rằng
trong ngoài trên dưới trước sau giữa về tới tại ở ra vào lên xuống
cũng đều luôn thật thực sự
""".split())

_NUM_RE = re.compile(r"\d[\d.,]*\s*(?:%|km/h|km|kg|cm|mm|m|triệu|tỷ)?", re.I)

# Từ nối: ưu tiên cắt nhịp ngay trước những từ này
_BREAK_BEFORE = {"và", "nhưng", "mà", "thì", "nên", "vì", "khi", "nếu", "còn", "rồi",
                 "để", "hoặc", "tuy", "dù", "sau", "trước", "&"}

_HAS_DIGIT_RE = re.compile(r"\d")

# Cặp từ dính thành một ý — cắt giữa hai từ này là gãy câu khi TTS đọc
_GLUE_PAIRS = {("đặt", "chân"), ("khủng", "long"), ("kim", "tự"), ("thập", "tự"),
               ("george", "washington"), ("hai", "bà"), ("bà", "trưng"),
               ("tần", "thuỷ"), ("thuỷ", "hoàng"), ("quang", "trung"),
               ("cleopatra", "vii"), ("đại", "tây"), ("tây", "dương")}


_CLOSE = "”\"')]"
_OPEN = "“‘\"'(["
_STRONG_END = "!?;:…"


def _cut_score(words: list[str], j: int) -> int:
    """Điểm của chỗ cắt trước words[j]: 3 = ranh giới ngoặc, 2 = sau phẩy, 1 = trước từ nối.

    Âm = chỗ cắt xấu cho TTS: sau/before con số trơ trọi (bẻ "1799 và", "mất / 1799")
    hoặc để hư từ / dấu hai chấm lơ lửng cuối nhịp.
    """
    prev, nxt = words[j - 1], words[j]
    if prev and prev[-1] in _CLOSE + _STRONG_END:
        return 3
    if nxt and nxt[0] in _OPEN:
        return 3
    if prev.endswith(","):
        return 2
    if nxt.lower().strip(",.!?:;…”)") in _BREAK_BEFORE:
        return 1
    prev_bare = prev.lower().strip(",.!?:;…”)")
    nxt_bare = nxt.lower().strip(",.!?:;…”)\"'")
    if (prev_bare, nxt_bare) in _GLUE_PAIRS:
        return -2  # "đặt chân", "khủng long"… không được bẻ đôi
    if _HAS_DIGIT_RE.search(prev):
        # sau con số chỉ ổn khi số đó đã khép cụm (năm 1799.) hoặc đứng sau đơn vị đo
        return -2
    if _HAS_DIGIT_RE.search(nxt):
        return -2  # cắt ngay trước con số làm "mất / 1799" — TTS đọc cụt
    if prev_bare in _STOPWORDS or prev_bare in (":",):
        return -1  # hư từ lơ lửng cuối nhịp nghe rất gãy
    return 0


def _chop(words: list[str], max_words: int) -> list[list[str]]:
    """Cắt mảnh dài thành các phần gần đều, ưu tiên ranh giới ngoặc / dấu câu / từ nối."""
    n = len(words)
    if n <= max_words:
        return [words]
    parts = -(-n // max_words)
    size = -(-n // parts)
    out: list[list[str]] = []
    start = 0
    for _ in range(parts - 1):
        ideal = start + size
        lo = max(start + 1, ideal - 5)
        hi = min(n - 1, max(lo, min(ideal + 3, start + max_words)))
        best_j, best = ideal, None
        for j in range(lo, hi + 1):
            score = _cut_score(words, j)
            if best is None or score > best or (
                    score == best and abs(j - ideal) < abs(best_j - ideal)):
                best_j, best = j, score
        cut = max(start + 1, min(best_j, start + max_words))
        out.append(words[start:cut])
        start = cut
    tail = words[start:]
    out.extend(_chop(tail, max_words) if len(tail) > max_words else [tail])
    return out


def split_beats(text: str, min_words: int = 7, max_words: int = 14) -> list[str]:
    """Chia lời đọc thành nhịp 7–14 từ, cắt ưu tiên ở dấu câu. Giữ nguyên từng chữ."""
    text = re.sub(r"\s+", " ", (text or "").replace("\u200b", "")).strip()
    if not text:
        return []

    pieces = [p.strip() for p in re.split(r"(?<=[.!?…;:])\s+|(?<=,)\s+", text) if p.strip()]
    chunks: list[list[str]] = []
    for piece in pieces:
        chunks.extend(_chop(piece.split(), max_words))

    beats: list[list[str]] = []
    for ch in chunks:
        if beats and len(beats[-1]) + len(ch) <= max_words:
            beats[-1].extend(ch)
        else:
            beats.append(list(ch))

    # gộp nhịp quá ngắn vào hàng xóm (chấp nhận dài hơn max một chút để trọn cụm nghĩa)
    changed = True
    while changed:
        changed = False
        for i, b in enumerate(beats):
            if len(b) >= min_words:
                continue
            if i > 0 and len(beats[i - 1]) + len(b) <= max_words + 2:
                beats[i - 1].extend(b)
                beats.pop(i)
                changed = True
                break
            if i + 1 < len(beats) and len(b) + len(beats[i + 1]) <= max_words + 2:
                beats[i].extend(beats[i + 1])
                beats.pop(i + 1)
                changed = True
                break
    return [" ".join(b) for b in beats]


def mark_emphasis(spoken: str) -> str:
    """Bọc *…* quanh chỗ đáng nhấn — chỉ khi chính tác giả đã đánh dấu.

    Số liệu (50%, 40%, 10) trước, rồi tới chữ viết HOA giữa câu (KHÔNG).
    Không có gì rõ ràng thì để nguyên, không đoán từ khoá.
    """
    m = _NUM_RE.search(spoken)
    if m:
        before = spoken[m.start() - 1] if m.start() > 0 else " "
        if not (before.isalnum() or before in "<>#@:/"):
            end = m.start() + len(m.group(0).rstrip())
            return spoken[:m.start()] + "*" + spoken[m.start():end] + "*" + spoken[end:]

    for w in re.finditer(r"[^\W\d_]{2,}", spoken, re.UNICODE):
        word = w.group(0)
        if not word.isupper() or word.upper() == word.lower():
            continue
        if w.start() == 0:            # chữ đầu câu bị viết hoa, không phải ý tác giả
            continue
        return spoken[:w.start()] + "*" + word + "*" + spoken[w.end():]
    return spoken


def split_beat(beat: str) -> tuple[str, str]:
    """Tách một dòng kịch bản chữ thành (lời đọc, chữ hiển thị).

    Dòng có '||': bên trái là lời đọc, bên phải là chữ hiển thị do người dùng soạn.
    Dòng thường: lời đọc = chữ hiển thị (tự nhấn mạnh bằng mark_emphasis).
    """
    spoken, sep, display = (beat or "").partition("||")
    if sep:
        return spoken.strip(), display.strip() or spoken.strip()
    return beat.strip(), mark_emphasis(beat.strip())


def script_lines(result: dict) -> list[tuple[str, str]]:
    """[(ảnh trong thư viện nội dung, lời đọc)] — bài gốc trước, comment theo like."""
    items = [result["post"]] + list(result.get("comments") or [])
    pairs: list[tuple[str, str]] = []
    for item in items:
        image = item.get("image") or ""
        for beat in split_beats(item.get("text") or "") or ['[sound]']:
            pairs.append((image, beat))
    return pairs


def build_script(result: dict) -> tuple[str, list[str]]:
    """Sinh kịch bản dán được vào app + ảnh cho từng dòng (để ghi vào cột clip).

    Video Threads mặc định KHÔNG có phụ đề: chữ đã nằm trên ảnh comment, mỗi nhịp
    là 'lời đọc || -'. Muốn nhịp nào có phụ đề thì thay '-' bằng chữ hiển thị.
    """
    tag = result.get("tag") or "post"
    lines: list[str] = []
    clips: list[str] = []
    for image, beat in script_lines(result):
        lines.append(f"[{tag}] {beat} || -")
        clips.append(image)
    return "\n".join(lines), clips


# Kịch bản dạng chữ để người dùng sửa trước khi chuyển thành "Các nhịp".
# Mỗi ảnh là một mục:  # <đường-dẫn-ảnh>   (mô tả)
# Các dòng bên dưới là từng nhịp đọc, đúng thứ tự.
# Video Threads mặc định KHÔNG có phụ đề: mỗi nhịp là 'lời đọc || -' (chỉ TTS đọc +
# ảnh comment hiện đầy màn hình). Muốn nhịp nào có phụ đề thì thay '-' bằng chữ:  lời đọc || chữ
# Đơn giản hơn: ghi lời đọc không có '||' -> tự hiện phụ đề với chỗ nhấn mạnh *từ*.
SECTION_DESC_RE = re.compile(r"\s+\(.*\)\s*$")


def build_editable_script(result: dict) -> str:
    """Kịch bản chữ (sửa được): mỗi ảnh một mục '#', bên dưới là từng nhịp đọc."""
    out: list[str] = []
    items = [("post", result["post"])] + [("cmt", c) for c in (result.get("comments") or [])]
    for n, (kind, item) in enumerate(items, 1):
        image = (item.get("image") or "").strip()
        if not image:
            image = f"{result.get('tag') or 'post'}/" \
                    f"{_image_name(n, item)}"
        who = "bài gốc" if kind == "post" else (
            "reply" if (item.get("depth") or 1) >= 2 else f"comment {n - 1}")
        bits = [who]
        if item.get("parent_handle"):
            bits.append("↳ @" + item["parent_handle"])
        if item.get("handle"):
            bits.append("@" + item["handle"])
        bits.append(f"{vn_int(item.get('likes') or 0)} like")
        out.append(f"# {image}   ({' · '.join(bits)})")
        out.extend(f"{beat} || -" for beat in split_beats(item.get("text") or "") or ['[sound]'])
        out.append("")
    return "\n".join(out).strip() + "\n"


def parse_sections(text: str) -> list[tuple[str, list[str]]]:
    """Đọc kịch bản chữ đã sửa: [(đường dẫn ảnh, [từng nhịp đọc])].

    Dòng bắt đầu bằng '#' mở mục ảnh mới; mỗi dòng còn lại là một nhịp. Phần mô tả
    trong ngoặc ở cuối dòng '#' bị bỏ, chỉ giữ đường dẫn ảnh.
    """
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            body = SECTION_DESC_RE.sub("", line.lstrip("#").strip()).strip()
            image = body.split()[0] if body.split() else ""
            current = []
            if image:
                sections.append((image, current))
            else:
                current = None
            continue
        if current is not None:
            current.append(line)
    return [(img, beats or ['[sound] || -']) for img, beats in sections]


def reorder_script_sections(text: str, images, fallback: str, removed=()) -> str:
    """Đổi thứ tự mục ảnh, giữ nguyên các dòng đọc đã sửa và các mục thêm tay."""
    def blocks(value):
        out, current = [], []
        image = None
        for raw in (value or "").splitlines(keepends=True):
            if raw.strip().startswith("#"):
                if current:
                    out.append((image, "".join(current)))
                body = SECTION_DESC_RE.sub("", raw.strip().lstrip("#").strip()).strip()
                image = body.split()[0] if body.split() else None
                current = []
            current.append(raw)
        if current:
            out.append((image, "".join(current)))
        return out

    def key(image):
        return (image or "").replace("\\", "/").rsplit("/", 1)[-1]

    existing = blocks(text)
    defaults = {key(image): block for image, block in blocks(fallback) if image}
    wanted = {key(image) for image in images}
    dropped = {key(image) for image in removed}
    out = [block for image, block in existing if image is None]
    for image in images:
        matches = [block for old, block in existing if old and key(old) == key(image)]
        out.extend(matches or [defaults.get(key(image), "")])
    out.extend(block for image, block in existing
               if image and key(image) not in wanted and key(image) not in dropped)
    return "\n\n".join(block.rstrip() for block in out if block.strip()).rstrip() + "\n"


# --------------------------------------------------------------------------- API cho app
@dataclass
class Run:
    """Tham số một lần lấy bài — dùng chung cho CLI và tab Threads trong app."""

    url: str
    content: str = ""
    tag: str = "post"
    top: int = 20
    mode: str = "auto"          # auto | card | shot
    ident: str = "avatar"       # avatar | full | no-avatar | anon
    out: str = ""
    canvas: str = "auto"
    max_chars: int = 900
    scrolls: int = 6
    login: bool = False
    show: bool = False
    dry_run: bool = False
    nested_replies: bool = True
    reply_depth: int = 1
    reply_pages: int = 20
    reply_limit: int = 100
    reply_min_likes: int = 10
    reply_per_parent: int = 2


def _canvas_size(spec: str) -> tuple[int, int] | None:
    """'1080x900' -> (1080, 900); 'none' -> None (cao theo nội dung)."""
    if (spec or "").strip().lower() in {"", "none", "auto"}:
        return None
    try:
        _, h = (int(x) for x in spec.lower().split("x"))
        return (OUT_W, h)
    except ValueError:
        return (OUT_W, 900)


def _image_name(i: int, item: dict) -> str:
    kind = "post" if i == 1 else "cmt"
    return f"{i:02d}-{kind}-{slug(item['handle'], 18)}.png"


def run(r: Run, progress=None) -> dict:
    """Cào bài + comment, ghi ảnh và threads.json. Trả về dữ liệu cho app/CLI.

    `progress(frac, desc="…")` là tuỳ chọn — app truyền gr.Progress vào để thanh chạy.
    """
    def say(frac: float, msg: str) -> None:
        if progress is not None:
            try:
                progress(frac, desc=msg)
            except TypeError:  # progress kiểu cũ chỉ nhận 1 tham số
                progress(frac)

    if r.dry_run:
        r.mode = "card"          # chỉ đọc dữ liệu, không mở trình duyệt để chụp
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR, ignore_errors=True)

    say(0.05, f"Đang mở {r.url} …")
    post, comments, shots, avatars, n_found = crawl(r, progress=progress)
    if not post:
        raise RuntimeError("Không đọc được bài nào. Thử đăng nhập (--login) "
                           "hoặc mở trình duyệt (--show).")
    # crawl đã chọn top theo like; chỉ đổi thứ tự phát của chính nhóm đã chọn.
    comments = cm.chronological(comments)

    content = (r.content or "").strip() or slug(post["handle"])
    tag = slug(r.tag)
    out_dir = Path(r.out) if r.out else ILLUS_DIR / content / tag
    canvas = _canvas_size(r.canvas)

    plan = [post] + comments
    for i, it in enumerate(plan, start=1):
        it["file"] = _image_name(i, it)
        it["rel"] = f"{tag}/{it['file']}"
        it["kind"] = "post" if i == 1 else "cmt"

    if not r.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        from .threads_text import prepare_emojis
        prepare_emojis([text for it in plan if it.get('mode') != 'shot'
                        for text in (it.get('text', ''), it.get('handle', ''))])
        for i, it in enumerate(plan):
            say(0.55 + 0.4 * i / max(1, len(plan)), f"Vẽ ảnh {i + 1}/{len(plan)}…")
            dest = out_dir / it["file"]
            key = it.get("shot_key") or (it["handle"], it["text"][:60])
            if key in shots:
                shots[key].replace(dest)
                shrink(dest)
            else:
                render_card(it, dest, canvas, avatars.get(key),
                            max_chars=r.max_chars, ident=r.ident)

        # dọn ảnh của lần chạy trước (like đổi -> nội dung mới) và ảnh tạm
        keep = {it["file"] for it in plan}
        for old in out_dir.iterdir():
            if not old.is_file():
                continue
            if old.name.startswith("_raw_") or (
                    re.match(r"^\d{2}-(post|cmt)-", old.name) and old.name not in keep):
                old.unlink()

    result = {
        "url": r.url,
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
        "content": content,
        "tag": tag,
        "ident": r.ident,
        "dir": str(out_dir),
        "json": str(out_dir / "threads.json"),
        "post": {**{k: post[k] for k in ("handle", "text", "likes", "replies", "reposts",
                                         "shares", "datetime", "url")},
                 "id": tr.post_id(post),
                 "media_urls": post.get("media_urls", []),
                 "minutes": reading_minutes(post["text"]),
                 "image": post["rel"]},
        "comments": [{**{k: c[k] for k in ("handle", "text", "likes", "replies",
                                           "datetime", "url", "is_author")},
                      **{k: c.get(k) for k in ("id", "parent_id", "parent_url", "parent_handle", "depth", "relation", "is_pinned")},
                      "media_urls": c.get("media_urls", []),
                      "minutes": reading_minutes(c["text"]),
                      "image": c["rel"]} for c in comments],
        "images": [{"file": it["file"], "rel": it["rel"],
                    "path": str(out_dir / it["file"]),
                    "kind": "post" if i == 0 else "cmt",
                    "handle": it["handle"]} for i, it in enumerate(plan)],
        "stats": {"comments_found": n_found, "comments_used": len(comments),
                  "nested": post.get("_nested_stats") or {},
                  "logged_in": bool(_threads_auth_cookies(_state_cookies())),
                  "replies_total": post.get("replies") or 0,
                  "replies_hidden": max(0, (post.get("replies") or 0) - n_found
                                        - (post.get("_nested_stats") or {}).get("replies_added", 0))},
    }

    if not r.dry_run:
        Path(result["json"]).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
        script, _ = build_script(result)
        (out_dir / "script.txt").write_text(script + "\n", "utf-8")
        if TMP_DIR.exists():
            shutil.rmtree(TMP_DIR, ignore_errors=True)
    say(1.0, "Xong")
    return result


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chụp post Threads + comment nhiều like cho video")
    ap.add_argument("url", help="link post Threads")
    ap.add_argument("--content", default="", help="tên nội dung (thư mục trong assets/illus)")
    ap.add_argument("--tag", default="post", help="thẻ minh họa để kịch bản gọi [tag]")
    ap.add_argument("--top", type=int, default=20, help="số comment nhiều like nhất (0 = tất cả)")
    ap.add_argument("--mode", choices=["auto", "card", "shot"], default="auto")
    ap.add_argument("--ident", choices=["avatar", "full", "no-avatar", "anon"], default="avatar",
                    help="danh tính trên card: avatar = ảnh đại diện + chữ Threads (mặc định), "
                         "full = avatar + tên, no-avatar = ẩn avatar giữ tên, anon = ẩn cả hai")
    ap.add_argument("--out", default="", help="thư mục xuất (mặc định assets/illus/<content>/<tag>)")
    ap.add_argument("--canvas", default="auto",
                    help="khung ảnh card: 'auto' = cao theo nội dung (mặc định), "
                         "'1080x900' = khung cố định, 'none' = như auto")
    ap.add_argument("--max-chars", type=int, default=900, help="cắt chữ trên card (lời đọc vẫn đủ)")
    ap.add_argument("--scrolls", type=int, default=6, help="số lần cuộn để nạp comment")
    ap.add_argument("--login", action="store_true", help="mở trình duyệt để đăng nhập và lưu phiên")
    ap.add_argument("--show", action="store_true", help="hiện trình duyệt (debug)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in dữ liệu, không tạo ảnh")
    ap.add_argument("--no-nested-replies", action="store_true", help="chỉ lấy comment ngoài cùng")
    ap.add_argument("--reply-depth", type=int, choices=range(1, 5), default=1,
                    help="số lớp reply lồng tối đa (mặc định 1)")
    ap.add_argument("--reply-min-likes", type=int, default=10, help="like tối thiểu của reply")
    ap.add_argument("--reply-per-parent", type=int, default=2, help="reply tối đa mỗi comment cha")
    a = ap.parse_args(argv)

    r = Run(url=a.url, content=a.content, tag=a.tag, top=a.top, mode=a.mode, ident=a.ident,
            out=a.out, canvas=a.canvas, max_chars=a.max_chars, scrolls=a.scrolls,
            login=a.login, show=a.show, dry_run=a.dry_run,
            nested_replies=not a.no_nested_replies, reply_depth=a.reply_depth,
            reply_min_likes=max(0, a.reply_min_likes), reply_per_parent=max(0, a.reply_per_parent))

    print(f"Đang mở {a.url} …")
    try:
        res = run(r)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2

    if a.dry_run:
        head = {"post": res["post"], "comments": res["comments"],
                "comments_found": res["stats"]["comments_found"]}
        print(json.dumps(head, ensure_ascii=False, indent=2)[:5000])
        return 0

    print(f"\nĐã ghi {len(res['images'])} ảnh vào {res['dir']}")
    p = res["post"]
    print(f"  bài gốc : @{p['handle']} — {vn_int(p['likes'])} like — "
          f"{len(p['text'])} ký tự (~{p['minutes'] * 60:.0f}s đọc)")
    for c in res["comments"]:
        print(f"  comment : @{c['handle']}{' (tác giả)' if c['is_author'] else ''} — "
              f"{vn_int(c['likes'])} like — ~{c['minutes'] * 60:.0f}s đọc")
    print(f"  dữ liệu : {res['json']}")
    print(f"  kịch bản: {res['dir']}\\script.txt")
    hidden = res["stats"].get("replies_hidden") or 0
    if hidden:
        who = ("Threads chỉ tải một phần reply trong một lượt — reply lồng dưới comment khác "
               "phải mở riêng từng comment mới thấy." if res["stats"].get("logged_in")
               else "Threads chỉ trả chừng đó cho khách chưa đăng nhập — comment lồng dưới "
                    "comment khác bị ẩn.")
        print(f"  (!) Threads báo bài có {res['stats']['replies_total']} reply nhưng chỉ trả "
              f"{res['stats']['comments_found']} — còn {hidden} reply chưa lấy được.\n"
              f"      {who}")
        if not res["stats"].get("logged_in"):
            print("      Bấm nút Đăng nhập Threads trong app (hoặc chạy `--login`) rồi lấy lại.")
    print(f"\nKịch bản: đọc nguyên văn post + từng comment, mỗi nhịp dùng đúng ảnh "
          f"trong cột clip (đường dẫn tính từ {res['content']}/).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
