"""Giao diện web chạy trên máy bạn: python -m videomaker (hoặc bấm run.bat)."""
from __future__ import annotations

import json
import re
import subprocess
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path


from . import caption as cap
from . import comment_manager as cm
from . import script_draft as sd
from . import pipeline as pl
from . import threads_shot as ts
from . import fb_post as fb
from .paths import CONFIG_DIR
from .settings_store import load_settings as read_settings, save_settings as write_settings


class AppError(Exception):
    """Lỗi dành cho người dùng: message hiển thị thẳng trên giao diện."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _noop_progress(*_args, **_kwargs):
    pass

# --------------------------------------------------------------------------- lưu / khôi phục cấu hình
SETTINGS_FILE = CONFIG_DIR / "settings.json"
_SAVE_LOCK = threading.Lock()

# Thứ tự khớp đúng tham số của make_opts()
OPT_KEYS = ["backend", "voice", "speed", "bg", "upper", "font", "font_size", "text_color",
            "outline_color", "outline_w", "text_y", "max_words", "pop", "meme_y", "meme_w",
            "meme_h", "carry", "use_music", "music_vol", "nvenc", "emph_color", "emph_scale",
            "content", "gap", "threads_radius", "threads_side_margin", "threads_shadow", "threads_padding", "threads_max_height", "threads_padding_top", "threads_padding_right", "threads_padding_bottom", "threads_padding_left", "threads_zoom", "card_motion", "karaoke", "bg_motion", "pop_in", "sfx", "fps", "mascot", "next_card", "align_subs", "tier_gap_scale"]

DEFAULTS = {
    "backend": pl.BACKEND_VIENEU, "voice": "", "speed": 1.0, "bg": "ngẫu nhiên",
    "upper": True, "font": "Segoe UI Black", "font_size": 120, "text_color": "#FFFFFF",
    "outline_color": "#FF9A1F", "outline_w": 9, "text_y": 880, "max_words": 4, "pop": False,
    "meme_y": 150, "meme_w": 960, "meme_h": 640, "carry": True, "use_music": False,
    "music_vol": 0.08, "nvenc": False, "emph_color": "#FF9A1F", "emph_scale": 1.4,
    "tier_gap_scale": 0.8,
    "content": "", "gap": pl.GAP, "threads_radius": 0, "threads_side_margin": 108,
    "threads_shadow": 0, "threads_padding": 0, "threads_max_height": 640, "threads_zoom": 140,
    "threads_padding_top": -1, "threads_padding_right": -1, "threads_padding_bottom": -1, "threads_padding_left": -1,
    "card_motion": True, "karaoke": False, "bg_motion": True, "pop_in": False, "sfx": True, "fps": 60, "mascot": True, "next_card": True, "align_subs": True,
    "threads_scrape": {"top": 20, "mode": "auto", "ident": "avatar", "nested": True,
                       "reply_depth": 1, "reply_per_parent": 2},
}

_SLIDERS = {"speed": (0.8, 1.4), "font_size": (60, 200), "outline_w": (0, 20),
            "text_y": (300, 1700), "max_words": (1, 8), "meme_y": (60, 800),
            "meme_w": (300, 1080), "meme_h": (200, 900), "music_vol": (0.02, 0.4),
            "emph_scale": (1.0, 1.8), "tier_gap_scale": (0.6, 1.2), "gap": (0.0, 2.0), "threads_radius": (0, 80),
            "threads_zoom": (100, 200), "threads_side_margin": (0, 120), "threads_shadow": (0, 100), "threads_padding": (0, 200), "threads_max_height": (200, 1000), "fps": (24, 60),
            **{f"threads_padding_{side}": (-1, 200) for side in ("top", "right", "bottom", "left")}}
_INT_KEYS = {"font_size", "outline_w", "text_y", "max_words", "meme_y", "meme_w", "meme_h", "threads_radius", "threads_side_margin", "threads_shadow", "threads_padding", "threads_max_height", "threads_padding_top", "threads_padding_right", "threads_padding_bottom", "threads_padding_left", "threads_zoom", "fps"}
_FLOAT_KEYS = {"speed", "music_vol", "emph_scale", "tier_gap_scale", "gap"}
_BOOL_KEYS = {"upper", "pop", "carry", "use_music", "nvenc", "card_motion", "karaoke", "bg_motion", "pop_in", "sfx", "mascot", "next_card"}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

def _clean(key, value):
    """Đọc 1 giá trị từ file: sai kiểu, sai khoảng hoặc đã lỗi thời thì trả None (giữ mặc định)."""
    if key == 'threads_scrape':
        from .threads_options import clean_options
        return clean_options(value)
    if key in _BOOL_KEYS:
        return value if isinstance(value, bool) else None
    if key in _INT_KEYS or key in _FLOAT_KEYS:
        if isinstance(value, bool):
            return None
        lo, hi = _SLIDERS[key]
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        if num != num:  # NaN
            return None
        num = min(max(num, lo), hi)
        return int(round(num)) if key in _INT_KEYS else round(num, 3)
    if key in ("text_color", "outline_color", "emph_color"):
        return value if isinstance(value, str) and _HEX.match(value) else None
    if key == "backend":
        return value if value in (pl.BACKEND_VIENEU, pl.BACKEND_DUMMY) else None
    if key == "bg":
        # nền đã bị xóa khỏi thư mục thì quay về ngẫu nhiên
        return value if isinstance(value, str) and value in bg_choices() else None
    if key == "voice":
        return value if isinstance(value, str) else None
    if key == "font":
        return value if isinstance(value, str) and value.strip() else None
    if key == "content":
        # tên nội dung -> thư viện minh họa assets/illust/<content>/ (mỗi video một nội dung)
        return value.strip() if isinstance(value, str) else None
    return None

def load_settings() -> dict:
    """Cấu hình đã lưu; thiếu hoặc hỏng thì dùng mặc định."""
    cfg = dict(DEFAULTS)
    try:
        raw = read_settings(SETTINGS_FILE)
    except (OSError, ValueError):
        return cfg
    if isinstance(raw, dict):
        for key in DEFAULTS:
            if key in raw:
                val = _clean(key, raw[key])
                if val is not None:
                    cfg[key] = val
    return cfg

def save_settings(**updates) -> str:
    """Ghi các khóa truyền vào, giữ nguyên các khóa khác đang có trong file."""
    with _SAVE_LOCK:
        cfg = load_settings()
        for key, value in updates.items():
            if key in DEFAULTS:
                val = _clean(key, value)
                if val is not None:
                    cfg[key] = val
        write_settings(SETTINGS_FILE, {key: value for key, value in cfg.items() if key != "script"})
    return str(SETTINGS_FILE)

# --------------------------------------------------------------------------- hàm hỗ trợ
def bg_choices() -> list[str]:
    return ["ngẫu nhiên"] + [p.name for p in pl.list_backgrounds()]

def safe_name(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', " ", s or "").strip()
    return s or "khac"

def make_opts(backend, voice, speed, bg, upper, font, font_size, text_color, outline_color,
              outline_w, text_y, max_words, pop, meme_y, meme_w, meme_h, carry,
              use_music, music_vol, nvenc, emph_color, emph_scale, content, gap=pl.GAP,
              threads_radius=0, threads_side_margin=0, threads_shadow=0,
              threads_padding=0, threads_max_height=640, threads_padding_top=-1,
              threads_padding_right=-1, threads_padding_bottom=-1, threads_padding_left=-1, threads_zoom=140,
              card_motion=True, karaoke=False, bg_motion=True, pop_in=True, sfx=True,
              fps=60, mascot=True, next_card=True, align_subs=True, tier_gap_scale=0.8) -> pl.Options:
    return pl.Options(
        backend=backend, voice=voice or "", speed=float(speed), bg=bg or "ngẫu nhiên",
        content=(content or "").strip(), gap=float(gap),
        upper=bool(upper), font=(font or "Segoe UI Black").strip(), font_size=int(font_size),
        text_color=text_color or "#FFFFFF", outline_color=outline_color or "#FF9A1F",
        outline_w=int(outline_w), text_y=int(text_y), max_words=int(max_words), pop=bool(pop),
        meme_y=int(meme_y), meme_w=int(meme_w), meme_h=int(meme_h), carry=bool(carry),
        use_music=bool(use_music), music_volume=float(music_vol), nvenc=bool(nvenc),
        emph_color=emph_color or "#FF9A1F", emph_scale=float(emph_scale),
        tier_gap_scale=float(tier_gap_scale),
        threads_radius=int(threads_radius),
        threads_side_margin=int(threads_side_margin),
        threads_shadow=int(threads_shadow),
        threads_padding=int(threads_padding),
        threads_max_height=int(threads_max_height),
        threads_padding_top=int(threads_padding_top), threads_padding_right=int(threads_padding_right),
        threads_padding_bottom=int(threads_padding_bottom), threads_padding_left=int(threads_padding_left),
        threads_zoom=int(threads_zoom),
        card_motion=bool(card_motion), karaoke=bool(karaoke),
        bg_motion=bool(bg_motion), pop_in=bool(pop_in), sfx=bool(sfx), fps=int(fps),
        mascot=bool(mascot), next_card=bool(next_card), align_subs=bool(align_subs),
    )

# --------------------------------------------------------------------------- xử lý sự kiện
def on_analyze(script, content):
    rows = pl.analyze(script or "", content=content.strip() or "")
    if not rows:
        raise AppError("Kịch bản đang trống. Mỗi dòng là một nhịp, dòng bắt đầu bằng # bị bỏ qua.")
    n_clip = sum(1 for r in rows if r[4])
    msg = f"Đã tách {len(rows)} dòng, gán được clip cho {n_clip} dòng. Sửa bảng bên dưới nếu cần rồi bấm xem thử."
    if n_clip == 0:
        msg += " (Chưa có clip nào khớp thẻ — thêm clip vào tab 'Thư viện' hoặc gõ tên file vào cột cuối.)"
    warns = sd.lint_rows(rows)
    if warns:
        msg += "\n\n⚠️ **Cần rà:** " + "; ".join(warns) + "."
    return rows, msg

# --------------------------------------------------------------------------- Threads
def threads_opts(t_content, *opt_values) -> pl.Options:
    """Tab Threads: bề ngang card cố định, chiều cao khung tự nở theo card cao nhất.

    Mọi card phủ đủ ngang (lề 2 bên bằng nhau) và kết thúc ở cùng một đường, chữ sát
    ngay dưới. Nhịp không phụ đề (`|| -`) canh giữa dọc khung và không bị chỗ chữ kéo lên.

    Các thông số còn lại (giọng đọc, màu chữ, nhạc…) lấy từ tab 'Làm video'.
    """
    opt = make_opts(*opt_values)
    opt.content = (t_content or "").strip() or opt.content
    margin = max(0, int(getattr(opt, 'threads_side_margin', 0) or 0))
    opt.meme_w, opt.meme_h, opt.meme_y = max(300, 1080 - 2 * margin), opt.threads_max_height, 60
    opt.meme_anchor = "bottom"   # mọi card kết thúc ở cùng một đường (y = 700)
    opt.carry = True
    # chữ neo mép trên, cách đáy card 56px — không phụ thuộc card cao thấp hay 1-2 dòng
    opt.text_anchor = "top"
    opt.text_y = opt.meme_y + opt.meme_h + 56
    opt.threads = True
    return opt

def on_threads_logout():
    if ts.STATE_FILE.exists():
        ts.STATE_FILE.unlink()
    return ts.session_status()

def _threads_item_rows(res: dict) -> list[list]:
    return cm.table_rows(res)

def on_threads_comment_action(state, rows, script, image, action):
    """Nút riêng trên mỗi comment; không dùng trạng thái chọn hàng hoặc ô tick."""
    comments = (state or {}).get("comments") or []
    identity = next((i for i, c in enumerate(comments, 1) if c.get("image") == image), None)
    if identity is None:
        raise AppError("Comment đã thay đổi hoặc đã bị xóa. Hãy dùng danh sách hiện tại.")
    try:
        draft = cm.validate_rows(rows, len(comments))
        for row in draft:
            row[1] = action == "delete" and int(row[0]) == identity
        if action in ("up", "down"):
            draft = cm.move_row(draft, identity, -1 if action == "up" else 1)
        elif action != "delete":
            raise ValueError("Thao tác comment không hợp lệ.")
    except ValueError as e:
        raise AppError(str(e)) from e
    return on_threads_manage(state, draft, script)

def on_threads_sort_commit(state, rows, script, mode):
    try:
        draft = (cm.sort_likes(rows) if mode == "likes"
                 else cm.sort_time(state or {}, rows, newest=mode == "newest"))
    except ValueError as e:
        raise AppError(str(e)) from e
    return on_threads_manage(state, draft, script)

def on_threads_manage(state, rows, script):
    """Áp dụng thứ tự / bỏ comment khỏi video; đồng bộ kịch bản và ảnh, giữ file nguồn."""
    if not state or not state.get("post"):
        raise AppError("Bấm '1. Lấy bài + comment' trước đã.")
    try:
        res = cm.apply_draft(state, rows)
    except ValueError as e:
        raise AppError(str(e)) from e
    wanted = [res["post"].get("image")] + [c.get("image") for c in res["comments"]]
    gone_rel = {c.get("image") for c in state.get("comments", [])} - set(wanted)
    new_script = ts.reorder_script_sections(
        script, wanted, ts.build_editable_script(res), gone_rel)
    try:
        Path(res["json"]).write_text(json.dumps(res, ensure_ascii=False, indent=2), "utf-8")
        tag = res.get("tag") or "post"
        script_ref = "\n".join(
            f"[{tag}] {spoken} || {display}"
            for _image, beats in ts.parse_sections(new_script)
            for spoken, display in (ts.split_beat(beat) for beat in beats))
        Path(res["dir"], "script.txt").write_text(script_ref + "\n", "utf-8")
    except OSError as e:
        raise AppError(f"Không lưu được danh sách comment: {e}") from e
    cards = [(i["rel"], i["rel"]) for i in res["images"]]
    removed = len(state.get("comments") or []) - len(res["comments"])
    msg = f"Đã cập nhật thứ tự, bỏ {removed} comment. Còn {len(res['comments'])} comment."
    items = _threads_item_rows(res)
    return (res, {'value': items},
            [i["path"] for i in res["images"]],
            {'choices': cards, 'value': cards[0][1] if cards else None},
            new_script, "Bấm **2. Chuyển thành Các nhịp** để dùng danh sách mới.", msg,
            {'value': []}, None, None, "Danh sách đã thay đổi; hãy dựng lại video.")


def _state_from_script(text: str) -> dict | None:
    """Chưa bấm '1. Lấy bài + comment' trong phiên này nhưng kịch bản dán vào có dòng
    '# …png' -> tự tìm lại bài nguồn: khớp tên ảnh trong các threads.json đã lưu dưới
    assets/illus, chọn bài khớp nhiều ảnh nhất. Ảnh đã có sẵn nên không cần lấy lại."""
    wanted = {Path(img.replace("\\", "/")).name
              for img, _ in ts.parse_sections(text or "") if img}
    if not wanted:
        return None
    best: tuple[int, dict] | None = None
    for f in pl.ILLUS_DIR.glob("*/*/threads.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not data.get("post"):
            continue
        rels = {Path(i.get("rel") or "").name for i in data.get("images") or []}
        score = len(wanted & rels)
        if score and (best is None or score > best[0]):
            best = (score, data)
    return best[1] if best else None

def on_threads_build(text, state):
    """Đọc kịch bản chữ đã sửa -> bảng 'Các nhịp', cột cuối gắn đúng ảnh của từng mục.

    Reply còn được gắn thêm ngữ cảnh cha (cột 6): tên + 1–2 dòng đang được trả lời,
    để lúc dựng video hiện khung nhỏ ↳ phía trên ảnh reply. Chưa lấy bài trong phiên
    này mà kịch bản có tên ảnh thì tự nhận diện bài nguồn đã lưu, không phải bấm bước 1.
    """
    res = state or {}
    recovered = False
    if not res.get("post"):
        res = _state_from_script(text or "")
        recovered = res is not None
        if not recovered:
            raise AppError(
                "Chưa có dữ liệu bài Threads. Bấm **1. Lấy bài + comment**, hoặc dùng "
                "kịch bản có dòng `# …png` trỏ tới ảnh của một bài đã lấy trước đó "
                "(app tự nhận diện bài nguồn từ tên ảnh).")

    sections = ts.parse_sections(text or "")
    if not sections:
        raise AppError("Chưa đọc được mục ảnh nào. Mỗi ảnh phải bắt đầu bằng một dòng "
                       "`# ten-file-anh.png` rồi bên dưới là các dòng đọc.")
    content = res.get("content", "")
    tag = (res.get("tag") or "post").strip() or "post"
    # Dòng '#' có [nozoom]: mục đó không sinh nhịp zoom tự động (nút thùng rác ở tab
    # Các nhịp thêm marker này để xoá nhịp zoom mà vẫn nhớ sau khi tạo nhịp lại).
    no_zoom = {line.lstrip("#").strip().split()[0]
               for line in (text or "").splitlines()
               if line.strip().startswith("#") and "[nozoom]" in line.lower()
               and line.lstrip("#").strip()}

    lines: list[str] = []
    clips: list[str] = []
    for image, beats in sections:
        for number, beat in enumerate(beats, 1):
            spoken, display = ts.split_beat(beat)
            if not spoken.replace('*', '').strip():
                spoken, display = '[sound]', '-'
            if spoken in ('[sound]', '[zoom]'):
                display = '-'
            lines.append(f"[{tag}] {spoken} || {display}")
            clips.append(image)

    rows = pl.analyze("\n".join(lines), content=content)
    if len(rows) != len(clips):
        raise AppError(f'Không thể chuyển đủ dòng đọc ({len(rows)}/{len(clips)}). '
                       'Kiểm tra các dòng trống hoặc chỉ có ký hiệu trong kịch bản.')

    missing: list[str] = []
    n_ctx = 0
    n_zoom = 0
    n_sound_zoom = 0
    manual_zoom = {clip for row, clip in zip(rows, clips) if row[1] == '[zoom]'}
    # Mục chỉ có ảnh (comment/ảnh không chữ) đã có nhịp [sound] phát tiếng cho cả mục.
    sound_only: dict[str, bool] = {}
    for row, clip in zip(rows, clips):
        sound_only[clip] = sound_only.get(clip, True) and row[1] == '[sound]'
    built: list[list] = []
    for i, (row, clip) in enumerate(zip(rows, clips)):
        row[4] = clip          # ảnh cụ thể của mục, không để assign_clips bốc ngẫu nhiên
        ctx = ts.reply_context(res, clip)
        row.append(ctx)
        row.append('1' if row[1] == '[zoom]' else '')   # cột 7: công tắc zoom của nhịp
        n_ctx += bool(ctx)
        built.append(row)
        if i + 1 < len(rows) and clips[i + 1] == clip:
            continue
        # Mục có ảnh đính kèm: thêm 1 nhịp zoom ở cuối mục — card phóng to, ẩn phụ đề,
        # đọc `[zoom]` nên đi kèm nhạc videoplayback như dòng `[zoom] || -` viết tay.
        # Riêng mục chỉ có ảnh: nhịp [sound] đã phát đúng tiếng đó rồi, thêm nhịp
        # [zoom] nữa là lặp tiếng — cho chính nhịp tiếng bật zoom luôn.
        if ts.has_media(res, clip) and clip not in manual_zoom and clip not in no_zoom:
            if sound_only.get(clip):
                built[-1][6] = '1'
                n_sound_zoom += 1
            else:
                built.append([len(built) + 1, '[zoom]', '-', row[3], clip, ctx, '1'])
                manual_zoom.add(clip)
                n_zoom += 1
        try:
            if not pl.resolve_clip(clip, content):
                missing.append(clip)
        except ValueError:
            missing.append(clip)
    rows = [[i + 1, *row[1:]] for i, row in enumerate(built)]

    words = sum(len(r[1].split()) for r in rows if r[1] != '[zoom]')
    msg = (f"Đã chuyển **{len(rows)} nhịp** (~{words / 180 * 60:.0f} giây đọc, chưa tính "
           f"khoảng nghỉ). Mỗi nhịp đã gắn sẵn ảnh ở cột cuối; mặc định **không phụ đề** "
           f"(`|| -`, chữ đã nằm trên ảnh) — nhịp nào muốn phụ đề thì thay `-` bằng chữ.")
    if recovered:
        msg = (f"🔎 Đã tự nhận diện bài nguồn từ ảnh trong kịch bản: `{res.get('dir')}` — "
               "không cần bấm bước 1 lại.\n\n" + msg)
    if n_ctx:
        msg += (f" {n_ctx} nhịp reply kèm khung ngữ cảnh cha (↳ + trích đoạn, không hiện "
                f"tên) khi dựng video.")
    if n_zoom:
        msg += (f" {n_zoom} mục có ảnh đính kèm (bài gốc/comment) được **thêm 1 nhịp zoom** "
                f"ở cuối mục: card phóng to, ẩn phụ đề, đi kèm nhạc. Bấm chip **Zoom** trên "
                f"nhịp để tắt, hoặc xoá nhịp nếu không cần.")
    if n_sound_zoom:
        msg += (f" {n_sound_zoom} mục chỉ có ảnh: nhịp tiếng có sẵn được bật zoom luôn "
                f"(không thêm nhịp thứ hai nên tiếng không bị lặp).")
    if missing:
        uniq = list(dict.fromkeys(missing))
        msg += (f"\n\n⚠️ {len(missing)} nhịp trỏ tới ảnh không tìm thấy trong "
                f"`assets/illus/{content}/`: " + ", ".join(f"`{m}`" for m in uniq[:5]))
    warns = sd.lint_rows(rows)
    if warns:
        msg += "\n\n⚠️ **Cần rà:** " + "; ".join(warns) + "."
    cards = [(i["rel"], i["rel"]) for i in res.get("images", [])]
    # bảng nhịp dùng '-' làm ký hiệu 'không phụ đề' -> ô xem thử khung coi như rỗng
    first = (rows[0][2] if rows and rows[0][2] != "-" else "") if rows else ""
    # điền luôn ô 'Nội dung' để xem thử khung / xuất video tìm đúng thư mục minh họa
    # (luồng dán kịch bản mà không bấm bước 1 thì ô này còn trống)
    return (res, rows, msg, {'value': content},
            {'choices': cards, 'value': rows[0][4] if rows else None}, first)

def _auto_schedule_draft(video: str) -> tuple[str, str, str]:
    """Chuẩn bị hẹn Facebook sau khi xuất: caption + giờ tự điền, user tự bấm Lên lịch.

    Trả về (caption, giờ dạng 'dd/mm/YYYY HH:MM', ghi chú) — chưa đụng gì tới Facebook.
    """
    try:
        tags = (fb.load_config().get("hashtags") or "").strip()
        caption, _src = _fb_caption_for(video, tags)
    except Exception as e:  # noqa: BLE001 — chuẩn bị thất bại không được làm mất video
        return "", _fb_suggest_time(), f"⚠ Không soạn được caption tự động: {e}"
    if not (caption or "").strip():
        note = "⚠ Không tìm được bài nguồn để soạn caption — viết caption bên dưới rồi hẹn."
    else:
        note = "✅ Đã điền caption + giờ gợi ý. Kiểm tra, sửa nếu cần rồi bấm **📅 Lên lịch**."
    return caption, _fb_suggest_time(), note

# --------------------------------------------------------------------------- Facebook
def _fb_dataset_for(video: str) -> Path | None:
    """Bài Threads đã tạo ra video này (file ghi kèm lúc xuất, không có thì đoán theo giờ)."""
    p = Path(video)
    meta = p.with_suffix(".json")
    if meta.is_file():
        try:
            content = (json.loads(meta.read_text(encoding="utf-8")) or {}).get("content") or ""
        except (OSError, ValueError, AttributeError):
            content = ""
        if content:
            f = pl.ILLUS_DIR / content / "post" / "threads.json"
            if f.is_file():
                return f
    try:
        made = Path(video).stat().st_mtime
    except OSError:
        return None
    best: tuple[float, Path] | None = None
    try:
        files = list(pl.ILLUS_DIR.glob("*/post/threads.json"))
    except OSError:
        files = []
    for f in files:
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if m > made + 60 or made - m > 86400 * 3:
            continue
        if best is None or m > best[0]:
            best = (m, f)
    return best[1] if best else None

def _fb_script_for(video: str) -> Path | None:
    """Tìm kịch bản video thường theo sidecar hoặc tên content trong output."""
    p = Path(video)
    candidates: list[str] = []
    meta = p.with_suffix(".json")
    if meta.is_file():
        try:
            content = (json.loads(meta.read_text(encoding="utf-8")) or {}).get("content") or ""
            if content:
                candidates.append(str(content))
        except (OSError, ValueError, AttributeError):
            pass
    stem = p.stem
    if stem.startswith("video_"):
        candidates.append(stem[6:].rsplit("_", 1)[0])
    for content in candidates:
        script = pl.ILLUS_DIR / content / "kich-ban.txt"
        if script.is_file():
            return script
    return None

def _script_hook(text: str) -> str:
    """Nhịp mở đầu (hook) của kịch bản video thường — câu mở caption khi lên lịch."""
    beats = pl.parse_script(text or "")
    return beats[0].spoken if beats else ""


def _fb_caption_for(video: str, tags: str = "", fallback: str = "") -> tuple[str, str]:
    """(caption, nguồn) cho một video: ưu tiên caption chung, không thì soạn từ bài gốc."""
    if (fallback or "").strip():
        return fallback.strip(), "caption chung"
    src = _fb_script_for(video) or _fb_dataset_for(video)
    if src is None:
        return "", "—"
    try:
        if src.name == "kich-ban.txt":
            data = {"post": {"text": src.read_text(encoding="utf-8")}, "comments": []}
        else:
            data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "", "—"
    post = data.get("post") or {}
    extra = [(c.get("text") or "") for c in (data.get("comments") or [])[:3]]
    name = src.parent.parent.name if src.name == "threads.json" else src.parent.name
    topic = "Mẹo / kiến thức" if src.name == "kich-ban.txt" else "Tự nhận diện"
    hook = _script_hook(post.get("text") or "") if src.name == "kich-ban.txt" else ""
    opts = cap.make_options(post.get("text") or "", name, tags, extra, topic, hook=hook)
    if not opts:
        return "", "—"
    return opts[0]["caption"], name

def _fb_sources() -> list[tuple[str, str]]:
    """Caption sources from scanned Threads posts and prepared regular scripts."""
    out: list[tuple[str, str]] = []
    try:
        files = sorted(
            [*pl.ILLUS_DIR.glob("*/post/threads.json"),
             *pl.ILLUS_DIR.glob("*/kich-ban.txt")],
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        files = []
    for f in files:
        try:
            if f.name == "kich-ban.txt":
                text = f.read_text(encoding="utf-8").strip()
                if not text:
                    continue
                out.append((f"{f.parent.name} · video thường", str(f)))
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        post = data.get("post") or {}
        if not (post.get("text") or "").strip():
            continue
        n = len(data.get("comments") or [])
        out.append((f"{f.parent.parent.name} · @{post.get('handle', '?')} · {n} comment",
                    str(f)))
    return out

def on_fb_default_caption(video, tags=""):
    """Caption mặc định của một video: phương án 1; không có nguồn thì để trống."""
    return _fb_caption_for(video, tags or "")

def _fb_rows(page, token, version) -> tuple[list[list], list[tuple[str, str]]]:
    items = fb.list_scheduled(page, token, version)
    rows = [[it["id"], it["when"],
             " ".join((it["message"] or "(không có caption)").split())[:110]]
            for it in items]
    choices = [(f"{it['when']} · {it['id']} · "
                f"{' '.join((it['message'] or '').split())[:40]}", it["id"]) for it in items]
    return rows, choices

def _fb_creds(page, token, version) -> tuple[str, str, str]:
    """Page/token/version: ô nào để trống thì dùng giá trị đã lưu trên máy.

    Nhờ vậy token không cần hiện lại trong giao diện (và không lọt vào /config),
    nhưng vẫn đăng được ở lần mở app sau.
    """
    cfg = fb.load_config()
    page = (page or "").strip() or (cfg.get("page_id") or "").strip()
    token = (token or "").strip() or (cfg.get("token") or "").strip()
    version = ((version or "").strip() or (cfg.get("version") or "").strip()
               or fb.DEFAULT_VERSION)
    return page, token, version

def _fb_env_note() -> str:
    """Dòng trạng thái: Page ID/token đang lấy từ đâu."""
    src = fb.creds_source()
    if src == "env":
        return ("✅ Đang dùng **Page ID + token từ biến môi trường** của máy "
                "(`FB_PAGE_ID`, `FB_PAGE_TOKEN`).")
    if src == "env-file":
        return "✅ Đang dùng **Page ID + token từ `work/fb.env`**."
    if src == "config":
        return ("✅ Đang dùng Page ID + token đã lưu trong `work/fb_config.json` "
                "(nhập ở ô bên dưới nếu cần đổi).")
    return ("⚠ Chưa có Page ID/token. Đặt biến môi trường `FB_PAGE_ID`, `FB_PAGE_TOKEN` "
            "(hoặc tạo `work/fb.env`) rồi mở lại app — hoặc nhập tay ở ô bên dưới.")

def _fb_suggest_time() -> str:
    """Giờ đăng gợi ý mặc định: 11:30 gần nhất còn ≥ 15 phút nữa."""
    now = datetime.now()
    for add in (0, 1):
        day = now + timedelta(days=add)
        when = day.replace(hour=11, minute=30, second=0, microsecond=0)
        if when >= now + timedelta(minutes=15):
            return when.strftime("%d/%m/%Y %H:%M")
    return (now + timedelta(days=1)).replace(hour=11, minute=30, second=0,
                                             microsecond=0).strftime("%d/%m/%Y %H:%M")

def on_fb_save(page, token, version, tags):
    """Chỉ lưu thứ người dùng gõ; token lấy từ env không bị ghi xuống file."""
    fields = {"version": (version or "").strip() or fb.DEFAULT_VERSION,
              "hashtags": (tags or "").strip()}
    if (page or "").strip():
        fields["page_id"] = page.strip()
    if (token or "").strip():
        fields["token"] = token.strip()
    fb.save_config(**fields)
    note = _fb_env_note()
    if not (token or "").strip() and fb.creds_source() in ("env", "env-file"):
        note += "\n\nToken từ env không bị ghi vào `work/fb_config.json`."
    return "✅ Đã lưu cấu hình.\n\n" + note

def on_fb_check(page, token, version):
    page, token, version = _fb_creds(page, token, version)
    if not page or not token:
        return "❌ Chưa có Page ID hoặc token.\n\n" + _fb_env_note()
    try:
        info = fb.check(page, token, version)
    except fb.FbError as e:
        return f"❌ {e}"
    src = {"env": "biến môi trường", "env-file": "`work/fb.env`",
           "config": "`work/fb_config.json`"}.get(fb.creds_source(), "ô nhập tay")
    return (f"✅ Token khớp Page: **{info.get('name')}** (ID `{info.get('id')}`)."
            + f"\n\nNguồn token: {src}.")

def on_fb_schedule(page, token, version, video, file, caption, tags, when, now,
                   progress=_noop_progress):
    page, token, version = _fb_creds(page, token, version)
    # Chỉ lưu version/hashtag; Page ID + token lấy từ env không bị ghi xuống file.
    fb.save_config(version=version, hashtags=(tags or "").strip())
    cfg = fb.load_config()
    path = file
    if isinstance(path, list):
        path = path[0] if path else ""
    path = (path or video or "").strip()
    if not path:
        raise AppError("Chọn video trong `output/` hoặc tải một file video lên.")
    final = fb.append_tags(caption or "", tags or "")
    try:
        progress(0.02, desc="Đang kiểm tra Page…")
        info = fb.check(page, token, version)
        progress(0.10, desc="Đang tải Reel lên Facebook…")
        if now:
            res = fb.upload_reel(page, token, path, final, None, version, cfg)
            msg = (f"✅ Facebook đã nhận lệnh đăng Reel lên **{info.get('name')}**. Reel ID `{res.get('id')}`. "
                   f"Facebook xử lý video vài phút rồi bài mới hiện.")
        else:
            dt = fb.parse_when(when)
            res = fb.schedule_reel(page, token, path, final, dt, version, cfg)
            msg = (f"✅ Đã hẹn Reel **{dt:%d/%m/%Y %H:%M}** trên **{info.get('name')}**. "
                   f"Facebook tự đăng lúc đó (app tắt vẫn được). Reel ID `{res.get('id')}`.")
        fb.mark_posted(path, res.get("id", ""), None if now else dt)
        progress(0.90, desc="Đang tải danh sách bài đã hẹn…")
        try:
            rows, choices = _fb_rows(page, token, version)
        except fb.FbError:
            # Facebook đã gỡ endpoint liệt kê bài hẹn; việc liệt kê thất bại
            # không được phép át thông báo đăng thành công.
            rows, choices = [], []
            msg += ("\n\n(Không tải được danh sách bài đang chờ từ Facebook, nhưng bài của bạn "
                    "vẫn đã được tạo thành công. Kiểm tra trong Meta Business Suite.)")
        return (msg, {'value': rows}, {'choices': choices, 'value': None},
                {'value': ""})
    except fb.FbError as e:
        raise AppError(str(e)) from e
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise AppError(f"Lỗi khi đăng: {e}") from e

def on_fb_list(page, token, version):
    page, token, version = _fb_creds(page, token, version)
    try:
        rows, choices = _fb_rows(page, token, version)
    except fb.FbError as e:
        raise AppError(str(e)) from e
    msg = (f"{len(rows)} bài đang chờ đăng." if rows
           else "Chưa có bài nào đang chờ (bài vừa hẹn có thể mất vài giây mới hiện).")
    return rows, {'choices': choices, 'value': None}, msg

def on_fb_cancel(page, token, version, post_id):
    if not post_id:
        raise AppError("Chọn bài cần huỷ trong danh sách trước đã.")
    page, token, version = _fb_creds(page, token, version)
    try:
        fb.cancel_scheduled(post_id, token, version)
        fb.unmark_posted(post_id)
        rows, choices = _fb_rows(page, token, version)
    except fb.FbError as e:
        raise AppError(str(e)) from e
    return (f"🗑 Đã huỷ bài `{post_id}`. Video tương ứng đã về lại danh sách chưa đăng.",
            {'value': rows}, {'choices': choices, 'value': None})

def on_check():
    lines = []
    try:
        ff = pl.ffmpeg_path()
        ver = subprocess.run([ff, "-version"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout.splitlines()[0]
        lines.append(f"✅ FFmpeg: {ver}")
        enc = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
        flt = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
        lines.append("✅ Mã hóa H.264 (libx264)" if "libx264" in enc else "❌ Thiếu libx264")
        lines.append("✅ Bộ vẽ chữ (ass/libass)" if " ass " in flt else "❌ Thiếu bộ lọc ass — chữ sẽ không hiện")
        lines.append("ℹ️ FFmpeg có hỗ trợ NVENC (xuất bằng GPU NVIDIA). Có chạy được hay không tùy card và driver — "
                     "thử bật ở tab 'Làm video', lỗi thì tắt đi"
                     if "h264_nvenc" in enc else "ℹ️ Bản FFmpeg này không có NVENC (dùng CPU để xuất)")
    except Exception as e:  # noqa: BLE001
        lines.append(f"❌ FFmpeg: {e}")
    try:
        import vieneu  # noqa: F401
        lines.append("✅ Thư viện giọng đọc vieneu đã cài")
    except Exception as e:  # noqa: BLE001
        lines.append(f"❌ vieneu: {e}")
    lines.append(f"ℹ️ Thư mục app: {pl.APP_DIR}")
    return "\n".join(lines)
