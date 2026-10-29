"""Giao diện web chạy trên máy bạn: python -m videomaker (hoặc bấm run.bat)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import traceback
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

import gradio as gr

from . import caption as cap
from . import comment_manager as cm
from . import script_draft as sd
from . import threads_editorial as editorial
from . import pipeline as pl
from . import threads_shot as ts
from . import fb_post as fb
from .paths import CONFIG_DIR

EXAMPLE = """# Mỗi dòng là một nhịp. [thẻ] ở đầu dòng dùng để chọn clip meme (có thể bỏ trống).
# Muốn chữ hiển thị khác lời đọc thì thêm || chữ hiển thị
# Từ quan trọng thì bao bằng dấu sao: *50 KM/H* (sẽ to hơn và đổi màu, không bị đọc ra)
[sốc] Bình thường thì trong giới giải trí, mọi thứ đều rất êm đềm
[sốc] Nhưng sự sụp đổ của công ty này thì khác hẳn
[im lặng] Thứ duy nhất bạn cần làm là im lặng
Im lặng là vàng
"""

BACKENDS = [("Giọng thật (VieNeu-TTS)", pl.BACKEND_VIENEU),
            ("Chế độ thử (tiếng bíp, không cần tải model)", pl.BACKEND_DUMMY)]
HEADERS = ["#", "Lời đọc", "Chữ hiển thị", "Thẻ", "Clip meme (tên file, để trống = không có)"]
# Bảng nhịp của tab Threads có thêm cột ngữ cảnh cha cho reply (cột 6, pipeline đọc tuỳ chọn);
# giá trị giữ '@tên: trích' để người sửa biết cha là ai, nhưng video chỉ vẽ ↳ + trích đoạn (ẩn danh)
THREAD_HEADERS = HEADERS + ["Ngữ cảnh cha (↳ trích đoạn cha)"]


# --------------------------------------------------------------------------- lưu / khôi phục cấu hình
SETTINGS_FILE = CONFIG_DIR / "settings.json"
_SAVE_LOCK = threading.Lock()

# Thứ tự khớp đúng tham số của make_opts()
OPT_KEYS = ["backend", "voice", "speed", "bg", "upper", "font", "font_size", "text_color",
            "outline_color", "outline_w", "text_y", "max_words", "pop", "meme_y", "meme_w",
            "meme_h", "carry", "use_music", "music_vol", "nvenc", "emph_color", "emph_scale",
            "content", "gap", "threads_radius", "threads_side_margin", "threads_shadow", "threads_padding", "threads_max_height", "threads_padding_top", "threads_padding_right", "threads_padding_bottom", "threads_padding_left", "threads_zoom", "card_motion", "karaoke", "bg_motion", "pop_in", "sfx", "fps", "mascot"]

DEFAULTS = {
    "backend": pl.BACKEND_VIENEU, "voice": "", "speed": 1.0, "bg": "ngẫu nhiên",
    "upper": True, "font": "Segoe UI Black", "font_size": 120, "text_color": "#FF9A1F",
    "outline_color": "#FFFFFF", "outline_w": 9, "text_y": 1010, "max_words": 4, "pop": True,
    "meme_y": 210, "meme_w": 960, "meme_h": 560, "carry": True, "use_music": False,
    "music_vol": 0.08, "nvenc": False, "emph_color": "#FFE600", "emph_scale": 1.3,
    "script": EXAMPLE, "content": "", "gap": pl.GAP, "threads_radius": 0, "threads_side_margin": 108,
    "threads_shadow": 0, "threads_padding": 0, "threads_max_height": 640, "threads_zoom": 140,
    "threads_padding_top": -1, "threads_padding_right": -1, "threads_padding_bottom": -1, "threads_padding_left": -1,
    "card_motion": True, "karaoke": True, "bg_motion": True, "pop_in": True, "sfx": True, "fps": 60, "mascot": True,
    "threads_scrape": {"top": 20, "mode": "auto", "ident": "avatar", "nested": True,
                       "reply_depth": 1, "reply_min_likes": 10, "reply_per_parent": 2},
}

_SLIDERS = {"speed": (0.8, 1.4), "font_size": (60, 200), "outline_w": (0, 20),
            "text_y": (300, 1700), "max_words": (1, 8), "meme_y": (60, 800),
            "meme_w": (300, 1080), "meme_h": (200, 900), "music_vol": (0.02, 0.4),
            "emph_scale": (1.0, 1.8), "gap": (0.0, 2.0), "threads_radius": (0, 80),
            "threads_zoom": (100, 200), "threads_side_margin": (0, 120), "threads_shadow": (0, 100), "threads_padding": (0, 200), "threads_max_height": (200, 1000), "fps": (24, 60),
            **{f"threads_padding_{side}": (-1, 200) for side in ("top", "right", "bottom", "left")}}
_INT_KEYS = {"font_size", "outline_w", "text_y", "max_words", "meme_y", "meme_w", "meme_h", "threads_radius", "threads_side_margin", "threads_shadow", "threads_padding", "threads_max_height", "threads_padding_top", "threads_padding_right", "threads_padding_bottom", "threads_padding_left", "threads_zoom", "fps"}
_FLOAT_KEYS = {"speed", "music_vol", "emph_scale", "gap"}
_BOOL_KEYS = {"upper", "pop", "carry", "use_music", "nvenc", "card_motion", "karaoke", "bg_motion", "pop_in", "sfx", "mascot"}
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
    if key in ("voice", "script"):
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
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
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
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_FILE.with_name(SETTINGS_FILE.name + ".tmp")
        tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, SETTINGS_FILE)
    return str(SETTINGS_FILE)


def _save_field(key, value) -> None:
    try:
        save_settings(**{key: value})
    except OSError:
        pass  # ổ đầy / file bị khóa: app vẫn chạy, chỉ là lần sau không nhớ thông số này


def _persist_all(opt_values) -> None:
    try:
        save_settings(**dict(zip(OPT_KEYS, opt_values)))
    except OSError:
        pass


def on_save(script_text, *opt_values) -> str:
    save_settings(script=script_text or "", **dict(zip(OPT_KEYS, opt_values)))
    return ("✅ Đã lưu cấu hình vào `config/settings.json`. Lần sau mở app, các thông số và kịch bản này "
            "được dùng lại ngay. (Muốn về mặc định: xóa file `config/settings.json`.)")


# --------------------------------------------------------------------------- hàm hỗ trợ
def bg_choices() -> list[str]:
    return ["ngẫu nhiên"] + [p.name for p in pl.list_backgrounds()]


def library_markdown() -> str:
    lib = pl.scan_memes()
    parts = []
    if lib:
        parts.append("**Thư viện meme (dùng chung mọi video, theo thẻ cảm xúc):**")
        for tag, files in sorted(lib.items()):
            names = ", ".join(pl.clip_label(f) for f in files[:6])
            more = f" … (+{len(files) - 6})" if len(files) > 6 else ""
            parts.append(f"- `{tag}` — {len(files)} clip: {names}{more}")
    else:
        parts.append("**Thư viện meme đang trống.**")
    bgs = pl.list_backgrounds()
    parts.append(f"\n**Video nền:** {', '.join(p.name for p in bgs) if bgs else 'chưa có'}")
    mus = pl.list_music()
    parts.append(f"\n**Nhạc nền:** {', '.join(p.name for p in mus) if mus else 'chưa có'}")
    contents = pl.list_contents()
    if contents:
        parts.append("\n**Thư viện minh họa theo nội dung** (assets/illus/<nội dung>/<thẻ>/…):")
        for c in contents:
            ill = pl.scan_illust(c)
            n = sum(len(v) for v in ill.values())
            tags = ", ".join(f"`{t}`" for t in sorted(ill))
            parts.append(f"- `{c}` — {n} file ({tags})")
    else:
        parts.append("\n**Thư viện minh họa theo nội dung đang trống.**")
    return "\n".join(parts)


def safe_name(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', " ", s or "").strip()
    return s or "khac"


def _files(files) -> list[Path]:
    if not files:
        return []
    out = []
    for f in files if isinstance(files, list) else [files]:
        out.append(Path(f if isinstance(f, (str, Path)) else getattr(f, "name", str(f))))
    return out


def make_opts(backend, voice, speed, bg, upper, font, font_size, text_color, outline_color,
              outline_w, text_y, max_words, pop, meme_y, meme_w, meme_h, carry,
              use_music, music_vol, nvenc, emph_color, emph_scale, content, gap=pl.GAP,
              threads_radius=0, threads_side_margin=0, threads_shadow=0,
              threads_padding=0, threads_max_height=640, threads_padding_top=-1,
              threads_padding_right=-1, threads_padding_bottom=-1, threads_padding_left=-1, threads_zoom=140,
              card_motion=True, karaoke=True, bg_motion=True, pop_in=True, sfx=True,
              fps=60, mascot=True) -> pl.Options:
    return pl.Options(
        backend=backend, voice=voice or "", speed=float(speed), bg=bg or "ngẫu nhiên",
        content=(content or "").strip(), gap=float(gap),
        upper=bool(upper), font=(font or "Segoe UI Black").strip(), font_size=int(font_size),
        text_color=text_color or "#FF9A1F", outline_color=outline_color or "#FFFFFF",
        outline_w=int(outline_w), text_y=int(text_y), max_words=int(max_words), pop=bool(pop),
        meme_y=int(meme_y), meme_w=int(meme_w), meme_h=int(meme_h), carry=bool(carry),
        use_music=bool(use_music), music_volume=float(music_vol), nvenc=bool(nvenc),
        emph_color=emph_color or "#FFE600", emph_scale=float(emph_scale),
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
        mascot=bool(mascot),
    )


# --------------------------------------------------------------------------- xử lý sự kiện
def on_analyze(script, content):
    rows = pl.analyze(script or "", content=content.strip() or "")
    if not rows:
        raise gr.Error("Kịch bản đang trống. Mỗi dòng là một nhịp, dòng bắt đầu bằng # bị bỏ qua.")
    n_clip = sum(1 for r in rows if r[4])
    msg = f"Đã tách {len(rows)} dòng, gán được clip cho {n_clip} dòng. Sửa bảng bên dưới nếu cần rồi bấm xem thử."
    if n_clip == 0:
        msg += " (Chưa có clip nào khớp thẻ — thêm clip vào tab 'Thư viện' hoặc gõ tên file vào cột cuối.)"
    return rows, msg


def on_load_voices(backend, current):
    try:
        voices = pl.list_voices(backend)
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"Không tải được danh sách giọng: {e}") from e
    if not voices:
        raise gr.Error("Không có giọng nào.")
    # giữ giọng đang chọn (đã lưu từ lần trước) nếu vẫn còn trong danh sách
    keep = current if any(value == current for _, value in voices) else voices[0][1]
    return gr.update(choices=voices, value=keep), f"Đã tải {len(voices)} giọng."


def on_sample(backend, voice, speed, text):
    text = (text or "").strip() or "Xin chào, đây là giọng đọc thử."
    try:
        wav = pl.synth(text, backend, voice or "", float(speed))
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"Lỗi tạo giọng: {e}") from e
    return str(wav)


def _do_render(rows, opts, preview, progress):
    try:
        out = pl.render(rows, opts, preview=preview,
                        cb=lambda f, m: progress(f, desc=m))
    except (ValueError, RuntimeError) as e:
        raise gr.Error(str(e)) from e
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise gr.Error(f"Lỗi không mong đợi: {e}") from e
    return out


def on_preview(rows, *opt_values, progress=gr.Progress()):
    _persist_all(opt_values)
    out = _do_render(rows, make_opts(*opt_values), True, progress)
    return str(out), "Đây là bản xem thử nhanh (chất lượng thấp). Ưng rồi thì bấm 'Xuất video đẹp'."


def on_export(rows, *opt_values, progress=gr.Progress()):
    _persist_all(opt_values)
    out = _do_render(rows, make_opts(*opt_values), False, progress)
    return str(out), f"Đã xuất: {out}"


def on_frame(text, *opt_values):
    """Dựng 1 khung hình theo bố cục hiện tại — xem trước mà không phải xuất video."""
    if not (text or "").strip():
        raise gr.Error("Chưa có chữ để xem thử.")
    opt = make_opts(*opt_values)
    try:
        img, chunks = pl.preview_frame(text, opt)
    except (ValueError, RuntimeError) as e:
        raise gr.Error(str(e)) from e
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise gr.Error(f"Lỗi không mong đợi: {e}") from e
    md = (f"**{len(chunks)} cụm chữ** (tối đa {opt.max_words} từ/cụm): "
          + " · ".join(f"`{c}`" for c in chunks)
          + "\n\nẢnh trên là **cụm đầu tiên**. Đổi thông số rồi bấm lại là thấy ngay, "
            "không cần xuất video.")
    return str(img), md


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


def on_threads_login(progress=gr.Progress()):
    try:
        ts.save_login(progress=progress)
    except RuntimeError as e:
        raise gr.Error(str(e)) from e
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise gr.Error(f"Lỗi khi đăng nhập: {e}") from e
    return ts.session_status()


def on_threads_logout():
    if ts.STATE_FILE.exists():
        ts.STATE_FILE.unlink()
    return ts.session_status()


def on_threads_scrape(url, t_content, tag, top, mode, ident="avatar", nested=True,
                      reply_depth=1, reply_min_likes=10, reply_per_parent=2,
                      progress=gr.Progress()):
    url = (url or "").strip()
    if not re.match(r"^https?://", url):
        raise gr.Error("Hãy dán link post Threads (bắt đầu bằng https://).")
    try:
        res = ts.run(ts.Run(url=url, content=(t_content or "").strip(),
                            tag=(tag or "post").strip() or "post",
                            top=int(top or 0), mode=mode or "auto",
                            ident=ident or "avatar", nested_replies=bool(nested),
                            reply_depth=int(reply_depth), reply_min_likes=int(reply_min_likes),
                            reply_per_parent=int(reply_per_parent)),
                     progress=progress)
    except RuntimeError as e:
        raise gr.Error(str(e)) from e
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise gr.Error(f"Lỗi khi lấy bài: {e}") from e

    found, used = res["stats"]["comments_found"], res["stats"]["comments_used"]
    msg = (f"Đã lấy **1 bài + {used} comment** (trang có {found} comment) và ghi "
           f"{len(res['images'])} ảnh vào `{res['dir']}`.")
    if found > used:
        msg += "\n\nMuốn lấy thêm: tăng **Số comment** rồi bấm lấy lại."
    nested_stats = res["stats"].get("nested") or {}
    if not nested_stats.get("disabled", True):
        msg += f"\n\nReply lồng: thêm **{nested_stats.get('replies_added', 0)}** reply."
        if nested_stats.get("failures"):
            msg += f" Có {nested_stats['failures']} trang comment không đọc được; kiểm tra phiên đăng nhập."
        if nested_stats.get("limited") or nested_stats.get("depth_limit"):
            msg += " Đã chạm giới hạn số trang hoặc độ sâu, có thể còn reply chưa lấy hết."
    hidden = res["stats"].get("replies_hidden") or 0
    if hidden:
        msg += (f"\n\n⚠ Threads báo bài có **{res['stats']['replies_total']} reply** nhưng chỉ trả "
                f"**{found}** — còn **{hidden} reply chưa lấy được**.")
        if res["stats"].get("logged_in"):
            msg += (" Threads chỉ tải một phần reply mỗi lượt; reply lồng dưới một comment "
                    "phải mở riêng comment đó mới thấy.")
        else:
            msg += (" Bấm **🔑 Đăng nhập Threads** ở trên rồi lấy lại để có đủ.")
    items = _threads_item_rows(res)
    cards = [(i["rel"], i["rel"]) for i in res["images"]]
    draft = ts.build_editable_script(res)
    hint = ("Bản nguyên văn — cầm nó cho AI làm sạch theo quy tắc TTS rồi dán lại, "
            "hoặc tự sửa tay, sau đó bấm **2. Chuyển thành Các nhịp**.")
    msg += ("\n\n📄 Kịch bản chữ bên dưới là **bản nguyên văn** (đủ mọi comment đã lấy). "
            "Muốn bản đọc trôi: cầm nó cho AI chỉnh theo quy tắc TTS rồi dán lại vào ô này.")
    return ([i["path"] for i in res["images"]],
            gr.update(value=items), msg, res,
            gr.update(value=res["content"]),
            gr.update(choices=cards, value=res["images"][0]["rel"] if cards else None),
            "",
            ts.session_status(),
            draft, hint, gr.update(value=[]),
            None)


def _threads_item_rows(res: dict) -> list[list]:
    return cm.table_rows(res)


def on_threads_comment_action(state, rows, script, image, action):
    """Nút riêng trên mỗi comment; không dùng trạng thái chọn hàng hoặc ô tick."""
    comments = (state or {}).get("comments") or []
    identity = next((i for i, c in enumerate(comments, 1) if c.get("image") == image), None)
    if identity is None:
        raise gr.Error("Comment đã thay đổi hoặc đã bị xóa. Hãy dùng danh sách hiện tại.")
    try:
        draft = cm.validate_rows(rows, len(comments))
        for row in draft:
            row[1] = action == "delete" and int(row[0]) == identity
        if action in ("up", "down"):
            draft = cm.move_row(draft, identity, -1 if action == "up" else 1)
        elif action != "delete":
            raise ValueError("Thao tác comment không hợp lệ.")
    except ValueError as e:
        raise gr.Error(str(e)) from e
    return on_threads_manage(state, draft, script)


def on_threads_sort_commit(state, rows, script, mode):
    try:
        draft = (cm.sort_likes(rows) if mode == "likes"
                 else cm.sort_time(state or {}, rows, newest=mode == "newest"))
    except ValueError as e:
        raise gr.Error(str(e)) from e
    return on_threads_manage(state, draft, script)


def on_threads_manage(state, rows, script):
    """Áp dụng thứ tự / bỏ comment khỏi video; đồng bộ kịch bản và ảnh, giữ file nguồn."""
    if not state or not state.get("post"):
        raise gr.Error("Bấm '1. Lấy bài + comment' trước đã.")
    try:
        res = cm.apply_draft(state, rows)
    except ValueError as e:
        raise gr.Error(str(e)) from e
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
        raise gr.Error(f"Không lưu được danh sách comment: {e}") from e
    cards = [(i["rel"], i["rel"]) for i in res["images"]]
    removed = len(state.get("comments") or []) - len(res["comments"])
    msg = f"Đã cập nhật thứ tự, bỏ {removed} comment. Còn {len(res['comments'])} comment."
    items = _threads_item_rows(res)
    return (res, gr.update(value=items),
            [i["path"] for i in res["images"]],
            gr.update(choices=cards, value=cards[0][1] if cards else None),
            new_script, "Bấm **2. Chuyển thành Các nhịp** để dùng danh sách mới.", msg,
            gr.update(value=[]), None, None, "Danh sách đã thay đổi; hãy dựng lại video.")


def on_threads_script(state):
    """Tạo lại kịch bản chữ nguyên bản từ dữ liệu đã lấy (bỏ mọi chỉnh sửa tay)."""
    res = state or {}
    if not res.get("post"):
        raise gr.Error("Bấm '1. Lấy bài + comment' trước đã.")
    return (ts.build_editable_script(res),
            "Đã tạo lại kịch bản chữ từ dữ liệu gốc. Sửa xong bấm **2. Chuyển thành "
            "Các nhịp**.")


def on_threads_import_script(file, state):
    if not state or not state.get("post"):
        raise gr.Error("Lấy bài + comment trước khi nạp kịch bản.")
    if not file:
        raise gr.Error("Chọn file kịch bản UTF-8 (.txt hoặc .md).")
    try:
        text = Path(file).read_text(encoding="utf-8-sig")
        checked = editorial.validate_script(state, text)
        # Giữ bản nguồn trước khi áp dụng tuyển chọn, không mất pool comment để biên tập lại.
        backup = Path(state["dir"], "threads-source.json")
        if not state.get("editorial_source"):
            backup.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        state = {**state, "editorial_source": str(backup)}
        selected = checked["images"]
        rows = cm.table_rows(state)
        for row, comment in zip(rows, state.get("comments") or []):
            image = comment.get("image")
            row[1] = image not in selected
            row[2] = selected.index(image) if image in selected else len(selected) + row[0]
        result = list(on_threads_manage(state, rows, text))
        result[5] = (f"Đã nạp {checked['comments']} comment, {checked['beats']} nhịp. "
                     "Bấm **2. Chuyển thành Các nhịp**.")
        return tuple(result)
    except (OSError, UnicodeError, ValueError) as e:
        raise gr.Error(f"Không nạp được kịch bản: {e}") from e


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
            raise gr.Error(
                "Chưa có dữ liệu bài Threads. Bấm **1. Lấy bài + comment**, hoặc dùng "
                "kịch bản có dòng `# …png` trỏ tới ảnh của một bài đã lấy trước đó "
                "(app tự nhận diện bài nguồn từ tên ảnh).")

    sections = ts.parse_sections(text or "")
    if not sections:
        raise gr.Error("Chưa đọc được mục ảnh nào. Mỗi ảnh phải bắt đầu bằng một dòng "
                       "`# ten-file-anh.png` rồi bên dưới là các dòng đọc.")
    content = res.get("content", "")
    tag = (res.get("tag") or "post").strip() or "post"

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
        raise gr.Error(f'Không thể chuyển đủ dòng đọc ({len(rows)}/{len(clips)}). '
                       'Kiểm tra các dòng trống hoặc chỉ có ký hiệu trong kịch bản.')

    missing: list[str] = []
    n_ctx = 0
    n_zoom = 0
    manual_zoom = {clip for row, clip in zip(rows, clips) if row[1] == '[zoom]'}
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
        if ts.has_media(res, clip) and clip not in manual_zoom:
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
    return (res, rows, msg, gr.update(value=content),
            gr.update(choices=cards, value=rows[0][4] if rows else None), first)


def on_threads_frame(text, clip, rows, t_content, *opt_values):
    opt = threads_opts(t_content, *opt_values)
    text = (text or "").strip()
    # ngữ cảnh cha của ảnh đang chọn (nếu là reply): lấy từ cột 6 của bảng nhịp
    ctx = next((str(r[5]) for r in (rows or [])
                if len(r) > 5 and str(r[4] or "") == (clip or "") and str(r[5] or "").strip()), "")
    try:
        img, chunks = pl.preview_frame(text, opt, clip or "", ctx)
    except (ValueError, RuntimeError) as e:
        raise gr.Error(str(e)) from e
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise gr.Error(f"Lỗi không mong đợi: {e}") from e
    if text:
        md = (f"**{len(chunks)} cụm chữ**: " + " · ".join(f"`{c}`" for c in chunks)
              + "\n\nCard phủ đủ bề ngang khung, chữ chạy sát ngay dưới đáy card — đây "
                "chính là bố cục video khi xuất.")
    else:
        md = ("**Không phụ đề** (nhịp `|| -`): không vẽ chữ, card phủ đủ bề ngang và canh "
              "**giữa dọc khung** (thấp hơn chính giữa một chút để né nút tương tác "
              "TikTok/Reels bên phải). Muốn xem bố cục có chữ thì gõ câu vào ô 'Câu hiển thị'.")
    if ctx:
        md = ("Có **khung ngữ cảnh cha (↳)** phía trên ảnh reply — khung chỉ ghép khi dựng, "
              "ảnh gốc vẫn nguyên riêng biệt.\n\n") + md
    return str(img), md


def on_threads_preview(rows, t_content, *opt_values, progress=gr.Progress()):
    _persist_all(opt_values)
    out = _do_render(rows, threads_opts(t_content, *opt_values), True, progress)
    return str(out), "Bản xem thử nhanh (chất lượng thấp). Ưng rồi bấm 'Xuất video đẹp'."


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


def on_threads_fb_schedule(video, caption, when, progress=gr.Progress()):
    """Nút Lên lịch: đúng flow của tab Facebook nhưng chạy tại chỗ với video vừa xuất."""
    if not video or not Path(video).is_file():
        raise gr.Error("Chưa có video nào vừa xuất — bấm **4. Xuất video đẹp** trước đã.")
    text = (caption or "").strip()
    if not text:
        raise gr.Error("Caption đang trống — điền caption trước khi lên lịch.")
    page, token, version = _fb_creds("", "", "")
    if not page or not token:
        raise gr.Error("Chưa có Page ID/token — kết nối ở tab **Đăng Facebook Reels** "
                       "(biến môi trường / work/fb.env) rồi bấm lại.")
    try:
        progress(0.05, desc="Đang kiểm tra Page…")
        info = fb.check(page, token, version)
        dt = fb.parse_when(when)
        if dt < datetime.now() + timedelta(minutes=15):
            raise gr.Error("Giờ hẹn phải cách hiện tại ít nhất 15 phút.")
        progress(0.25, desc="Đang tải Reel lên lịch…")
        cfg = fb.load_config()
        tags = (cfg.get("hashtags") or "").strip()
        res = fb.schedule_reel(page, token, video, fb.append_tags(text, tags), dt, version, cfg)
        fb.mark_posted(video, res.get("id", ""), dt)
        progress(1.0, desc="Xong")
        return (f"✅ Đã hẹn: **{dt:%d/%m/%Y %H:%M}** trên **{info.get('name')}**. "
                f"Xem hoặc huỷ ở tab **Đăng Facebook Reels**.")
    except fb.FbError as e:
        raise gr.Error(str(e)) from e


def on_threads_export(rows, t_content, fbprep, *opt_values, progress=gr.Progress()):
    _persist_all(opt_values)
    out = _do_render(rows, threads_opts(t_content, *opt_values), False, progress)
    status = f"Đã xuất: {out}"
    if fbprep:
        caption, when, note = _auto_schedule_draft(str(out))
    else:
        caption, when, note = gr.update(), gr.update(), ""
    return str(out), status, caption, when, note


# --------------------------------------------------------------------------- Facebook
def _fb_video_choices() -> list[tuple[str, str]]:
    """(nhãn, đường dẫn) các video đã xuất trong output/, mới nhất trước."""
    out: list[tuple[str, str]] = []
    try:
        files = sorted(pl.OUT_DIR.glob("*.mp4"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        files = []
    for p in files:
        try:
            if p.stat().st_size <= 0:
                continue
        except OSError:
            continue
        out.append((fb.describe_video(p), str(p)))
    return out


FB_SLOTS = {"2/ngày": ((11, 30), (20, 0)), "1/ngày": ((20, 0),)}


def _fb_batch_choices() -> list[tuple[str, str]]:
    """(nhãn có ghi chú đã hẹn, đường dẫn) cho danh sách tích hàng loạt."""
    log = fb.posted_log()
    out: list[tuple[str, str]] = []
    for label, path in _fb_video_choices():
        item = log.get(Path(path).name) or {}
        when = (item.get("when") or "").strip() if isinstance(item, dict) else ""
        note = f" · đã hẹn {when}" if when and when != "ngay" else (" · đã đăng" if when else "")
        out.append((label + note, path))
    return out


def _fb_plan(count: int, pattern: str) -> list[datetime]:
    """Các mốc giờ trống kế tiếp theo nhịp đăng, bỏ qua giờ đã hẹn trước đó."""
    now = datetime.now()
    earliest = now + timedelta(minutes=15)
    slots = FB_SLOTS.get(pattern) or FB_SLOTS["2/ngày"]
    booked = fb.booked_times()
    out: list[datetime] = []
    for day in range(0, 90):
        d = now + timedelta(days=day)
        for hour, minute in slots:
            when = d.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if when < earliest or when.strftime("%Y-%m-%d %H:%M") in booked:
                continue
            out.append(when)
            if len(out) >= count:
                return out
    return out


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


def _fb_caption_for(video: str, tags: str = "", fallback: str = "") -> tuple[str, str]:
    """(caption, nguồn) cho một video: ưu tiên caption chung, không thì soạn từ bài gốc."""
    if (fallback or "").strip():
        return fallback.strip(), "caption chung"
    src = _fb_dataset_for(video)
    if src is None:
        return "", "—"
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "", "—"
    post = data.get("post") or {}
    extra = [(c.get("text") or "") for c in (data.get("comments") or [])[:3]]
    name = src.parent.parent.name
    opts = cap.make_options(post.get("text") or "", name, tags, extra)
    if not opts:
        return "", "—"
    return opts[0]["caption"], name


def on_fb_refresh(selected, pattern, current):
    choices = _fb_batch_choices()
    available = {path for _label, path in choices}
    selected = [v for v in (selected or []) if v in available]
    return (gr.update(choices=choices, value=selected),
            on_fb_edit_rows(selected, pattern, current), _fb_env_note())


def on_fb_edit_rows(videos, pattern, current, reset_times=False, shared=None):
    """Mỗi video một hàng; giữ bản sửa khi thêm/bỏ video khỏi danh sách."""
    vids = [v for v in (videos or []) if v and Path(v).is_file()]
    old = {r[0]: r for r in (current or []) if len(r) == 3}
    plan = _fb_plan(len(vids), pattern) if vids else []
    if len(plan) < len(vids):
        raise gr.Error("Không xếp đủ giờ trống trong 90 ngày tới.")
    rows = []
    for video, when in zip(vids, plan):
        name = Path(video).name
        prev = old.get(name)
        text = prev[2] if prev else _fb_caption_for(video)[0]
        if shared is not None:
            text = shared.strip() if shared.strip() else _fb_caption_for(video)[0]
        stamp = prev[1] if prev and not reset_times else when.strftime("%d/%m/%Y %H:%M")
        rows.append([name, stamp, text])
    return gr.update(value=rows)


def on_fb_batch_schedule(videos, pattern, caption, tags, edits=None, progress=gr.Progress()):
    """Hẹn giờ hàng loạt: mỗi video một mốc giờ trống kế tiếp, caption tự soạn theo bài gốc."""
    page, token, version = _fb_creds("", "", "")
    if not page or not token:
        raise gr.Error("Chưa có Page ID/token.\n\n" + _fb_env_note())
    vids = [v for v in (videos or []) if v and Path(v).is_file()]
    if not vids:
        raise gr.Error("Chưa tích video nào. Tích ở danh sách **1. Video cần đăng** trước đã.")
    tags = (tags or "").strip()
    fb.save_config(version=version, hashtags=tags)
    plan = _fb_plan(len(vids), pattern)
    if len(plan) < len(vids):
        raise gr.Error("Không xếp đủ giờ trống trong 90 ngày tới. Chọn ít video hơn.")
    # Chốt và kiểm tra toàn bộ hàng trước khi gọi Facebook.
    by_name = {r[0]: r for r in (edits or []) if len(r) == 3}
    ready = []
    for video, when in zip(vids, plan):
        row = by_name.get(Path(video).name)
        if edits is not None and row is None:
            raise gr.Error("Danh sách video vừa thay đổi. Chờ bảng cập nhật rồi đăng lại.")
        text = str(row[2] or "").strip() if row else _fb_caption_for(video, tags, caption)[0]
        if not text:
            raise gr.Error(f"{Path(video).name}: hãy điền caption trong hàng của video.")
        if row:
            try:
                when = datetime.strptime(str(row[1]).strip(), "%d/%m/%Y %H:%M")
            except ValueError as e:
                raise gr.Error(f"{Path(video).name}: giờ đăng cần dạng ngày/tháng/năm giờ:phút.") from e
        if when < datetime.now() + timedelta(minutes=15):
            raise gr.Error(f"{Path(video).name}: chọn giờ đăng cách hiện tại ít nhất 15 phút.")
        ready.append((video, when, text))
    try:
        info = fb.check(page, token, version)
    except fb.FbError as e:
        raise gr.Error(str(e)) from e

    cfg = fb.load_config()
    done: list[str] = []
    fails: list[tuple[str, str]] = []
    total = len(vids)
    for i, (video, when, text) in enumerate(ready):
        name = Path(video).name
        progress(0.02 + 0.9 * i / total,
                 desc=f"Đang hẹn {name} — {when:%d/%m %H:%M} ({i + 1}/{total})…")
        if not text.strip():
            fails.append((name, "không có caption và không tìm được bài gốc"))
            continue
        try:
            res = fb.schedule_reel(page, token, video, fb.append_tags(text, tags),
                                    when, version, cfg)
            fb.mark_posted(video, res.get("id", ""), when)
            done.append(f"{when:%d/%m %H:%M} · `{name}`")
        except fb.FbError as e:
            fails.append((name, str(e)))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            fails.append((name, str(e)))

    progress(0.94, desc="Đang tải danh sách bài đã hẹn…")
    try:
        rows, choices = _fb_rows(page, token, version)
    except fb.FbError:
        rows, choices = [], []
    batch = _fb_batch_choices()
    msg = f"✅ Đã hẹn **{len(done)}/{total}** Reel lên **{info.get('name')}**."
    if done:
        msg += "\n\n" + "\n".join(f"- {d}" for d in done)
    if fails:
        msg += f"\n\n❌ {len(fails)} video lỗi:\n\n" + "\n".join(
            f"- `{n}`: {e}" for n, e in fails)
    msg += "\n\nFacebook tự đăng đúng giờ — app tắt vẫn chạy. Xem ở **Bài đang chờ đăng**."
    failed_names = {name for name, _error in fails}
    remaining = [v for v in vids if Path(v).name in failed_names]
    return (msg, gr.update(value=rows), gr.update(choices=choices, value=None),
            gr.update(choices=batch, value=remaining),
            gr.update(value="Bấm **Đăng lên lịch tất cả** để chốt danh sách vừa hẹn."),
            on_fb_edit_rows(remaining, pattern, edits))


def _fb_sources() -> list[tuple[str, str]]:
    """(nhãn, đường dẫn `threads.json`) của các bài Threads đã cào, mới nhất trước."""
    out: list[tuple[str, str]] = []
    try:
        files = sorted(pl.ILLUS_DIR.glob("*/post/threads.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        files = []
    for f in files:
        try:
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


def _fb_read(src: str | None) -> tuple[dict, Path]:
    """Đọc threads.json của bài đã chọn (rỗng = bài mới nhất)."""
    path = Path(src) if src else None
    if path is None or not path.is_file():
        rows = _fb_sources()
        if not rows:
            raise gr.Error("Chưa có bài Threads nào — bấm **1. Lấy bài + comment** ở tab "
                           "Threads trước.")
        path = Path(rows[0][1])
    try:
        return json.loads(path.read_text(encoding="utf-8")), path
    except (OSError, ValueError) as e:
        raise gr.Error(f"Không đọc được dữ liệu bài Threads: {e}") from e


def on_fb_caption(src):
    """Điền nguyên văn bài Threads đã chọn vào ô caption."""
    data, path = _fb_read(src)
    text = ((data.get("post") or {}).get("text") or "").strip()
    if not text:
        raise gr.Error("Bài này không có chữ nào.")
    handle = (data.get("post") or {}).get("handle", "?")
    return text, f"Đã điền nguyên văn bài của @{handle} (`{path.parent.parent.name}`)."


def on_fb_caption_targets(videos, target):
    videos = videos or []
    return gr.update(choices=[(Path(v).name, v) for v in videos],
                     value=target if target in videos else None)


def on_fb_caption_target(video, rows):
    row = next((r for r in (rows or []) if video and r[0] == Path(video).name), None)
    src = _fb_dataset_for(video) if row else None
    return (video if row else None, row[2] if row else "",
            gr.update(value=str(src) if src else None), [],
            gr.update(choices=[], value=None, visible=False), "",
            (f"Đang sửa caption cho **{Path(video).name}**."
             + ("" if src else " Không tìm được bài gốc; hãy chọn bài nguồn trước khi tạo gợi ý."))
            if row else "Chọn video cần sửa caption ở trên.", "Tự nhận diện")


def _fb_require_caption_target(video, owner, src=None):
    if not video or owner != video:
        raise gr.Error("Chọn video cần sửa caption và chờ nội dung tải xong.")
    if src is not None and not Path(src).is_file():
        raise gr.Error("Chọn bài nguồn cho video này trước khi tạo caption.")


def on_fb_gen_target(video, owner, src, tags, topic="Tự nhận diện"):
    _fb_require_caption_target(video, owner, src or "")
    return (*on_fb_gen(src, tags, topic), video)


def on_fb_original_target(video, owner, src):
    _fb_require_caption_target(video, owner, src or "")
    text, note = on_fb_caption(src)
    return text, note, video


def on_fb_apply_caption(video, owner, text, rows):
    _fb_require_caption_target(video, owner)
    if not any(r[0] == Path(video).name for r in (rows or [])):
        raise gr.Error("Video này đã bị bỏ khỏi danh sách đăng.")
    updated = [[r[0], r[1], text if r[0] == Path(video).name else r[2]] for r in rows]
    return gr.update(value=updated), f"Đã cập nhật caption cho **{Path(video).name}**."


def on_fb_gen(src, tags, topic="Tự nhận diện"):
    """3 bản nháp caption theo skill facebook-reels-caption."""
    data, path = _fb_read(src)
    post = data.get("post") or {}
    extra = [(c.get("text") or "") for c in (data.get("comments") or [])[:3]]
    opts = cap.make_options(post.get("text") or "", path.parent.parent.name, tags, extra, topic)
    if not opts:
        raise gr.Error("Bài này không có chữ nào để viết caption.")
    titles = [o["title"] for o in opts]
    note = "Đã điền bản đầu vào ô soạn. Bấm Lưu caption cho video đã chọn để cập nhật hàng."
    return (opts, gr.update(choices=titles, value=titles[0], visible=True),
            opts[0]["caption"], cap.report(opts[0]), note)


def on_fb_use(opts, title):
    for o in opts or []:
        if o.get("title") == title:
            return o["caption"], cap.report(o)
    return gr.update(), ""


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
    """Giờ đăng gợi ý: 11:30 hoặc 20:00 gần nhất còn ≥ 15 phút nữa."""
    now = datetime.now()
    for add in (0, 1):
        day = now + timedelta(days=add)
        for hour, minute in ((11, 30), (20, 0)):
            when = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if when >= now + timedelta(minutes=15):
                return when.strftime("%d/%m/%Y %H:%M")
    return (now + timedelta(days=1)).replace(hour=20, minute=0, second=0,
                                             microsecond=0).strftime("%d/%m/%Y %H:%M")


def on_fb_open_tab(selected, pattern, current):
    """Đồng bộ lựa chọn và các hàng ngay khi mở tab, giữ nội dung đã sửa."""
    return on_fb_refresh(selected, pattern, current)


def on_fb_pick_video(video):
    """Chọn video khác -> gợi ý lại giờ đăng (vẫn sửa tay được)."""
    if not video:
        return gr.update(), "Chọn video đã xuất trong `output/`."
    return _fb_suggest_time(), ""


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


def on_fb_refresh_video():
    rows = _fb_video_choices()
    return gr.update(choices=rows, value=rows[0][1] if rows else None)


def on_fb_tags(text, tags):
    raw = (tags or "").strip()
    if not raw:
        raise gr.Error("Nhập hashtag vào ô 'Hashtag mặc định' trước đã.")
    before = set(re.findall(r"#\w+", text or ""))
    out = fb.append_tags(text or "", raw)
    added = [t for t in re.findall(r"#\w+", out) if t not in before]
    dropped = fb.dropped_tags(raw)
    note = ("Đã chèn: " + " ".join(added) if added
            else "Không thêm tag mới (caption đã có các tag đó).")
    if dropped:
        note += ("\n\n⚠ Đã bỏ: " + ", ".join("#" + d for d in dropped) +
                 " — skill khuyên tối đa 5 tag cụ thể, tránh tag chung chung "
                 "(#viral, #reels, #xuhuong…).")
    return out, note


def on_fb_slot(kind):
    """Gợi ý nhanh giờ đăng: tối nay 20:00 · trưa mai 11:30 · tối mai 20:00."""
    now = datetime.now()
    hour, minute, add = {"toi-nay": (20, 0, 0),
                         "trua-mai": (11, 30, 1),
                         "toi-mai": (20, 0, 1)}.get(kind, (20, 0, 0))
    when = (now + timedelta(days=add)).replace(hour=hour, minute=minute,
                                               second=0, microsecond=0)
    if when <= now + timedelta(minutes=11):
        when += timedelta(days=1)
    return when.strftime("%d/%m/%Y %H:%M")


def on_fb_schedule(page, token, version, video, file, caption, tags, when, now,
                   progress=gr.Progress()):
    page, token, version = _fb_creds(page, token, version)
    # Chỉ lưu version/hashtag; Page ID + token lấy từ env không bị ghi xuống file.
    fb.save_config(version=version, hashtags=(tags or "").strip())
    cfg = fb.load_config()
    path = file
    if isinstance(path, list):
        path = path[0] if path else ""
    path = (path or video or "").strip()
    if not path:
        raise gr.Error("Chọn video trong `output/` hoặc tải một file video lên.")
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
        rows, choices = _fb_rows(page, token, version)
        return (msg, gr.update(value=rows), gr.update(choices=choices, value=None),
                gr.update(value=""))
    except fb.FbError as e:
        raise gr.Error(str(e)) from e
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise gr.Error(f"Lỗi khi đăng: {e}") from e


def on_fb_list(page, token, version):
    page, token, version = _fb_creds(page, token, version)
    try:
        rows, choices = _fb_rows(page, token, version)
    except fb.FbError as e:
        raise gr.Error(str(e)) from e
    msg = (f"{len(rows)} bài đang chờ đăng." if rows
           else "Chưa có bài nào đang chờ (bài vừa hẹn có thể mất vài giây mới hiện).")
    return rows, gr.update(choices=choices, value=None), msg


def on_fb_cancel(page, token, version, post_id):
    if not post_id:
        raise gr.Error("Chọn bài cần huỷ trong danh sách trước đã.")
    page, token, version = _fb_creds(page, token, version)
    try:
        fb.cancel_scheduled(post_id, token, version)
        fb.unmark_posted(post_id)
        rows, choices = _fb_rows(page, token, version)
    except fb.FbError as e:
        raise gr.Error(str(e)) from e
    batch = _fb_batch_choices()
    return (f"🗑 Đã huỷ bài `{post_id}`. Video tương ứng đã về lại danh sách chưa đăng.",
            gr.update(value=rows), gr.update(choices=choices, value=None),
            gr.update(choices=batch, value=[]),
            gr.update(value=[]))


def on_add_memes(tag, files):
    paths = _files(files)
    if not paths:
        raise gr.Error("Chưa chọn file nào.")
    if not (tag or "").strip():
        raise gr.Error("Hãy nhập thẻ cảm xúc (ví dụ: sốc, im lặng, cười).")
    dest = pl.MEME_DIR / safe_name(tag)
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in paths:
        if p.suffix.lower() in (pl.VIDEO_EXT | pl.IMAGE_EXT):
            shutil.copy(p, dest / p.name)
            n += 1
    return library_markdown(), f"Đã thêm {n} file vào thẻ '{tag}'."


def on_add_bg(files):
    paths = [p for p in _files(files) if p.suffix.lower() in pl.VIDEO_EXT]
    if not paths:
        raise gr.Error("Hãy chọn file video (mp4, mov, mkv…).")
    for p in paths:
        shutil.copy(p, pl.BG_DIR / p.name)
    return library_markdown(), gr.update(choices=bg_choices()), f"Đã thêm {len(paths)} video nền."


def on_add_music(files):
    paths = [p for p in _files(files) if p.suffix.lower() in pl.AUDIO_EXT]
    if not paths:
        raise gr.Error("Hãy chọn file nhạc (mp3, wav…).")
    for p in paths:
        shutil.copy(p, pl.MUSIC_DIR / p.name)
    return library_markdown(), f"Đã thêm {len(paths)} file nhạc."


def on_add_illust(content, tag, files):
    """Thêm ảnh minh họa vào thư viện của đúng nội dung: assets/illus/<content>/<tag>/."""
    content = (content or "").strip()
    if not content:
        raise gr.Error("Hãy chọn/nhập tên nội dung trước (ví dụ: chientranhemu).")
    tag = (tag or "").strip()
    if not tag:
        raise gr.Error("Hãy nhập thẻ chủ thể (ví dụ: emu, lua-mi, cuu-binh).")
    paths = _files(files)
    if not paths:
        raise gr.Error("Chưa chọn file nào.")
    dest = pl.ILLUS_DIR / safe_name(content) / safe_name(tag)
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in paths:
        if p.suffix.lower() in (pl.VIDEO_EXT | pl.IMAGE_EXT):
            shutil.copy(p, dest / p.name)
            n += 1
    return library_markdown(), f"Đã thêm {n} file vào minh họa '{content}/{tag}'."


def on_add_fonts(files):
    paths = [p for p in _files(files) if p.suffix.lower() in {".ttf", ".otf", ".ttc"}]
    if not paths:
        raise gr.Error("Hãy chọn file font (.ttf, .otf).")
    for p in paths:
        shutil.copy(p, pl.FONT_DIR / p.name)
    return (f"Đã thêm {len(paths)} font. Gõ đúng TÊN FONT (family) vào ô 'Tên font' ở tab 'Làm video' "
            "(mở file font bằng Windows để xem tên).")


def asset_choices() -> list[tuple[str, str]]:
    """Danh sách mọi file trong thư viện, để chọn xóa. value = 'loại|đường dẫn tương đối'."""
    items: list[tuple[str, str]] = []
    for tag, files in sorted(pl.scan_memes().items()):
        for p in files:
            rel = pl.clip_label(p)
            items.append((f"🎞️ meme: {rel}", f"meme|{rel}"))
    for p in pl.list_backgrounds():
        rel = p.relative_to(pl.BG_DIR).as_posix()
        items.append((f"🖼️ nền: {rel}", f"bg|{rel}"))
    for p in pl.list_music():
        rel = p.relative_to(pl.MUSIC_DIR).as_posix()
        items.append((f"🎵 nhạc: {rel}", f"music|{rel}"))
    for p in sorted(pl.FONT_DIR.glob("*")):
        if p.is_file():
            items.append((f"🔤 font: {p.name}", f"font|{p.name}"))
    return items


_KIND_DIR = {"meme": pl.MEME_DIR, "bg": pl.BG_DIR, "music": pl.MUSIC_DIR, "font": pl.FONT_DIR}


def on_delete_assets(selected):
    if not selected:
        raise gr.Error("Chưa chọn file nào để xóa.")
    deleted, failed = 0, []
    for item in selected:
        kind, _, rel = item.partition("|")
        base = _KIND_DIR.get(kind)
        if base is None:
            continue
        target = (base / rel).resolve()
        # chặn việc xóa ra ngoài thư mục thư viện
        if base.resolve() not in target.parents:
            failed.append(rel)
            continue
        try:
            target.unlink()
            deleted += 1
            # xóa luôn thư mục thẻ nếu đã trống
            parent = target.parent
            if parent != base.resolve() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError as e:  # file đang được dùng (Windows) hoặc không còn tồn tại
            failed.append(f"{rel} ({e.__class__.__name__})")
    msg = f"Đã xóa {deleted} file."
    if failed:
        msg += " Không xóa được: " + ", ".join(failed)
    return (library_markdown(), gr.update(choices=bg_choices(), value="ngẫu nhiên"),
            gr.update(choices=asset_choices(), value=[]), msg)


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


# --------------------------------------------------------------------------- giao diện
def build_ui() -> gr.Blocks:
    cfg = load_settings()
    with gr.Blocks(title="Video Maker") as demo:
        gr.Markdown("# 🎬 Video Maker")

        with gr.Tabs():
            # ------------------------------------------------------------ tab 1
            with gr.Tab("Làm video"):
                with gr.Accordion("Hướng dẫn làm video", open=False):
                    gr.Markdown(
                        "Nhập kịch bản → **1. Phân tích** → sửa các nhịp → **2. Xem thử** → **3. Xuất video**.\n\n"
                        "Mỗi dòng là một nhịp. Dùng `[thẻ]` để chọn minh họa, `*từ*` để nhấn mạnh, "
                        "`lời đọc || chữ hiển thị` để tách lời và chữ.\n\n"
                        "Thông số được tự lưu. Lần đầu tải danh sách giọng có thể mất vài phút.")
                script = gr.Textbox(label="Kịch bản", lines=9, value=cfg["script"],
                                    placeholder="Mỗi dòng là một nhịp…")
                with gr.Row():
                    btn_analyze = gr.Button("1. Phân tích kịch bản", variant="primary")
                    status = gr.Markdown("")
                table = gr.Dataframe(headers=HEADERS, datatype=["number", "str", "str", "str", "str"],
                                     type="array", interactive=True, wrap=True,
                                     label="Bảng các dòng (sửa trực tiếp được)")
                with gr.Row():
                    btn_prev = gr.Button("2. Xem thử nhanh")
                    btn_exp = gr.Button("3. Xuất video đẹp", variant="primary")
                video = gr.Video(label="Kết quả", height=560)

                with gr.Accordion("🎙️ Giọng đọc", open=True):
                    backend = gr.Radio(BACKENDS, value=cfg["backend"], label="Kiểu giọng")
                    with gr.Row():
                        voice = gr.Dropdown(choices=[("Mặc định", "")], value=cfg["voice"], label="Giọng",
                                            allow_custom_value=True)
                        btn_voices = gr.Button("Tải danh sách giọng")
                    speed = gr.Slider(0.8, 1.4, value=cfg["speed"], step=0.05, label="Tốc độ đọc")
                    gap = gr.Slider(0, 2, value=cfg["gap"], step=0.01,
                                    label="Khoảng nghỉ giữa các nhịp (giây)",
                                    info="Dùng chung cho Làm video và Threads.")
                    with gr.Row():
                        sample_text = gr.Textbox(label="Câu đọc thử", value="Xin chào, đây là giọng đọc thử.")
                        btn_sample = gr.Button("Nghe thử")
                    sample_audio = gr.Audio(label="Âm thanh thử", type="filepath")

                with gr.Accordion("🎨 Bố cục & chữ", open=False):
                    with gr.Row():
                        bg = gr.Dropdown(choices=bg_choices(), value=cfg["bg"], label="Video nền")
                        content = gr.Dropdown(choices=pl.list_contents(), value=cfg.get("content", ""),
                                              label="Nội dung (thư viện minh họa)",
                                              allow_custom_value=True,
                                              info="Chọn bộ minh họa cho video.")
                    with gr.Row():
                        font = gr.Textbox(label="Tên font", value=cfg["font"])
                        font_size = gr.Slider(60, 200, value=cfg["font_size"], step=2, label="Cỡ chữ")
                        upper = gr.Checkbox(value=cfg["upper"], label="IN HOA")
                        pop = gr.Checkbox(value=cfg["pop"], label="Hiệu ứng nảy chữ")
                    with gr.Row():
                        text_color = gr.ColorPicker(value=cfg["text_color"], label="Màu chữ")
                        outline_color = gr.ColorPicker(value=cfg["outline_color"], label="Màu viền")
                        outline_w = gr.Slider(0, 20, value=cfg["outline_w"], step=1, label="Độ dày viền")
                    with gr.Row():
                        emph_color = gr.ColorPicker(value=cfg["emph_color"], label="Màu từ quan trọng (*từ*)")
                        emph_scale = gr.Slider(1.0, 1.8, value=cfg["emph_scale"], step=0.05,
                                               label="Từ quan trọng to gấp")
                    with gr.Row():
                        text_y = gr.Slider(300, 1700, value=cfg["text_y"], step=10,
                                           label="Vị trí chữ (từ trên xuống)")
                        max_words = gr.Slider(1, 8, value=cfg["max_words"], step=1,
                                              label="Số từ tối đa mỗi lần hiện")
                    with gr.Row():
                        meme_y = gr.Slider(60, 800, value=cfg["meme_y"], step=10, label="Vị trí khung meme")
                        meme_w = gr.Slider(300, 1080, value=cfg["meme_w"], step=10, label="Rộng khung meme")
                        meme_h = gr.Slider(200, 900, value=cfg["meme_h"], step=10, label="Cao khung meme")
                    carry = gr.Checkbox(value=cfg["carry"],
                                        label="Dòng không có thẻ thì giữ clip meme của dòng trước")
                    with gr.Row():
                        use_music = gr.Checkbox(value=cfg["use_music"], label="Thêm nhạc nền (từ thư mục nhạc)")
                        music_vol = gr.Slider(0.02, 0.4, value=cfg["music_vol"], step=0.01,
                                              label="Âm lượng nhạc")
                        nvenc = gr.Checkbox(value=cfg["nvenc"],
                                            label="Xuất bằng GPU NVIDIA")
                    with gr.Row():
                        frame_text = gr.Textbox(label="Câu xem thử", scale=4,
                                                value="Năm 1960, Ông A làm gì đó")
                        btn_frame = gr.Button("👁 Xem thử bố cục", scale=1, variant="primary")
                    frame_img = gr.Image(label="Khung hình xem thử", type="filepath", height=430)
                    frame_md = gr.Markdown("")

                with gr.Row():
                    btn_save = gr.Button("💾 Lưu cấu hình")
                    save_status = gr.Markdown("Đã bật tự lưu cấu hình.")

                opt_inputs = [backend, voice, speed, bg, upper, font, font_size, text_color, outline_color,
                              outline_w, text_y, max_words, pop, meme_y, meme_w, meme_h, carry,
                              use_music, music_vol, nvenc, emph_color, emph_scale, content, gap]

                # đổi thông số nào thì lưu ngay thông số đó (slider lưu lúc thả chuột để khỏi ghi liên tục)
                for _key, _comp in zip(OPT_KEYS, opt_inputs):
                    if _key in _SLIDERS:
                        _comp.release(partial(_save_field, _key), _comp, None)
                    else:
                        _comp.change(partial(_save_field, _key), _comp, None)
                script.change(partial(_save_field, "script"), script, None)

                btn_analyze.click(on_analyze, [script, content], [table, status])
                btn_voices.click(on_load_voices, [backend, voice], [voice, status])
                btn_sample.click(on_sample, [backend, voice, speed, sample_text], [sample_audio])
                btn_prev.click(on_preview, [table] + opt_inputs, [video, status])
                btn_exp.click(on_export, [table] + opt_inputs, [video, status])
                btn_save.click(on_save, [script] + opt_inputs, [save_status])
                btn_frame.click(on_frame, [frame_text] + opt_inputs, [frame_img, frame_md])

            # ------------------------------------------------------------ tab 2
            with gr.Tab("Thư viện"):
                with gr.Accordion("Tổng quan thư viện", open=False):
                    lib_md = gr.Markdown(library_markdown())
                lib_status = gr.Markdown("")
                with gr.Accordion("Hướng dẫn thư viện", open=False):
                    gr.Markdown(
                        "**Meme / ảnh:** đặt thẻ, ví dụ `sốc`; dòng kịch bản `[sốc]` sẽ dùng clip trong thẻ đó. "
                        "Thẻ không phân biệt hoa thường và dấu.\n\n"
                        "**Minh họa:** chọn tên nội dung và thẻ chủ thể. File được lưu trong "
                        "`assets/illus/<nội dung>/<thẻ>/`.\n\n"
                        "**Video nền:** nên dài từ 5 phút; app tự chọn đoạn để ghép.")
                gr.Markdown("### Thêm clip meme / ảnh")
                with gr.Row():
                    meme_tag = gr.Textbox(label="Thẻ", placeholder="sốc")
                    meme_files = gr.File(label="Clip / ảnh", file_count="multiple")
                btn_meme = gr.Button("Thêm vào thư viện meme")
                gr.Markdown("### Minh họa theo nội dung")
                with gr.Row():
                    ill_content = gr.Textbox(label="Tên nội dung", placeholder="chientranhemu")
                    ill_tag = gr.Textbox(label="Thẻ chủ thể", placeholder="emu, lua-mi")
                    ill_files = gr.File(label="Ảnh minh họa", file_count="multiple")
                btn_ill = gr.Button("Thêm minh họa theo nội dung")
                gr.Markdown("### Video nền")
                bg_files = gr.File(label="Video nền", file_count="multiple")
                btn_bg = gr.Button("Thêm video nền")
                gr.Markdown("### Nhạc nền / Font")
                music_files = gr.File(label="Nhạc (mp3, wav)", file_count="multiple")
                btn_music = gr.Button("Thêm nhạc")
                font_files = gr.File(label="Font (.ttf, .otf)", file_count="multiple")
                btn_font = gr.Button("Thêm font")
                btn_refresh = gr.Button("Làm mới danh sách")
                gr.Markdown("### Xóa file khỏi thư viện\n**File bị xóa vĩnh viễn khỏi ổ đĩa.**")
                del_select = gr.Dropdown(choices=asset_choices(), value=[], multiselect=True,
                                         label="File cần xóa")
                btn_delete = gr.Button("🗑️ Xóa các file đã chọn", variant="stop")

                refresh_del = lambda: gr.update(choices=asset_choices(), value=[])

                btn_meme.click(on_add_memes, [meme_tag, meme_files], [lib_md, lib_status]
                               ).then(refresh_del, None, [del_select])
                btn_ill.click(on_add_illust, [ill_content, ill_tag, ill_files], [lib_md, lib_status]
                              ).then(refresh_del, None, [del_select])
                btn_bg.click(on_add_bg, [bg_files], [lib_md, bg, lib_status]
                             ).then(refresh_del, None, [del_select])
                btn_music.click(on_add_music, [music_files], [lib_md, lib_status]
                                ).then(refresh_del, None, [del_select])
                btn_font.click(on_add_fonts, [font_files], [lib_status]
                               ).then(refresh_del, None, [del_select])
                btn_refresh.click(lambda: (library_markdown(), gr.update(choices=bg_choices()),
                                           gr.update(choices=asset_choices(), value=[])),
                                  None, [lib_md, bg, del_select])
                btn_delete.click(on_delete_assets, [del_select],
                                 [lib_md, bg, del_select, lib_status])

            # ------------------------------------------------------------ tab 3: Threads
            with gr.Tab("Threads"):
                gr.Markdown("### Threads → video — dán link, duyệt 2 lần, máy lo phần còn lại")
                with gr.Accordion("Hướng dẫn", open=False):
                    gr.Markdown(
                        "Dán link → **1. Lấy bài + comment** → sửa kịch bản → "
                        "**2. Chuyển thành Các nhịp** → nghe bản xem thử → **4. Xuất video đẹp**.\n\n"
                        "Bấm 2 và bấm 4 chính là hai lần duyệt của bạn — không bấm thì app "
                        "không tự chạy tiếp bước nào.\n\n"
                        "Lời đọc giữ nguyên văn bài gốc và comment, chỉ chuẩn hoá để đọc trôi. "
                        "Giọng đọc, màu chữ và nhạc dùng chung với tab **Làm video**.\n\n"
                        "Reply được đọc ngay sau comment cha, kèm khung nhỏ ngữ cảnh (↳ + 1–2 dòng "
                        "đang được trả lời, không hiện tên để giữ ẩn danh) phía trên ảnh. Khung chỉ "
                        "ghép lúc dựng video — ảnh cha và con vẫn lưu riêng.\n\n"
                        "Mở lại app mà lười lấy lại bài: cứ dán kịch bản chữ có dòng `# …png` "
                        "và bấm **2. Chuyển thành Các nhịp** — app tự nhận diện bài nguồn "
                        "từ tên ảnh đã lưu trong assets/illus.\n\n"
                        "Sau khi xuất, phần **📅 Hẹn Facebook** tự điền caption (soạn từ bài nguồn) "
                        "và giờ gợi ý — bạn kiểm tra, sửa rồi bấm **📅 Lên lịch**. App chỉ đăng khi "
                        "bạn bấm nút đó.")
                with gr.Row():
                    t_login_md = gr.Markdown(ts.session_status(), scale=5)
                    btn_t_login = gr.Button("🔑 Đăng nhập", scale=1, size="sm")
                    btn_t_logout = gr.Button("Xoá phiên", scale=1, size="sm")
                with gr.Row():
                    t_url = gr.Textbox(label="Link post Threads", scale=5,
                                       placeholder="https://www.threads.com/@user/post/xxxx")
                    t_content = gr.Dropdown(choices=pl.list_contents(), value="",
                                            label="Nội dung", scale=3, allow_custom_value=True,
                                            info="Mỗi bài một tên riêng để không đè nhau.")
                    t_top = gr.Slider(1, 20, value=20, step=1, label="Số comment cha",
                                      scale=2)
                btn_t_scrape = gr.Button("1. Lấy bài + comment", variant="primary")
                t_status = gr.Markdown("")

                gr.Markdown("### Kịch bản chữ (sửa trực tiếp)")
                t_script = gr.Textbox(lines=14, interactive=True, show_label=False,
                                      placeholder="Bấm '1. Lấy bài + comment' để có kịch bản…")
                t_script_status = gr.Markdown("")
                btn_t_build = gr.Button("2. Chuyển thành Các nhịp", variant="primary")

                with gr.Row():
                    btn_t_prev = gr.Button("3. Xem thử nhanh")
                    btn_t_exp = gr.Button("4. Xuất video đẹp", variant="primary")
                t_video_status = gr.Markdown("")
                t_video = gr.Video(label="Kết quả", height=560)

                with gr.Accordion("📅 Hẹn Facebook cho video vừa xuất", open=True):
                    t_fbprep = gr.Checkbox(
                        value=True, label="Sau khi xuất: tự điền caption + giờ gợi ý")
                    t_fb_caption = gr.Textbox(
                        label="Caption (sửa được)", lines=4,
                        placeholder="Bấm 4 xuất video — caption tự điền vào đây…")
                    with gr.Row():
                        t_fb_when = gr.Textbox(label="Giờ hẹn", scale=2,
                                               placeholder="dd/mm/YYYY HH:MM")
                        btn_t_fb_schedule = gr.Button("📅 Lên lịch", variant="primary", scale=1)
                    t_fb_status = gr.Markdown("")

                t_state = gr.State()
                t_comment_selected = gr.State(None)

                with gr.Accordion("🔍 Ảnh đã tạo & dữ liệu comment", open=False):
                    t_gallery = gr.Gallery(label="Ảnh đã tạo", columns=3,
                                           height=420, object_fit="contain")
                    t_items = gr.Dataframe(
                        value=[], headers=["#", "Bỏ", "Thứ tự", "Tài khoản", "Like", "Nội dung", "Giờ đăng (VN)"],
                        datatype=["number", "bool", "number", "str", "number", "str", "str"],
                        type="array", interactive=True, static_columns=[0, 3, 4, 5, 6],
                        column_count=7, wrap=True, max_height=460,
                        column_widths=["5%", "6%", "8%", "14%", "7%", "43%", "17%"],
                        label="Comment theo thứ tự đọc", visible=False)
                with gr.Accordion("⚙ Tuỳ chọn lấy bài (để mặc định là được)", open=False):
                    with gr.Row():
                        t_tag = gr.Textbox(label="Thẻ ảnh", value="post", scale=1,
                                           info="thư mục con trong nội dung")
                        t_mode = gr.Radio(
                            [("Tự động (chỉ có chữ → dựng card, có ảnh → chụp trang)", "auto"),
                             ("Luôn dựng card", "card"),
                             ("Luôn chụp trang", "shot")],
                            value="auto", label="Kiểu ảnh", scale=2)
                    t_ident = gr.Radio(
                        [("Ảnh đại diện + chữ 'Threads' (không lộ tên)", "avatar"),
                         ("Ảnh đại diện + tên tài khoản", "full"),
                         ("Ẩn ảnh đại diện, giữ tên", "no-avatar"),
                         ("Ẩn cả avatar lẫn tên", "anon")],
                        value="avatar", label="Tên & ảnh đại diện trên card",
                        info="Kiểu 'chụp trang' luôn tự chuyển sang dựng card khi đã ẩn tên/avatar.")
                    with gr.Accordion("Lấy reply lồng trong comment", open=False):
                        t_nested = gr.Checkbox(value=True, label="Lấy reply nổi bật trong comment đã chọn")
                        with gr.Row():
                            t_reply_min_likes = gr.Number(value=10, minimum=0, precision=0,
                                                          label="Like tối thiểu của reply")
                            t_reply_per_parent = gr.Slider(1, 5, value=2, step=1,
                                                           label="Reply tối đa mỗi cha")
                        t_reply_depth = gr.Slider(1, 4, value=1, step=1, label="Độ sâu reply tối đa",
                                                  info="Dùng phiên Threads đã đăng nhập; có thể mất thêm thời gian.")
                with gr.Accordion("🧮 Bảng Các nhịp (sửa nâng cao)", open=False):
                    t_rows = gr.Dataframe(headers=THREAD_HEADERS,
                                          datatype=["number", "str", "str", "str", "str", "str"],
                                          type="array", interactive=True, wrap=True,
                                          label="Các nhịp")
                with gr.Accordion("👁 Xem thử bố cục khung", open=False):
                    with gr.Row():
                        t_card = gr.Dropdown(choices=[], label="Ảnh để xem thử khung", scale=3)
                        t_frame_text = gr.Textbox(label="Câu hiển thị", scale=5)
                        btn_t_frame = gr.Button("👁 Xem thử khung", scale=1)
                    t_frame_img = gr.Image(label="Khung hình xem thử", type="filepath", height=430)
                    t_frame_md = gr.Markdown("")
                with gr.Accordion("📄 Nạp kịch bản từ file / tạo lại nguyên bản", open=False):
                    with gr.Row():
                        t_editorial_file = gr.File(label="Kịch bản đã biên tập", file_types=[".txt", ".md"],
                                                   type="filepath")
                        btn_t_import = gr.Button("Nạp và áp dụng tuyển chọn", size="sm")
                        btn_t_script = gr.Button("↻ Tạo lại kịch bản chữ", size="sm")

                btn_t_login.click(on_threads_login, None, [t_login_md])
                btn_t_logout.click(on_threads_logout, None, [t_login_md])
                btn_t_scrape.click(on_threads_scrape,
                                   [t_url, t_content, t_tag, t_top, t_mode, t_ident, t_nested,
                                    t_reply_depth, t_reply_min_likes, t_reply_per_parent],
                                   [t_gallery, t_items, t_status, t_state, t_content,
                                    t_card, t_frame_text, t_login_md, t_script,
                                    t_script_status, t_rows, t_comment_selected])
                comment_outputs = [t_state, t_items, t_gallery, t_card, t_script,
                                   t_script_status, t_status, t_rows, t_comment_selected,
                                   t_video, t_video_status]
                btn_t_import.click(on_threads_import_script, [t_editorial_file, t_state],
                                   comment_outputs, concurrency_id="threads-comment-edit")
                btn_t_script.click(on_threads_script, [t_state], [t_script, t_script_status])
                btn_t_build.click(on_threads_build, [t_script, t_state],
                                  [t_state, t_rows, t_script_status, t_content, t_card,
                                   t_frame_text])
                btn_t_frame.click(on_threads_frame,
                                  [t_frame_text, t_card, t_rows, t_content] + opt_inputs,
                                  [t_frame_img, t_frame_md])
                btn_t_prev.click(on_threads_preview, [t_rows, t_content] + opt_inputs,
                                 [t_video, t_video_status])
                btn_t_exp.click(on_threads_export, [t_rows, t_content, t_fbprep] + opt_inputs,
                                [t_video, t_video_status, t_fb_caption, t_fb_when, t_fb_status])
                btn_t_fb_schedule.click(on_threads_fb_schedule,
                                        [t_video, t_fb_caption, t_fb_when], [t_fb_status])

            # ------------------------------------------------------------ tab 4: Facebook
            with gr.Tab("Đăng Facebook Reels") as f_tab:
                with gr.Accordion("Hướng dẫn đăng Facebook", open=False):
                    gr.Markdown(
                        "Chọn video → kiểm tra caption và giờ đăng trong từng hàng → "
                        "**Đăng lên lịch tất cả**.\n\n"
                        "Caption được soạn từ bài nguồn, hashtag đặt ở cuối theo chủ đề. "
                        "Để tạo lại, mở **Sửa và gợi ý caption**, chọn video, tạo bản nháp rồi lưu.\n\n"
                        "Nhịp **2/ngày** dùng 11:30 và 20:00; **1/ngày** dùng 20:00. "
                        "Giờ Việt Nam; đổi nhịp sẽ xếp lại giờ của các hàng.\n\n"
                        "Chỉ đăng lên **Facebook Page**. Facebook tự đăng đúng giờ dù app đã tắt.")
                f_conn = gr.Markdown(_fb_env_note())

                _fbc = fb.load_config()
                _fb_src_kind = fb.creds_source()
                with gr.Accordion("⚙ Kết nối Facebook Page", 
                                  open=False):
                    gr.Markdown(
                        "Đặt biến môi trường trên máy rồi mở lại app:\n\n"
                        "```powershell\n"
                        "[Environment]::SetEnvironmentVariable('FB_PAGE_ID', '1234567890', 'User')\n"
                        "[Environment]::SetEnvironmentVariable('FB_PAGE_TOKEN', 'EAA…', 'User')\n"
                        "```\n\n"
                        "Hoặc tạo file `work/fb.env` với 2 dòng `FB_PAGE_ID=…` và `FB_PAGE_TOKEN=…` "
                        "(đọc lại mỗi lần đăng, không cần khởi động lại app). Token lấy từ env "
                        "**không bao giờ bị ghi xuống** `work/fb_config.json`.")
                    with gr.Row():
                        f_page = gr.Textbox(label="Page ID (chỉ khi không dùng env)", scale=3,
                                            value=_fbc.get("page_id", ""),
                                            placeholder="123456789012345")
                        f_token = gr.Textbox(
                            label="Page access token (chỉ khi không dùng env)", type="password",
                            scale=5, value="",
                            placeholder=("Đang dùng token từ env — để trống"
                                         if _fb_src_kind in ("env", "env-file")
                                         else ("Đã lưu token trên máy — để trống nếu không đổi"
                                               if (_fbc.get("token") or "").strip()
                                               else "EAA… (dán Page token dài hạn)")),
                            info="Lưu trong `work/fb_config.json` trên máy bạn, không hiện lại "
                                 "trong giao diện.")
                        f_version = gr.Textbox(label="API version", scale=1,
                                               value=_fbc.get("version") or fb.DEFAULT_VERSION)
                    with gr.Row():
                        btn_f_save = gr.Button("💾 Lưu", size="sm")
                        btn_f_check = gr.Button("🔌 Kiểm tra kết nối", size="sm")

                gr.Markdown("### 1. Video cần đăng")
                _fb_vids = _fb_batch_choices()
                with gr.Row():
                    f_batch = gr.Dropdown(
                        choices=_fb_vids, value=[], multiselect=True,
                        label="Chọn video cần đăng", filterable=True, scale=6,
                        info="Gõ tên để tìm, bấm × để bỏ chọn.")
                    btn_f_refresh = gr.Button("↻ Làm mới video", size="sm", scale=0,
                                              min_width=150)
                f_plan_md = gr.Markdown("", visible=False)

                gr.Markdown("### 2. Nội dung từng video")
                f_pattern = gr.Radio(
                    choices=["2/ngày", "1/ngày"], value="2/ngày", label="Xếp giờ đăng",
                    info="Đổi nhịp sẽ xếp lại giờ. Giờ Việt Nam.")
                gr.Markdown(
                    "Sửa caption và giờ đăng trực tiếp trong từng hàng.")
                f_edit_rows = gr.Dataframe(
                    value=[], headers=["Video", "Giờ đăng", "Caption"],
                    datatype=["str", "str", "str"], type="array", interactive=True,
                    static_columns=[0], column_count=3,
                    column_widths=["25%", "20%", "55%"], wrap=True,
                    max_height=640, label="Video sẽ đăng", show_row_numbers=True)
                with gr.Accordion("Sửa và gợi ý caption cho từng video", open=False):
                    f_caption_target = gr.Dropdown(
                        choices=[], value=None, label="Đang sửa caption cho video",
                        info="Chỉ cập nhật video đã chọn.")
                    f_caption_owner = gr.State(None)
                    f_caption = gr.Textbox(
                        label="Caption của video đã chọn", lines=5,
                        placeholder="Chọn video ở trên để tải caption…")
                    with gr.Accordion("Gợi ý caption từ bài Threads", open=False):
                        f_topic = gr.Dropdown(
                            choices=cap.TOPIC_CHOICES, value="Tự nhận diện",
                            label="Chủ đề cho gợi ý mới",
                            info="Tự nhận diện từ bài nguồn.")
                        _fb_src_rows = _fb_sources()
                        f_src = gr.Dropdown(
                            choices=_fb_src_rows, label="Bài nguồn của video đã chọn",
                            value=None)
                        with gr.Row():
                            btn_f_gen = gr.Button("Gợi ý 3 bản nháp", size="sm", variant="primary")
                            btn_f_caption = gr.Button("Dùng nguyên văn bài nguồn", size="sm")
                        f_opt = gr.Radio(choices=[], label="Chọn bản nháp", visible=False)
                        f_opt_md = gr.Markdown("")
                    btn_f_apply = gr.Button("Lưu caption cho video đã chọn", size="sm")
                    f_tags_md = gr.Markdown("")
                f_opt_state = gr.State([])
                with gr.Accordion("Hashtag cố định cho mọi video", open=False):
                    f_tags = gr.Textbox(
                        label="Hashtag chung", lines=2,
                        value=fb.normalize_tags(_fbc.get("hashtags", "")),
                        placeholder="#tenkenh #thuonghieu",
                        info="Luôn có #fyp #xuhuong #funny. Có thể thêm tag thương hiệu.")
                    btn_f_tags = gr.Button("Chèn vào caption đang sửa", size="sm")

                gr.Markdown("### 3. Chốt lịch")
                btn_f_batch = gr.Button("✅ Đăng lên lịch tất cả", variant="primary")
                f_msg = gr.Markdown("")

                gr.Markdown("### Bài đang chờ đăng")
                with gr.Row():
                    btn_f_list = gr.Button("↻ Tải danh sách", size="sm")
                    f_pick = gr.Dropdown(choices=[], label="Chọn bài để huỷ", scale=3)
                    btn_f_cancel = gr.Button("🗑 Huỷ bài đã chọn", size="sm", variant="stop")
                f_rows = gr.Dataframe(headers=["ID", "Giờ hẹn", "Caption"],
                                      datatype=["str", "str", "str"], type="array",
                                      interactive=False, wrap=True, label="Đã hẹn")

                with gr.Accordion("⚙ Tuỳ chọn: hẹn một video với giờ tự chọn", open=False):
                    with gr.Row():
                        _fb_single_vids = _fb_batch_choices()
                        f_video = gr.Dropdown(choices=_fb_single_vids,
                                              label="Video trong output/", scale=4,
                                              value=_fb_single_vids[0][1] if _fb_single_vids
                                              else None)
                        btn_f_refresh_video = gr.Button("↻ Làm mới", size="sm", scale=1)
                    f_file = gr.File(label="…hoặc tải video từ máy lên (nếu không chọn ở trên)",
                                     file_types=["video"], file_count="single", type="filepath")
                    f_single_caption = gr.Textbox(label="Caption cho video đăng riêng", lines=4)
                    with gr.Row():
                        f_when = gr.Textbox(label="Giờ hẹn", scale=3,
                                            value=_fb_suggest_time(),
                                            placeholder="28/10/2026 20:00")
                        f_now = gr.Checkbox(label="Đăng ngay", value=False, scale=1)
                        btn_f_schedule = gr.Button("📅 Đăng / Hẹn giờ", size="sm", scale=1)
                    with gr.Row():
                        gr.Markdown("Chọn nhanh:", scale=1)
                        btn_f_toinay = gr.Button("Tối nay 20:00", size="sm", scale=1)
                        btn_f_truamai = gr.Button("Trưa mai 11:30", size="sm", scale=1)
                        btn_f_toimai = gr.Button("Tối mai 20:00", size="sm", scale=1)
                    f_single_msg = gr.Markdown("")

                f_tab.select(on_fb_open_tab, [f_batch, f_pattern, f_edit_rows],
                             [f_batch, f_edit_rows, f_conn])
                btn_f_refresh.click(on_fb_refresh, [f_batch, f_pattern, f_edit_rows],
                                    [f_batch, f_edit_rows, f_conn])
                btn_f_save.click(on_fb_save, [f_page, f_token, f_version, f_tags], [f_conn])
                f_batch.change(on_fb_edit_rows, [f_batch, f_pattern, f_edit_rows],
                               [f_edit_rows]).then(
                    on_fb_caption_targets, [f_batch, f_caption_target], [f_caption_target])
                f_pattern.change(
                    partial(on_fb_edit_rows, reset_times=True),
                    [f_batch, f_pattern, f_edit_rows], [f_edit_rows])
                f_caption_target.change(
                    on_fb_caption_target, [f_caption_target, f_edit_rows],
                    [f_caption_owner, f_caption, f_src, f_opt_state, f_opt, f_opt_md, f_tags_md, f_topic])
                btn_f_apply.click(on_fb_apply_caption,
                                  [f_caption_target, f_caption_owner, f_caption, f_edit_rows],
                                  [f_edit_rows, f_tags_md])
                btn_f_check.click(on_fb_check, [f_page, f_token, f_version], [f_conn])
                btn_f_gen.click(on_fb_gen_target,
                                [f_caption_target, f_caption_owner, f_src, f_tags, f_topic],
                                [f_opt_state, f_opt, f_caption, f_opt_md, f_tags_md, f_caption_owner])
                f_opt.change(on_fb_use, [f_opt_state, f_opt], [f_caption, f_opt_md])
                btn_f_caption.click(on_fb_original_target,
                                    [f_caption_target, f_caption_owner, f_src],
                                    [f_caption, f_tags_md, f_caption_owner])
                btn_f_tags.click(on_fb_tags, [f_caption, f_tags], [f_caption, f_tags_md])
                btn_f_batch.click(on_fb_batch_schedule,
                                  [f_batch, f_pattern, f_caption, f_tags, f_edit_rows],
                                  [f_msg, f_rows, f_pick, f_batch, f_plan_md, f_edit_rows])
                btn_f_refresh_video.click(on_fb_refresh_video, None, [f_video])
                f_video.change(on_fb_pick_video, [f_video], [f_when, f_single_msg])
                for btn, kind in ((btn_f_toinay, "toi-nay"), (btn_f_truamai, "trua-mai"),
                                  (btn_f_toimai, "toi-mai")):
                    btn.click(partial(on_fb_slot, kind), None, [f_when])
                btn_f_schedule.click(on_fb_schedule,
                                     [f_page, f_token, f_version, f_video, f_file,
                                      f_single_caption, f_tags, f_when, f_now],
                                     [f_single_msg, f_rows, f_pick, f_when])
                btn_f_list.click(on_fb_list, [f_page, f_token, f_version],
                                 [f_rows, f_pick, f_msg])
                btn_f_cancel.click(on_fb_cancel, [f_page, f_token, f_version, f_pick],
                                   [f_msg, f_rows, f_pick, f_batch, f_edit_rows])

            # ------------------------------------------------------------ tab 5
            with gr.Tab("Kiểm tra máy"):
                btn_check = gr.Button("Kiểm tra cài đặt")
                check_out = gr.Textbox(label="Kết quả", lines=8)
                btn_check.click(on_check, None, [check_out])

    return demo


def main():
    pl.cleanup_old()
    build_ui().launch(server_name="127.0.0.1", inbrowser=not os.getenv("VIDEOMAKER_NO_BROWSER"),
                      allowed_paths=[str(pl.APP_DIR)])


if __name__ == "__main__":
    main()
