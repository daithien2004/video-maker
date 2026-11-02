"""Lõi dựng video: kịch bản -> giọng đọc -> chữ to -> ghép nền + clip meme -> MP4.

Mọi thứ nặng (mã hóa video) do FFmpeg làm. File này chỉ chuẩn bị dữ liệu và lệnh.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from . import next_card
from .paths import APP_DIR
ASSETS = APP_DIR / "assets"
BG_DIR = ASSETS / "backgrounds"
MEME_DIR = ASSETS / "memes"          # 🧠 THƯ VIỆN MEME dùng chung: mọi video cùng dùng, theo thẻ cảm xúc
ILLUS_DIR = ASSETS / "illus"        # 🎨 THƯ VIỆN MINH HỌA THEO NỘI DUNG: assets/illus/<tên-nội-dung>/...
MUSIC_DIR = ASSETS / "music"
FONT_DIR = ASSETS / "fonts"
OUT_DIR = APP_DIR / "output"
WORK_DIR = APP_DIR / "work"
CACHE_DIR = WORK_DIR / "cache"
for _d in (BG_DIR, MEME_DIR, MUSIC_DIR, FONT_DIR, OUT_DIR, WORK_DIR, CACHE_DIR, ILLUS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

W, H = 1080, 1920   # khung dọc; fps lấy theo opt.fps (mặc định 60)
LEAD = 0.25   # giây im lặng đầu video
GAP = 0.18    # khoảng nghỉ giữa các dòng
TAIL = 0.6    # giây im lặng cuối video
ZOOM_HOLD = 1.0   # giữ card đã phóng to thêm chút sau tiếng zoom cho kịp nhìn
ZOOM_IN = 0.18    # thời gian phóng + nảy của nhịp zoom
ZOOM_BACK = 2.2   # độ nảy: phóng vọt quá cỡ zoom rồi trở về đúng cỡ

BACKEND_VIENEU = "vieneu"
BACKEND_DUMMY = "dummy"

# Encoder CPU cho bản cuối (và cho lần xuất lại khi NVENC không lấy được VRAM).
CPU_VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]


# --------------------------------------------------------------------------- tiện ích
def _find_bin(name: str) -> str | None:
    exe = name + (".exe" if os.name == "nt" else "")
    local = APP_DIR / "ffmpeg"
    if local.exists():
        for p in local.rglob(exe):
            return str(p)
    return shutil.which(name)


def ffmpeg_path() -> str:
    p = _find_bin("ffmpeg")
    if not p:
        raise RuntimeError("Không tìm thấy FFmpeg. Hãy chạy lại install.bat.")
    return p


def ffprobe_path() -> str:
    p = _find_bin("ffprobe")
    if not p:
        raise RuntimeError("Không tìm thấy ffprobe. Hãy chạy lại install.bat.")
    return p


def strip_accents(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_tag(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", strip_accents(s).lower())


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        [ffprobe_path(), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def swap_encoder(args: list[str], old: list[str], new: list[str]) -> list[str]:
    """Đổi cụm cờ encoder trong lệnh FFmpeg, giữ nguyên phần còn lại."""
    for i in range(len(args) - len(old) + 1):
        if args[i:i + len(old)] == old:
            return args[:i] + new + args[i + len(old):]
    return args


def run_ffmpeg(args: list[str], cwd: Path, stall: float = 90.0) -> None:
    """Chạy FFmpeg và canh tiến độ: quá `stall` giây không nhích thì kill + báo lỗi.

    FFmpeg thỉnh thoảng kẹt hẳn (đã gặp: mã hóa AAC 192k cho audio mono 48k —
    tiến trình quay 1 nhân CPU mà không ra frame nào), treo cả hàng đợi của app.
    `-progress pipe:1` in trạng thái ~2 lần/giây; im lặng nghĩa là đã kẹt.
    """
    cmd = [ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error",
           "-nostats", "-progress", "pipe:1"] + args
    log = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
    p = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE,
                         stderr=log, text=True, encoding="utf-8", errors="replace")
    last = [time.time()]

    def _drain():
        for _ in p.stdout:
            last[0] = time.time()

    reader = threading.Thread(target=_drain, daemon=True)
    reader.start()
    killed = False
    while p.poll() is None:
        if time.time() - last[0] > stall:
            p.kill()
            killed = True
            break
        time.sleep(0.1)
    p.wait()
    reader.join()
    p.stdout.close()
    log.seek(0)
    err = log.read()
    log.close()
    if killed:
        tail = "\n".join(err.strip().splitlines()[-10:])
        raise RuntimeError(
            f"FFmpeg bị treo (không tiến triển {int(stall)}s) nên đã dừng.\n{tail}".strip())
    if p.returncode != 0:
        tail = "\n".join(err.strip().splitlines()[-15:])
        raise RuntimeError(f"FFmpeg báo lỗi:\n{tail}")


# --------------------------------------------------------------------------- kịch bản
@dataclass
class Beat:
    idx: int
    spoken: str
    display: str
    tag: str = ""
    clip: str = ""  # tên file trong thư viện meme ("" = không có clip)
    context: str = ""  # ngữ cảnh cha của reply Threads: '@tên: trích đoạn'
    threads: bool = False
    threads_radius: int = 0


_TAG_RE = re.compile(r"^\s*\[([^\]]*)\]\s*(.*)$")
_CUE_RE = re.compile(r"\[[^\]]*\]")


def parse_script(text: str) -> list[Beat]:
    """Mỗi dòng là một nhịp.  `[thẻ] lời đọc`  hoặc  `[thẻ] lời đọc || chữ hiển thị`.
    Dòng trống và dòng bắt đầu bằng # bị bỏ qua."""
    beats: list[Beat] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tag = ""
        m = _TAG_RE.match(line)
        if m:
            tag, line = m.group(1).strip(), m.group(2).strip()
        if not line:
            continue
        if "||" in line:
            spoken, display = (p.strip() for p in line.split("||", 1))
            no_sub = display == "-"  # '|| -' = không phụ đề, chỉ TTS đọc + ảnh
            if no_sub:
                display = ""
        else:
            spoken = display = line
            no_sub = False
        display = _CUE_RE.sub("", display).strip()  # bỏ thẻ cảm xúc inline như [cười]
        display = re.sub(r"\s*[—–]\s*", " ", display).strip()  # gạch ngang dài = khoảng trắng, không phải điểm ngắt
        spoken = spoken.replace("*", "").strip()  # dấu * chỉ dùng cho chữ hiển thị
        if not spoken:
            continue
        beats.append(Beat(len(beats) + 1, spoken,
                          display if (display or no_sub) else _CUE_RE.sub("", spoken).strip(),
                          tag))
    return normalize_beats(beats)


def normalize_beats(beats: list[Beat]) -> list[Beat]:
    """Chuẩn hoá chữ hiển thị: bỏ gạch ngang dài, bỏ dấu ngắt mắc kẹt cuối cụm."""
    for b in beats:
        b.display = re.sub(r"\s*[—–]\s*", " ", b.display).strip()
    return beats


# --------------------------------------------------------------------------- thư viện meme / nền
def scan_memes() -> dict[str, list[Path]]:
    lib: dict[str, list[Path]] = {}
    for p in sorted(MEME_DIR.rglob("*")):
        if p.is_file() and p.suffix.lower() in (VIDEO_EXT | IMAGE_EXT):
            rel = p.relative_to(MEME_DIR)
            if len(rel.parts) > 1:
                tag = rel.parts[0]
            else:
                tag = re.sub(r"[\s_\-.]*\d+$", "", p.stem)
            lib.setdefault(norm_tag(tag), []).append(p)
    return lib


def list_contents() -> list[str]:
    """Danh sách tên nội dung (mỗi nội dung = một chủ đề / video) có sẵn minh họa."""
    if not ILLUS_DIR.is_dir():
        return []
    return sorted(p.name for p in ILLUS_DIR.iterdir() if p.is_dir())


def scan_illust(content: str) -> dict[str, list[Path]]:
    """Thư viện MINH HỌA theo nội dung: assets/illus/<content>/<thẻ-chủ-tác>/..."""
    root = ILLUS_DIR / content if content else ILLUS_DIR
    lib: dict[str, list[Path]] = {}
    if not root.is_dir():
        return lib
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in (VIDEO_EXT | IMAGE_EXT):
            rel = p.relative_to(root)
            lib.setdefault(norm_tag(rel.parts[0]), []).append(p)
    return lib


def list_backgrounds() -> list[Path]:
    return [p for p in sorted(BG_DIR.rglob("*")) if p.is_file() and p.suffix.lower() in VIDEO_EXT]


def list_music() -> list[Path]:
    return [p for p in sorted(MUSIC_DIR.rglob("*")) if p.is_file() and p.suffix.lower() in AUDIO_EXT]


def clip_label(p: Path, root: Path = MEME_DIR) -> str:
    return p.relative_to(root).as_posix()


def load_meme_catalog() -> dict[str, dict]:
    """Catalog mô tả meme (file -> {tag, desc}) — do người/AI xem thumbnail và ghi.
    Thiếu file hay hỏng JSON thì trả {} và mọi thứ chạy như kiểu chọn ngẫu nhiên cũ."""
    try:
        data = json.loads((MEME_DIR / "_catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for e in data if isinstance(data, list) else []:
        rel = (e or {}).get("file")
        if rel:
            out[rel.replace("\\", "/")] = {"tag": e.get("tag") or "", "desc": e.get("desc") or ""}
    return out


# Thẻ cạn (ít clip) được vay clip của thẻ láng giềng cùng nhóm cảm xúc
_NEIGHBOR_TAGS = {
    "buon": ["hoang"], "dau": ["tucgian", "buon"], "danh": ["tucgian"],
    "imlang": ["hoang"], "run": ["hoang"], "ketthuc": ["vui"],
    "modau": ["chuyencanh"], "chapnhan": ["hieu", "khen"], "tinhtoan": ["khohieu", "soc"],
    "batluc": ["khohieu", "hieu"], "ngan": ["batluc", "khohieu"],  # tương thích kịch bản cũ
}


def _strip_accents_lower(s: str) -> str:
    return strip_accents(s).lower()


def _pick_by_desc(cands: list[Path], beat_text: str, catalog: dict, used: set) -> Path | None:
    """Chọn clip trong thẻ có MÔ TẢ khớp từ khoá của lời đọc, ưu tiên clip chưa dùng.

    Ví dụ nhịp nói 'gào lên kinh hoàng' sẽ ăn clip 'nam nhân vật gào lên kinh hoàng'
    thay vì bị bốc nhầm 'sóc há miệng la to'. Không khớp gì thì trả None (để caller
    bốc ngẫu nhiên trong thẻ như cũ).
    """
    words = {w for w in re.split(r"\W+", _strip_accents_lower(beat_text)) if len(w) >= 4}
    if not words:
        return None
    best, best_score = None, 0
    for p in cands:
        rel = p.relative_to(MEME_DIR).as_posix()
        entry = catalog.get(rel)
        if not entry or not entry["desc"]:
            continue
        desc_w = {w for w in re.split(r"\W+", _strip_accents_lower(entry["desc"])) if len(w) >= 4}
        score = len(words & desc_w)
        if score > best_score or (score == best_score and score > 0 and p not in used and best in used):
            best, best_score = p, score
    return best if best_score >= 2 else None   # cần ≥2 từ khớp để không bắt bừa


def assign_clips(beats: list[Beat], seed: int | None = None, content: str = "") -> None:
    """Gán clip tự động theo thẻ; tránh lặp lại đúng clip vừa dùng.

    Thứ tự chọn khi thẻ có clip:
      1. Clip có mô tả trong _catalog.json khớp ≥2 từ khoá với LỜI ĐỌC (chọn thông minh).
      2. Ngẫu nhiên trong thẻ, tránh clip đã dùng ở các nhịp trước.
      3. Thẻ cạn hết clip -> vay của thẻ láng giềng cùng cảm xúc (_NEIGHBOR_TAGS).
    Hai nguồn được ưu tiên theo thứ tự:
      1. Thẻ cảm xúc (soc, cuoi, buon, hoang...) -> thư viện meme dùng chung (assets/memes/<thẻ>/).
      2. Thẻ chủ thể / sự kiện (emu, lua-mi...) -> thư viện minh họa của đúng nội dung
         (assets/illus/<content>/<thẻ>/). Minh họa nội dung không nằm trong catalog meme.
    """
    rng = random.Random(seed)
    lib = scan_memes()
    ill = scan_illust(content)
    catalog = load_meme_catalog()
    used: set[Path] = set()

    def pool_for(tag: str) -> list[Path]:
        cands = lib.get(norm_tag(tag), [])
        if not cands:                      # thẻ rỗng -> vay thẻ láng giềng cùng cảm xúc
            for nb in _NEIGHBOR_TAGS.get(norm_tag(tag), ()):
                cands = lib.get(nb, [])
                if cands:
                    break
        return cands

    for b in beats:
        if b.clip:
            continue
        cands: list[Path] = []
        from_ill = False
        if b.tag:
            cands = pool_for(b.tag)
            if not cands:
                cands = ill.get(norm_tag(b.tag), [])
                from_ill = True
        vids = [c for c in cands if c.suffix.lower() in VIDEO_EXT]  # ưu tiên clip meme (video) hơn ảnh
        if vids:
            cands = vids
        if cands:
            fresh = [c for c in cands if c not in used] or cands
            pick = _pick_by_desc(fresh, b.spoken, catalog, used) if not from_ill else None
            if pick is None:
                pick = rng.choice(fresh)
            used.add(pick)
            b.clip = clip_label(pick, ILLUS_DIR / content if from_ill else MEME_DIR)


def resolve_clip(cell: str, content: str = "") -> Path | None:
    s = (cell or "").strip()
    if not s or s == "-":
        return None
    p = Path(s)
    if p.is_absolute() and p.exists():
        return p
    q = MEME_DIR / s
    if q.exists():
        return q
    # minh họa của đúng nội dung đang làm: assets/illus/<content>/<thẻ>/...
    if content:
        ill_root = ILLUS_DIR / content
        iq = ill_root / s
        if iq.exists():
            return iq
        if ill_root.is_dir():
            low = s.lower()
            for c in sorted(ill_root.rglob("*")):
                if c.is_file() and (c.name.lower() == low or c.stem.lower() == low):
                    return c
    low = s.lower()
    for c in MEME_DIR.rglob("*"):
        if c.is_file() and (c.name.lower() == low or c.stem.lower() == low):
            return c
    raise ValueError(f"Không tìm thấy clip '{s}' trong thư viện meme / minh họa.")


# --------------------------------------------------------------------------- giọng đọc
_engines: dict = {}


def get_engine(backend: str):
    if backend == BACKEND_DUMMY:
        return None
    if "vieneu" not in _engines:
        try:
            from vieneu import Vieneu
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Chưa cài thư viện giọng đọc 'vieneu'. Hãy chạy lại install.bat.") from e
        try:
            _engines["vieneu"] = Vieneu()
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "Không khởi tạo được model giọng đọc VieNeu-TTS. Lần đầu chạy cần có Internet để tải model "
                "(vài trăm MB); nếu mạng ổn mà vẫn lỗi, thử bật 'Chế độ thử' để kiểm tra phần dựng video. "
                f"Chi tiết: {type(e).__name__}: {e}"
            ) from e
    return _engines["vieneu"]


def list_voices(backend: str) -> list[tuple[str, str]]:
    if backend == BACKEND_DUMMY:
        return [("Giọng thử (tiếng bíp)", "")]
    eng = get_engine(backend)
    return [(label, vid) for label, vid in eng.list_preset_voices()]


def _dummy_audio(text: str, sr: int = 48000) -> np.ndarray:
    dur = max(0.7, 0.06 * len(text))
    t = np.arange(int(dur * sr)) / sr
    env = 0.5 + 0.5 * np.sin(2 * np.pi * 3.5 * t)
    fade = np.minimum(1.0, np.minimum(t / 0.03, (dur - t) / 0.03))
    return (0.2 * np.sin(2 * np.pi * 190 * t) * env * fade).astype(np.float32)


def _trim_silence(a: np.ndarray, sr: int, thr: float = 0.008, keep: float = 0.04) -> np.ndarray:
    if a.size == 0:
        return a
    idx = np.where(np.abs(a) > thr)[0]
    if idx.size == 0:
        return a
    s = max(0, idx[0] - int(keep * sr))
    e = min(a.size, idx[-1] + int(keep * sr))
    return a[s:e]


def synth(text: str, backend: str, voice: str, speed: float) -> Path:
    key = hashlib.sha1(f"{backend}|{voice}|{speed:.2f}|{text}".encode("utf-8")).hexdigest()[:20]
    out = CACHE_DIR / f"{key}.wav"
    if out.exists():
        return out
    if backend == BACKEND_DUMMY:
        audio, sr = _dummy_audio(text), 48000
    else:
        eng = get_engine(backend)
        audio = eng.infer(text, voice=voice or None)
        sr = int(eng.sample_rate)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1) if audio.shape[-1] <= 2 else audio.squeeze()
    audio = _trim_silence(audio.squeeze(), sr)
    raw = CACHE_DIR / f"{key}_raw.wav"
    sf.write(str(raw), audio, sr)
    if abs(speed - 1.0) > 0.01:
        run_ffmpeg(["-i", str(raw), "-filter:a", f"atempo={speed:.3f}", str(out)], CACHE_DIR)
        raw.unlink(missing_ok=True)
    else:
        raw.replace(out)
    return out


# --------------------------------------------------------------------------- tùy chọn dựng
@dataclass
class Options:
    backend: str = BACKEND_VIENEU
    voice: str = ""
    speed: float = 1.0
    gap: float = GAP             # giây nghỉ giữa hai nhịp đọc
    bg: str = "ngẫu nhiên"          # "ngẫu nhiên" hoặc tên file trong thư viện nền
    content: str = ""                 # tên nội dung -> thư viện minh họa assets/illus/<content>/
    upper: bool = True
    font: str = "Segoe UI Black"
    font_size: int = 120
    text_color: str = "#FF9A1F"
    outline_color: str = "#FFFFFF"
    outline_w: int = 9
    text_y: int = 1010
    max_words: int = 4
    pop: bool = True
    meme_w: int = 960
    meme_h: int = 560
    meme_y: int = 210
    meme_anchor: str = "top"        # "top" = ảnh dính mép trên khung · "bottom" = dính mép dưới
    text_anchor: str = "center"     # "center" = chữ canh giữa quanh text_y · "top" = text_y là mép trên
    carry: bool = True              # dòng không có thẻ thì giữ clip meme trước đó
    use_music: bool = False
    music_volume: float = 0.08
    nvenc: bool = False
    emph_color: str = "#FFE600"   # màu từ quan trọng (đánh dấu *từ*)
    emph_scale: float = 1.3        # từ quan trọng to gấp mấy lần
    card_motion: bool = True       # card ảnh nở nhẹ + trôi chậm trong mỗi mục
    karaoke: bool = True           # tô sáng lần lượt từng từ khi đọc (chỉ nhịp có chữ)
    bg_motion: bool = True         # nền phóng chậm suốt video để khung hình không đứng yên
    pop_in: bool = True            # Threads: card nảy vào (pop) khi sang mục mới
    sfx: bool = True               # tiếng pop/whoosh ở mỗi lần sang mục
    fps: int = 60                  # khung hình/giây: 60 mượt hơn 30 khi có chuyển động
    mascot: bool = True            # mascot trồi lên từ đáy khung ở nhịp mở đầu (hook)
    next_card: bool = True         # Threads: card kế tiếp chờ mờ bên dưới rồi trượt lên thay card cũ
    seed: int | None = None
    threads: bool = False
    threads_radius: int = 0
    threads_side_margin: int = 0
    threads_shadow: int = 0
    threads_padding: int = 0
    threads_max_height: int = 640
    threads_zoom: int = 140
    threads_padding_top: int = -1
    threads_padding_right: int = -1
    threads_padding_bottom: int = -1
    threads_padding_left: int = -1

    @property
    def card_padding(self):
        return tuple(self.threads_padding if value < 0 else value for value in
                     (self.threads_padding_top, self.threads_padding_right,
                      self.threads_padding_bottom, self.threads_padding_left))



# --------------------------------------------------------------------------- chữ (ASS)
def _ass_color(color: str) -> str:
    """Nhận '#RRGGBB' hoặc 'rgb(r,g,b)' / 'rgba(r,g,b,a)' (tùy bản Gradio) -> màu ASS."""
    c = (color or "").strip()
    if c.lower().startswith("rgb"):
        nums = re.findall(r"[\d.]+", c)[:3]
        try:
            r, g, b = (f"{int(float(x)):02X}" for x in nums)
        except ValueError:
            r = g = b = "FF"
    else:
        h = c.lstrip("#")
        if len(h) != 6:
            h = "FFFFFF"
        r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def _ass_dim(color: str, factor: float = 0.45) -> str:
    """Màu mờ cùng tông cho phần chưa đọc của karaoke."""
    raw = _ass_color(color)
    b, g, r = (int(raw[i:i + 2], 16) for i in (4, 6, 8))
    b, g, r = (round(v * factor) for v in (b, g, r))
    return f"&H00{b:02X}{g:02X}{r:02X}"


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


_WIN_FONTS = {"segoe ui black": "seguibl.ttf", "segoe ui": "segoeui.ttf",
              "arial black": "ariblk.ttf", "impact": "impact.ttf", "arial": "arial.ttf"}


@functools.lru_cache(maxsize=32)
def _font_path(name: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    dirs = [FONT_DIR]
    for env in ("WINDIR", "SystemRoot"):
        if os.environ.get(env):
            dirs.append(Path(os.environ[env]) / "Fonts")
    for d in dirs:
        if not d.is_dir():
            continue
        m = _WIN_FONTS.get(name.lower().strip())
        if m and (d / m).exists():
            return str(d / m)
        for f in sorted(d.glob("*")):
            if f.suffix.lower() in {".ttf", ".otf", ".ttc"} and \
                    re.sub(r"[^a-z0-9]", "", f.stem.lower()).startswith(key):
                return str(f)
    return ""


@functools.lru_cache(maxsize=64)
def _pil_font(path: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def _text_width(text: str, size: float, font_name: str) -> float:
    """Đo bề ngang chữ thật bằng chính file font; không tìm thấy font thì ước lượng."""
    path = _font_path(font_name)
    if path:
        try:
            f = _pil_font(path, 200)
            asc, desc = f.getmetrics()
            # Fontsize của ASS = chiều cao dòng (ascent+descent), không phải cỡ em -> quy đổi
            return f.getlength(text) * (size / 200.0) * (200.0 / (asc + desc)) * 1.02
        except Exception:  # noqa: BLE001
            pass
    return len(text) * size * 0.50


def parse_emph(text: str) -> list[tuple[str, bool]]:
    """'a *b c* d' -> [('a',False),('b',True),('c',True),('d',False)]"""
    out: list[tuple[str, bool]] = []
    emph = False
    for part in re.split(r"(\*)", text):
        if part == "*":
            emph = not emph
            continue
        out.extend((w, emph) for w in part.split())
    # dấu câu bị tách rời khỏi từ (do "*1960*,") thì dính lại: "1960 ," -> "1960,"
    punct = set(",;:.!?…\"')]»”’")
    merged: list[tuple[str, bool]] = []
    for w, e in out:
        if merged and w and all(ch in punct for ch in w):
            merged[-1] = (merged[-1][0] + w, merged[-1][1])
        else:
            merged.append((w, e))
    return merged


_BREAK_CHARS = ",;:.!?…"

# từ nối / đại từ không nên đứng cuối cụm (tách khỏi từ đi sau sẽ đọc rất vụn)
_GLUE_WORDS = {
    "và", "hoặc", "của", "với", "để", "thì", "mà", "là", "nhưng", "nên", "rồi", "trong",
    "từ", "cho", "ở", "khi", "nếu", "vì", "do", "bằng", "theo", "tới", "đến", "cùng",
    "hay", "còn", "các", "những", "một", "cái", "con", "chiếc", "ông", "bà", "anh", "chị",
    "cô", "chú", "bác", "ngài", "em", "người", "chúng", "mọi", "tất", "bị", "được",
    "sẽ", "đã", "đang", "vẫn", "cũng", "rất", "quá",
}


def _is_break(word: str) -> bool:
    return bool(word) and word[-1] in _BREAK_CHARS


def _is_glue(word: str) -> bool:
    return word.strip("\"'()“”").rstrip(_BREAK_CHARS).lower() in _GLUE_WORDS


def _is_number(word: str) -> bool:
    return bool(re.fullmatch(r"\d[\d.,:/%-]*[a-zA-Z%]?", word))


def _split_run(run: list, max_words: int) -> list[list]:
    """Chia một đoạn (không có dấu câu) thành các cụm đều nhau, tránh cắt giữa cụm từ."""
    if len(run) <= max_words:
        return [run]
    n = math.ceil(len(run) / max_words)
    size = math.ceil(len(run) / n)
    chunks = [run[i:i + size] for i in range(0, len(run), size)]
    # đừng để cụm kết thúc bằng từ nối: "... của" | "Ông" | "A làm"
    for i in range(len(chunks) - 1):
        while len(chunks[i]) > 2 and _is_glue(chunks[i][-1][0]):
            chunks[i + 1].insert(0, chunks[i].pop())
    # đừng tách số khỏi từ đứng trước: "Năm" | "1960" -> "Năm 1960"
    for i in range(1, len(chunks)):
        while _is_number(chunks[i][0][0]) and len(chunks[i - 1]) > 1:
            chunks[i].insert(0, chunks[i - 1].pop())
    # cụm cuối chỉ còn 1 từ thì gộp vào cụm trước cho khỏi chớp
    if max_words > 1 and len(chunks) > 1 and len(chunks[-1]) == 1:
        chunks[-2].extend(chunks.pop())
    return [c for c in chunks if c]


def split_items(items: list, max_words: int) -> list[list]:
    """Chia lời hiển thị thành các cụm hiện dần.

    Ưu tiên ngắt sau dấu câu (",", ".", "!"…) nên không cắt vụn giữa cụm từ;
    đoạn nào quá dài mới chia theo số từ.
    """
    if not items:
        return []
    max_words = max(1, max_words)
    runs: list[list] = []
    cur: list = []
    for it in items:
        cur.append(it)
        if _is_break(it[0]):
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    out: list[list] = []
    for run in runs:
        out.extend(_split_run(run, max_words))
    return out


def split_chunks(text: str, max_words: int) -> list[str]:
    return [" ".join(w for w, _ in c) for c in split_items(parse_emph(text), max_words)]


def layout_lines(items: list[tuple[str, bool]], opt: "Options") -> list[list[tuple[str, bool]]]:
    """Chia cụm chữ thành các dòng cố định, dùng gần hết bề ngang màn hình."""
    avail = W - 2 * 40 - 2 * opt.outline_w
    base = opt.font_size
    big = int(base * opt.emph_scale)
    widths = [_text_width(w, big if e else base, opt.font) for w, e in items]
    space = _text_width(" ", base, opt.font)
    total = sum(widths) + space * (len(items) - 1)
    n0 = max(1, math.ceil(total / avail))
    for n in range(n0, n0 + 3):
        if n == 1:
            return [items]
        target = total / n
        lines: list[list] = []
        cur: list = []
        curw = 0.0
        ok = True
        for it, w in zip(items, widths):
            add = w + (space if cur else 0)
            if cur and ((len(lines) < n - 1 and curw + add / 2 > target) or curw + add > avail):
                lines.append(cur)
                cur, curw, add = [], 0.0, w
            cur.append(it)
            curw += add
        lines.append(cur)
        if len(lines) <= n and all(
                sum(_text_width(w, big if e else base, opt.font) for w, e in ln)
                + space * (len(ln) - 1) <= avail for ln in lines):
            return lines
    return lines


def _inline_color(color: str) -> str:
    return "&H" + _ass_color(color)[4:] + "&"


def _line_text(line: list[tuple[str, bool]], opt: "Options") -> str:
    base = opt.font_size
    big = int(base * opt.emph_scale)
    pc, ec = _inline_color(opt.text_color), _inline_color(opt.emph_color)
    parts = []
    for w, e in line:
        if e:
            parts.append(f"{{\\fs{big}\\1c{ec}}}{w}{{\\fs{base}\\1c{pc}}}")
        else:
            parts.append(w)
    return " ".join(parts)


def _karaoke_lines(lines: list[list[tuple[str, bool]]], seconds: float, opt: "Options") -> str:
    """Chữ kèm tag \\kf: tô sáng lần lượt từng từ trong cụm.

    TTS chỉ trả tổng thời lượng nên thời lượng mỗi từ chia theo độ dài từ — đủ khớp
    để mắt bám theo chữ, không cần canh giọng thật.
    """
    words = [w for ln in lines for w, _ in ln]
    weights = [len(w) + 1 for w in words]
    total = float(sum(weights)) or 1.0
    base, big = opt.font_size, int(opt.font_size * opt.emph_scale)
    pc, ec = _inline_color(opt.text_color), _inline_color(opt.emph_color)
    parts: list[str] = []
    i = 0
    for ln in lines:
        seg = []
        for w, emph in ln:
            tag = f"\\kf{max(1, round(seconds * weights[i] / total * 100))}"
            i += 1
            if emph:
                seg.append(f"{{{tag}\\fs{big}\\1c{ec}}}{w}{{\\fs{base}\\1c{pc}}}")
            else:
                seg.append(f"{{{tag}}}{w}")
        parts.append(" ".join(seg))
    return r"\N".join(parts)


def build_ass(timed: list[dict], opt: Options) -> str:
    karaoke = bool(getattr(opt, "karaoke", False))
    secondary = _ass_dim(opt.text_color) if karaoke else "&H000000FF"
    style = (
        f"Style: Main,{opt.font},{opt.font_size},{_ass_color(opt.text_color)},{secondary},"
        f"{_ass_color(opt.outline_color)},&H96000000,-1,0,0,0,100,100,0,0,1,{opt.outline_w},3,5,40,40,0,1"
    )
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        style, "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    pop = r"\fscx80\fscy80\t(0,110,\fscx100\fscy100)" if opt.pop else ""
    an = 8 if opt.text_anchor == "top" else 5
    for t in timed:
        disp = t["display"].upper() if opt.upper else t["display"]
        disp = disp.replace("{", "(").replace("}", ")").replace("\\", "")
        chunks = split_items(parse_emph(disp), opt.max_words)
        if not chunks:
            continue
        weights = [sum(len(w) + 1 for w, _ in c) for c in chunks]
        total_w = float(sum(weights))
        span = t["text_end"] - t["start"]
        cur = t["start"]
        for c, w in zip(chunks, weights):
            end = cur + span * (w / total_w)
            laid = layout_lines(c, opt)
            if karaoke:
                text = _karaoke_lines(laid, end - cur, opt)
            else:
                text = r"\N".join(_line_text(ln, opt) for ln in laid)
            lines.append(
                f"Dialogue: 0,{_ass_time(cur)},{_ass_time(end)},Main,,0,0,0,,"
                f"{{\\an{an}\\q2\\pos({W // 2},{opt.text_y}){pop}}}{text}"
            )
            cur = end
    return "\n".join(lines) + "\n"


def _pause_after(text: str) -> float:
    """Nghỉ thêm sau mỗi nhịp theo dấu câu cuối: chấm/câu hỏi lâu hơn phẩy — nghe tự nhiên
    hơn kiểu nghỉ đều 0.18s. Nhịp không có dấu câu cuối (cắt giữa cụm) nghỉ ngắn nhất."""
    t = (text or "").rstrip().rstrip('"”’\')]')
    if not t:
        return 0.0
    if t[-1] in ".!?…":
        return 0.32
    if t[-1] in ",;:":
        return 0.12
    return 0.0


# --------------------------------------------------------------------------- dựng
def _overlay_y(opt: "Options") -> str:
    """Toạ độ y cho overlay: dính mép trên khung hoặc dính mép dưới (card cao thấp khác nhau).

    `h` là chiều cao ảnh/clip sau khi scale — dùng biểu thức của FFmpeg để mọi card
    đều kết thúc ở cùng một đường, nhờ vậy chữ bên dưới luôn cách card một khoảng đều.
    """
    if opt.meme_anchor == "bottom":
        return f"{opt.meme_y + opt.meme_h}-h"
    return str(opt.meme_y)


def _build_spans(timed: list[dict], carry: bool) -> list[dict]:
    """Gộp các nhịp liền nhau dùng chung một ảnh/clip thành span.

    `subs` của span cho biết có nhịp nào trong đó đang hiện chữ hay không — span
    không có chữ (nhịp `|| -`) sẽ được canh giữa màn hình dọc thay vì đỗ lên trên
    chờ chữ bên dưới.
    """
    spans: list[dict] = []
    cur = None
    for t in timed:
        clip = t["clip"]
        has_text = bool((t.get("display") or "").strip())
        if clip is not None:
            if cur is not None and carry and cur["clip"] == clip and cur.get('zoom', False) == t.get('zoom', False):
                cur["end"] = t["vis_end"]
                cur["subs"] = cur["subs"] or has_text
                continue
            cur = {"clip": clip, "start": t["vis_start"], "end": t["vis_end"],
                   "subs": has_text, 'zoom': t.get('zoom', False),
                   'sound': bool(t.get('sound')),
                   'context': (t.get('context') or '').strip()}
            spans.append(cur)
        elif carry and cur is not None:
            cur["end"] = t["vis_end"]
            cur["subs"] = cur["subs"] or has_text
        else:
            cur = None
    return spans


def _pop_starts(spans: list[dict], *, first: bool = True) -> list[float]:
    """Mốc kêu tiếng chuyển mục: mỗi lần một card mới hiện ra.

    Mục mở màn bằng nhịp `[sound]`/`[zoom]` đã kêu bằng videoplayback trong voice.wav
    rồi, thêm pop nữa thành hai tiếng chồng nhau. `first=False` bỏ mốc 0 (khi dùng
    whoosh, card đầu video không cần tiếng chuyển).
    """
    out: list[float] = []
    for kk, sp in enumerate(spans):
        if sp.get("sound") or (kk == 0 and not first):
            continue
        if kk and sp.get("clip") == spans[kk - 1].get("clip"):
            continue
        out.append(sp["start"])
    return out


def _probe_size(path: Path) -> tuple[int, int] | None:
    """Kích thước khung gốc của ảnh/clip — dùng để tính chiều cao card Threads."""
    if path.suffix.lower() in IMAGE_EXT:
        try:
            from PIL import Image
            with Image.open(path) as im:
                return im.size
        except Exception:  # noqa: BLE001
            return None
    try:
        r = subprocess.run(
            [ffprobe_path(), "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except RuntimeError:
        return None
    m = re.match(r"(\d+)x(\d+)", r.stdout.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def _card_pad(path: str) -> float:
    """Hệ số bù: ảnh card đã thêm bóng đổ rộng hơn phần card thật (viền trong suốt).

    Bù lại ở bước scale để bề ngang card hiện ra đúng bằng `meme_w` mà slider hứa.
    """
    p = Path(path)
    if p.suffix.lower() not in IMAGE_EXT:
        return 1.0
    try:
        from PIL import Image
        with Image.open(p) as im:
            alpha = im.convert("RGBA").getchannel("A")
            box = alpha.point(lambda v: 255 if v > 200 else 0).getbbox()
            if box and box[2] > box[0]:
                return im.width / (box[2] - box[0])
    except Exception:  # noqa: BLE001
        pass
    return 1.0


# Card Threads luôn phủ đủ bề ngang khung; chiều cao khung tự nở theo card cao nhất.
THREADS_CARD_TOP = 140        # mép trên của card cao nhất khi có chữ
THREADS_TEXT_GAP = 0          # chữ bám sát đáy card (font đã có leading riêng)
THREADS_CARD_CENTER = 768     # tâm dọc của card khi nhịp không có chữ (40% khung 1920)
THREADS_BOTTOM_RESERVE = 140  # chừa đáy cho caption/UI khi có chữ

NEXT_CARD_GAP = 92            # khoảng hở cho sợi dây nối giữa hai card
NEXT_CARD_SCALE = 0.86        # card kế tiếp nhỏ hơn card đang đọc
NEXT_CARD_DIM = 0.12          # độ tối của card kế tiếp (eq brightness)
NEXT_CARD_SAT = 0.55          # độ bão hoà màu của card kế tiếp
NEXT_CARD_DELAY = 0.5         # card kế tiếp hiện sau khi card hiện tại đứng yên
NEXT_CARD_PREVIEW = 0.4       # thời gian tối thiểu card kế tiếp chờ sẵn (nhịp đọc ngắn)

MASCOT_H = 1100               # chiều cao mascot mở đầu
MASCOT_BOTTOM = H + 40        # chân mascot nằm ngoài khung
MASCOT_TOP = MASCOT_BOTTOM - MASCOT_H
MASCOT_CARD_GAP = 28          # hở giữa card bài post và đỉnh đầu mascot


def _mascot_eyes(im) -> float | None:
    """Tâm ngang khuôn mặt: trung điểm hai mắt, đơn vị px của ảnh gốc.

    Ảnh biểu cảm thay tay thường bị cắt lệch — nhân vật không nằm giữa khung ảnh,
    lệch cả so với hộp alpha — nên canh theo mắt mới thấy mặt đứng giữa. Mắt là hai
    đốm sáng to, cùng cỡ, cùng hàng nằm quanh giữa khối người. Không thấy cặp nào
    thì trả None để canh theo hộp alpha.
    """
    from collections import deque
    from PIL import Image
    w, h = im.size
    if w < 16 or h < 16:
        return None
    k = max(1, w // 400)   # thu nhỏ giữ nguyên tỉ lệ để dò nhanh
    a = np.asarray(im.convert("RGBA").resize((max(1, w // k), max(1, h // k)), Image.BOX)).astype(int)
    al = a[:, :, 3] > 12
    bright = al & (a[:, :, :3].min(2) > 228)
    if not bright.any():
        return None
    bh, bw = bright.shape
    seen = np.zeros_like(bright)
    blobs: list[tuple[int, int, int, int, int]] = []
    for y0, x0 in zip(*np.where(bright)):
        if seen[y0, x0]:
            continue
        q, seen[y0, x0] = deque([(y0, x0)]), True
        n = 0
        bx0 = bx1 = x0
        by0 = by1 = y0
        while q:
            y, x = q.popleft()
            n += 1
            bx0, bx1, by0, by1 = min(bx0, x), max(bx1, x), min(by0, y), max(by1, y)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < bh and 0 <= nx < bw and bright[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        blobs.append((n, bx0, bx1, by0, by1))
    # Chỉ giữ đốm cỡ mắt: bỏ viền trắng và cả khối mặt (to gấp nhiều lần).
    cand = [b for b in blobs
            if 0.0015 * bh * bw < b[0] < 0.02 * bh * bw
            and b[2] - b[1] + 1 <= 0.12 * bw
            and b[4] - b[3] + 1 > 4
            and 0.4 < (b[2] - b[1] + 1) / (b[4] - b[3] + 1) < 2.5]
    ys, xs = np.where(al)
    a_cx, a_half = (xs.min() + xs.max() + 1) / 2, (xs.max() - xs.min() + 1) / 2
    best = None
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            a1, x10, x11, y10, y11 = cand[i]
            a2, x20, x21, y20, y21 = cand[j]
            c1, c2 = (x10 + x11) / 2, (x20 + x21) / 2
            wd = ((x11 - x10 + 1) + (x21 - x20 + 1)) / 2
            mid = (c1 + c2) / 2
            if abs((y10 + y11) - (y20 + y21)) > 0.12 * bh:
                continue
            if min(a1, a2) < 0.6 * max(a1, a2):
                continue
            if not (1.1 * wd < abs(c1 - c2) < 3.0 * wd):
                continue
            if abs(mid - a_cx) > 0.2 * a_half:
                continue
            if best is None or a1 + a2 > best[0]:
                best = (a1 + a2, mid * k)
    return best[1] if best else None


def _mascot_x(path: Path, height: int) -> str:
    """Vị trí ngang của mascot: đặt khuôn mặt vào giữa khung.

    Canh x=(W-w)/2 theo khung ảnh thì cả người lệch khi ảnh biểu cảm bị cắt lệch;
    ở đây bù đúng phần lệch giữa mặt (hoặc hộp alpha khi không thấy mắt) và tâm
    ảnh, quy về px sau khi scale. Tính riêng từng mặt để đổi biểu cảm không nhảy ngang.
    """
    dx = 0.0
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            ys, xs = np.where(np.asarray(im.convert("RGBA"))[:, :, 3] > 12)
            if len(xs):
                dx = ((xs.min() + xs.max() + 1) / 2 - w / 2) * (height / h)
            center = _mascot_eyes(im)
            if center is not None:
                dx = (center - w / 2) * (height / h)
    except Exception:  # noqa: BLE001
        dx = 0.0
    return f"(W-w)/2{-dx if dx else 0.0:+.1f}"


def _threads_cap(has_text: bool, opt: "Options") -> int:
    """Chiều cao tối đa của khung Threads: chừa chỗ cho 2 dòng chữ, hoặc chừa 2 mép."""
    if has_text:
        text_space = round(opt.font_size * 1.35 * 2 + 60)
        return H - THREADS_CARD_TOP - THREADS_TEXT_GAP - text_space - THREADS_BOTTOM_RESERVE
    return 2 * min(THREADS_CARD_CENTER, H - THREADS_CARD_CENTER)


def _threads_box(spans: list[dict], opt: "Options") -> int:
    """Chiều cao khung Threads: vừa đủ cho card cao nhất ở bề ngang hiện tại.

    Mọi card thấp hơn đều phủ đủ ngang (lề 2 bên bằng nhau); card vượt giới hạn
    an toàn (comment quá dài) tự thu chiều cao để không tràn khung/chữ.
    """
    needed = 0
    for sp in spans:
        size = _probe_size(Path(sp["clip"]))
        if not size or not size[0]:
            continue
        factor = opt.threads_zoom / 100 if sp.get("zoom") else 1.0
        width = round(opt.meme_w * factor * _card_pad(str(sp["clip"])))
        needed = max(needed, round(size[1] * width / size[0]))
    if any(sp.get("zoom") for sp in spans):
        return max(200, needed or 200)   # nhịp zoom cố ý tràn khung, không bị chặn
    cap = _threads_cap(any(sp.get("subs") for sp in spans), opt)
    return max(200, min(needed or 200, cap))


def _zoom_scale(factor: float) -> str:
    """Hệ số phóng nhịp ảnh: cỡ thường -> cỡ zoom, vọt quá rồi trở lại (nảy).

    Nhịp chỉ có ảnh không có hiệu ứng hiện-ra riêng: card đứng sẵn ở cỡ thường rồi
    phóng ngay; ease-out-back làm cú phóng vọt quá cỡ trong ZOOM_IN giây rồi thu về
    đúng cỡ zoom, nên mắt thấy đúng một cú zoom có nảy. Card dựng sẵn ở cỡ zoom nên
    nhân 1/factor cho khung đầu về cỡ thường.
    """
    if factor <= 1.0:
        return "1"
    q = f"(min(t/{ZOOM_IN:g},1)-1)"     # -1 ở đầu mục, 0 khi phóng + nảy xong
    ease = f"(1+{ZOOM_BACK + 1:.4f}*pow({q},3)+{ZOOM_BACK:.4f}*pow({q},2))"
    low = 1 / factor
    return f"({low:.4f}+{1 - low:.4f}*{ease})"


def _threads_opt(opt: "Options", spans: list[dict]) -> "Options":
    """Bản Options đã áp bố cục Threads: khung cao theo card, chữ sát đáy khung.

    Chỗ chữ chỉ chừa theo các card CÓ phụ đề — nhịp `|| -` canh giữa khung nên có
    thể cao hơn mà không đẩy chữ xuống.
    """
    texts = [sp for sp in spans if sp.get("subs")]
    box = _threads_box(texts or spans, opt)
    return replace(opt, meme_y=THREADS_CARD_TOP, meme_h=box,
                   text_y=THREADS_CARD_TOP + box + THREADS_TEXT_GAP,
                   text_anchor="top", meme_anchor="bottom")


def _overlay_y_threads(opt: "Options", has_subs: bool) -> str:
    if has_subs:
        return _overlay_y(opt)
    return f"{THREADS_CARD_CENTER}-h/2"


def _threads_card_geometry(sp: dict, opt: "Options") -> dict:
    """Kích thước và mép trên thật của card sau khi scale — để đặt card kế tiếp theo số.

    FFmpeg thu card vừa khung (`force_original_aspect_ratio=decrease`) nên card cao
    hẹp ra hẹp hơn `meme_w`; vị trí card kế tiếp phải tính từ chiều cao thật đó.
    """
    p = Path(sp["clip"])
    img = p.suffix.lower() in IMAGE_EXT
    factor = opt.threads_zoom / 100 if sp.get("zoom") else 1.0
    width = opt.meme_w * factor
    box = opt.meme_h
    if opt.threads and not sp.get("subs"):
        box = _threads_box([sp], opt)
    if opt.threads:
        width *= _card_pad(str(p))
    size = _probe_size(p) if img else None
    if size and size[0] and size[1]:
        fit_w = min(width, box * size[0] / size[1])
        fit_h = fit_w * size[1] / size[0]
    else:
        fit_w, fit_h = width, box
    w, h = round(fit_w), round(fit_h)
    top = opt.meme_y + opt.meme_h - h if sp.get("subs") else THREADS_CARD_CENTER - h / 2
    return {"img": img, "w": w, "h": h, "top": round(top)}


def _next_card_plan(spans: list[dict], opt: "Options") -> list[dict]:
    """Kế hoạch chuyển cảnh, chốt theo loại card.

    - Comment chính: nảy vào tại chỗ (pop), không có card chờ — người xem thấy một
      comment mới của thread, không phải dòng tiếp theo của comment trước.
    - Reply (có khung ngữ cảnh cha): trượt lên từ dưới — hiện mờ ngay dưới comment
      đang đọc, nối bằng sợi dây, rồi hai card trượt lên cùng quãng như một lần cuộn
      feed. Nhịp đọc ngắn ("=))", "tht sự") chỉ dời mốc hiện card chờ sớm hơn, không
      bỏ card chờ (trước đây bị bỏ nên cùng một reply lúc thì có dây nối, lúc thì
      trượt từ đáy khung).
    """
    geo = [_threads_card_geometry(sp, opt) for sp in spans]
    plan = [{"geo": g, "in": None, "out": None, "pv": None} for g in geo]
    for k in range(1, len(spans)):
        sp, g = spans[k], geo[k]
        reply = bool(str(sp.get("context") or "").strip())
        if not g["img"] or sp.get("zoom") or not reply:
            continue
        # Card chờ luôn nép dưới card đang đọc (mục k-1). Nhịp zoom cũng vậy: reply
        # sau zoom chỉ hiện card chờ khi card cha đã vào khung — lấy mục k-2 thì reply
        # con hiện trước cả comment cha.
        pv = None
        if geo[k - 1]["img"]:
            holder = k - 1
            start = spans[holder]["start"] + NEXT_CARD_DELAY
            # Nhịp quá ngắn: hiện card chờ sớm hơn, luôn giữ đủ NEXT_CARD_PREVIEW giây.
            start = max(spans[holder]["start"], min(start, sp["start"] - NEXT_CARD_PREVIEW))
            top = geo[holder]["top"] + geo[holder]["h"] + NEXT_CARD_GAP
            # Chỉ bỏ card chờ khi chỗ chờ nằm ngoài khung (card zoom cao tràn khung).
            if top <= H - 120:
                pv = {"start": start, "top": top}
        y0 = pv["top"] if pv else H + 40
        dist = y0 - g["top"]
        plan[k]["in"] = {"y0": y0, "t": min(0.55, max(0.32, dist / 2600))}
        plan[k]["pv"] = pv
    for k in range(len(spans) - 1):
        nxt = plan[k + 1]
        if nxt["in"] and geo[k]["img"]:
            delta = nxt["in"]["y0"] - geo[k + 1]["top"] if nxt["pv"] else 0
            plan[k]["out"] = {"delta": delta, "t": nxt["in"]["t"]}
    return plan


def _with_context(timed: list[dict], opt: Options, job: Path, max_h: int | None = None) -> None:
    """Ghép khung ngữ cảnh cha (↳ + 1–2 dòng trích, không hiện tên) lên ảnh reply.

    Ảnh cha và con vẫn được lưu riêng nên bỏ reply hay đổi cha không phải chụp lại;
    khung chỉ được ghép trong thư mục job của lần dựng này. Khi đọc cha thì chưa hiện
    gì thêm — đến lượt reply mới có khung, nhờ vậy người xem không thấy trước câu đáp.
    """
    try:
        from . import threads_shot as ts   # bộ vẽ card Threads; nạp muộn để lõi độc lập
    except ImportError:             # không có bộ vẽ -> dùng ảnh reply nguyên bản
        return
    done: dict[tuple[str, str], str] = {}
    for x in timed:
        ctx = (x.get("context") or "").strip()
        if not ctx or not x["clip"] or Path(x["clip"]).suffix.lower() not in IMAGE_EXT:
            continue
        key = (x["clip"], ctx)
        if key not in done:
            try:
                out = job / f"ctx_{len(done):02d}.png"
                done[key] = str(ts.context_card(Path(x["clip"]), ctx, out,
                                                max_h=max_h or opt.meme_h))
            except Exception:  # noqa: BLE001
                continue          # ảnh lỗi / không đọc được -> giữ ảnh reply nguyên bản
        x["clip"] = done[key]


def beat_audio(spoken: str, opt: Options) -> np.ndarray:
    """Read a speech or image-only sound beat as mono 48 kHz audio."""
    sound = opt.threads and spoken in ('[sound]', '[zoom]')
    source = MUSIC_DIR / 'videoplayback.m4a' if sound else synth(spoken, opt.backend, opt.voice, opt.speed)
    if not source.is_file():
        raise ValueError('Không tìm thấy âm thanh cho nhịp ảnh: assets/music/videoplayback.m4a')
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if sound:
        key = hashlib.sha1(f'{source.resolve()}|{source.stat().st_mtime_ns}'.encode()).hexdigest()[:20]
        converted = CACHE_DIR / f'sound_{key}_48000.wav'
    else:
        converted = CACHE_DIR / f'{source.stem}_48000.wav'
    if not converted.is_file():
        run_ffmpeg(['-i', str(source), '-ac', '1', '-ar', '48000', str(converted)], CACHE_DIR)
    audio, _sr = sf.read(str(converted), dtype='float32')
    if not len(audio):
        raise ValueError('File âm thanh của nhịp đang trống.')
    return audio * 0.6 if sound else audio


def voice_lines(rows: list[list], opt: Options, index: int | None = None,
                force: bool = False, cb=None) -> list[dict]:
    """Sinh giọng đọc cho từng nhịp (chỉ âm thanh), dùng chung cache với lúc dựng video.

    `index` = chỉ làm lại một nhịp (0-based); `force` = xoá cache của nhịp đó rồi sinh lại.
    Nhịp `[sound]`/`[zoom]` không có giọng đọc nên trả về `kind: 'sfx'`, không tạo file.
    """
    cb = cb or (lambda f, m: None)
    spoken_lines: list[tuple[int, str]] = []
    for i, r in enumerate(rows):
        if r is None or len(r) < 5:
            continue
        spoken = str(r[1] or "").replace("*", "").strip()
        if not spoken and opt.threads and r[4]:
            spoken = "[sound]"
        if spoken:
            spoken_lines.append((i, spoken))
    if not spoken_lines:
        raise ValueError("Kịch bản đang trống. Hãy nhập kịch bản và bấm 'Phân tích kịch bản' trước.")
    wanted = list(range(len(spoken_lines))) if index is None else [int(index)]
    items: list[dict] = []
    for completed, n in enumerate(wanted, 1):
        if not 0 <= n < len(spoken_lines):
            raise ValueError(f"Nhịp {n + 1} không có trong kịch bản.")
        row_index, spoken = spoken_lines[n]
        cb(completed / max(1, len(wanted)), f"Sinh giọng nhịp {n + 1}/{len(spoken_lines)}…")
        sound = opt.threads and spoken in ("[sound]", "[zoom]")
        if sound:
            items.append({"beat": n + 1, "row": row_index, "text": spoken,
                          "kind": "sfx", "seconds": 0.0, "cached": True, "path": ""})
            continue
        key = hashlib.sha1(f"{opt.backend}|{opt.voice}|{opt.speed:.2f}|{spoken}".encode("utf-8")).hexdigest()[:20]
        cached = (CACHE_DIR / f"{key}.wav").is_file()
        if force:
            (CACHE_DIR / f"{key}.wav").unlink(missing_ok=True)
            (CACHE_DIR / f"{key}_raw.wav").unlink(missing_ok=True)
            (CACHE_DIR / f"{key}_48000.wav").unlink(missing_ok=True)
            cached = False
        path = synth(spoken, opt.backend, opt.voice, opt.speed)
        items.append({"beat": n + 1, "row": row_index, "text": spoken, "kind": "voice",
                      "seconds": round(float(sf.info(str(path)).duration), 2),
                      "cached": cached, "path": str(path)})
    return items


def _background_filter(fps: int, total: float, motion: bool) -> str:
    if motion and total > 2:
        # Keep the 2x sampling grid for smooth subpixel movement, but sample directly
        # into the final frame instead of resizing a changing 4K-sized intermediate.
        width, height = W * 2, H * 2
        zoom = f"(1+0.10*min(in_time,{total:.2f})/{total:.2f})"
        return (f"[0:v]fps={fps}:start_time=0,scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},zoompan=z='{zoom}':"
                f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={fps},"
                "setsar=1,format=yuv420p[v0]")
    return (f"[0:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,format=yuv420p[v0]")


def _pass_bounds(n_spans: int, fps: int) -> list[int]:
    """Cụm mục card mỗi pass. 60fps giữ cụm nhỏ vì mỗi overlay chiếm buffer 1080x1920."""
    per_pass = 10 if fps > 30 else 22
    chunk_at = 14 if fps > 30 else 45
    return list(range(0, n_spans, per_pass)) if n_spans > chunk_at else [0]


def render(rows: list[list], opt: Options, preview: bool = False, cb=None) -> Path:
    """rows: [[#, lời đọc, chữ hiển thị, thẻ, clip, ngữ cảnh?, zoom?], ...]  ->  đường dẫn file MP4."""
    cb = cb or (lambda f, m: None)
    rng = random.Random(opt.seed)

    beats: list[Beat] = []
    zooms: list[bool] = []
    for r in rows:
        if r is None or len(r) < 5:
            continue
        spoken = str(r[1] or "").replace("*", "").strip()
        if not spoken and opt.threads and r[4]:
            spoken = '[sound]'
        if not spoken:
            continue
        # cột 7 (tuỳ chọn) là công tắc zoom; hàng cũ chưa có cột này thì đọc `[zoom]`.
        flag = str(r[6] or "").strip().lower() if len(r) > 6 else None
        zoom = opt.threads and (flag in ('1', 'true', 'on') if flag is not None else spoken == '[zoom]')
        disp_cell = str(r[2] or "").strip()
        display = "" if disp_cell == "-" else (disp_cell or spoken)
        if zoom or (opt.threads and spoken in ('[sound]', '[zoom]')):
            display = ''
        ctx = str(r[5] or "").strip() if len(r) > 5 else ""   # cột 6: ngữ cảnh cha (tuỳ chọn)
        beats.append(Beat(len(beats) + 1, spoken, display, str(r[3] or ""), str(r[4] or ""), ctx))
        zooms.append(zoom)
    if not beats:
        raise ValueError("Kịch bản đang trống. Hãy nhập kịch bản và bấm 'Phân tích kịch bản' trước.")
    normalize_beats(beats)

    job = WORK_DIR / f"job_{datetime.now():%Y%m%d_%H%M%S}"
    job.mkdir(parents=True, exist_ok=True)

    # 1) giọng đọc từng dòng
    n = len(beats)
    sr = 48000
    audios: list[np.ndarray] = []
    for i, b in enumerate(beats):
        cb(0.05 + 0.45 * i / n, f"Chuẩn bị âm thanh nhịp {i + 1}/{n}…")
        audios.append(beat_audio(b.spoken, opt))

    # 2) mốc thời gian
    timed: list[dict] = []
    t = LEAD
    for b, a, zoom in zip(beats, audios, zooms):
        dur = len(a) / sr
        clip_path = resolve_clip(b.clip, opt.content)
        timed.append({
            "display": b.display, "start": t, "dur": dur,
            "clip": str(clip_path) if clip_path else None,
            "context": b.context,
            'zoom': zoom,
            # Nhịp mở màn bằng tiếng videoplayback: chính nó là tiếng chuyển mục,
            # không cần thêm pop ở section_starts.
            'sound': opt.threads and b.spoken in ('[sound]', '[zoom]'),
        })
        # Nhịp zoom đọc/nghe hết tiếng rồi giữ thêm một nhịp để card to kịp hiện.
        t += dur + (ZOOM_HOLD if zoom else 0.0) + opt.gap + _pause_after(b.spoken)
    total = t - opt.gap + TAIL
    for i, x in enumerate(timed):
        nxt = timed[i + 1]["start"] if i + 1 < len(timed) else total
        x["vis_start"] = 0.0 if i == 0 else x["start"]
        x["vis_end"] = nxt
        x["text_end"] = x["start"] + x["dur"] + (opt.gap if i + 1 < len(timed) else 0.3)

    # 3) âm thanh ghép
    mix = np.zeros(int(total * sr) + sr, dtype=np.float32)
    for x, a in zip(timed, audios):
        s = int(x["start"] * sr)
        mix[s:s + len(a)] += a
    peak = float(np.max(np.abs(mix))) or 1.0
    if peak > 0.98:
        mix = mix / peak * 0.98
    sf.write(str(job / "voice.wav"), mix[:int(total * sr)], sr)

    # 4) font chữ (phụ đề ghi sau khi đã biết bố cục Threads)
    fonts = job / "fonts"
    fonts.mkdir(exist_ok=True)
    for f in FONT_DIR.glob("*"):
        if f.suffix.lower() in {".ttf", ".otf", ".ttc"}:
            shutil.copy(f, fonts / f.name)

    # 5) nền
    cb(0.55, "Chuẩn bị nền video…")
    bgs = list_backgrounds()
    if not bgs:
        raise ValueError("Chưa có video nền. Hãy thêm video vào thư mục assets/backgrounds "
                         "hoặc tải lên ở tab 'Thư viện'.")
    bg: Path | None = None
    if opt.bg and opt.bg != "ngẫu nhiên":
        for c in bgs:
            if c.name == opt.bg:
                bg = c
    bg = bg or rng.choice(bgs)
    bg_len = probe_duration(bg)

    bg_args: list[str] = []
    if bg_len > total + 1.0:
        start = rng.uniform(0, bg_len - total - 0.5)
        bg_args += ["-ss", f"{start:.2f}", "-t", f"{total:.2f}", "-i", str(bg)]
    else:
        bg_args += ["-stream_loop", "-1", "-t", f"{total:.2f}", "-i", str(bg)]
    voice_args = ["-i", str(job / "voice.wav")]

    ctx_max = None
    if opt.threads:
        ctx_max = _threads_cap(any(bool((x.get("display") or "").strip()) for x in timed), opt)
    _with_context(timed, opt, job, max_h=ctx_max)
    if opt.threads and (opt.threads_radius > 0 or opt.threads_shadow > 0 or any(opt.card_padding)):
        try:
            from . import threads_shot as ts
            # Một card chỉ bo góc/bóng một lần cho cả mục: các nhịp liền nhau dùng
            # chung file -> _build_spans gộp thành một span, card không "nảy" lại
            # ở từng dòng và bước dựng cũng nhẹ hơn.
            styled: dict[str, str] = {}
            for item in timed:
                clip = item.get("clip")
                if clip and Path(clip).suffix.lower() in IMAGE_EXT:
                    if clip not in styled:
                        out = job / f"round_{len(styled):02d}.png"
                        styled[clip] = str(ts.style_card(Path(clip), opt.threads_radius,
                                                         opt.threads_shadow, out,
                                                         padding_sides=opt.card_padding))
                    item["clip"] = styled[clip]
        except Exception:  # noqa: BLE001
            pass
    spans = _build_spans(timed, opt.carry)
    if opt.threads and spans:
        opt = _threads_opt(opt, spans)
    (job / "subs.ass").write_text(build_ass(timed, opt), encoding="utf-8")
    fps = min(30, int(opt.fps)) if preview else int(opt.fps)
    # Graph dựng hình được chia thành mảnh theo span: mỗi mảnh tự chứa input và
    # chuỗi filter của một mục, với incoming label xác định trước (v{k}, riêng mục
    # đầu là v0/mb). Cuối hàm, các mảnh được ghép theo cụm ~22 mục một pass để RAM
    # không tăng theo số comment; video ngắn vẫn ghép đúng một pass như trước.
    frags: list[dict] = [dict(inputs=bg_args, fg=[_background_filter(fps, total, opt.bg_motion)],
                              in_label="v0", out_label="v0", n_inputs=1)]
    cur_in = "v0"
    # Mascot mở đầu: trồi lên từ đáy khung, dừng hẳn rồi mới đổi biểu cảm (bình
    # thường -> thắc mắc), hết hook thì tụt xuống. Hai lớp overlay chồng lên nhau,
    # mỗi lớp chỉ bật trong đúng khoảng thời gian của nó. Overlay đặt trước card nên
    # card vẫn nằm trên, không bị mascot che.
    if opt.mascot and spans:
        sp0 = spans[0]
        span = sp0["end"] - sp0["start"]
        try:
            from . import mascot as ms
            mp_a = ms.face(0)
            mp_b = ms.face(1)
        except Exception:  # noqa: BLE001
            mp_a = mp_b = None
        if mp_a and mp_b and span > 2.0:
            m_in: list[str] = []
            m_in += ["-loop", "1", "-framerate", "1", "-t", f"{total:.2f}", "-i", str(mp_a)]
            m_in += ["-loop", "1", "-framerate", "1", "-t", f"{total:.2f}", "-i", str(mp_b)]
            mh, appear, hold, hide = MASCOT_H, 0.6, 0.35, 0.35
            bottom = MASCOT_BOTTOM   # chân mascot nằm ngoài khung -> chỉ thấy phần thân
            top = MASCOT_TOP
            t0 = sp0["start"]
            swap_at = t0 + appear + hold
            out_at = max(swap_at + 0.2, sp0["end"] - hide)
            u = f"((t-{t0:.3f})/{appear})"
            v = f"((t-{out_at:.3f})/{hide})"
            # y là mép trên của lớp phủ: phải chạy từ đáy khung (bottom) lên top,
            # chậm dần rồi đứng hẳn; chiều ngược lại sẽ thành trồi xuống.
            rise = f"{top}+({bottom - top})*(1-{u})*(1-{u})"
            fall = f"{top}+({bottom - top})*{v}*{v}"
            y = (f"if(lt(t,{t0 + appear:.3f}),{rise},"
                 f"if(gt(t,{out_at:.3f}),{fall},{top}))")
            m_fg = [f"[0:v]scale=-2:{mh},setsar=1,fps={fps},format=rgba[a]",
                    f"[{cur_in}][a]overlay=x={_mascot_x(mp_a, mh)}:y='{y}':"
                    f"enable='between(t,{t0:.3f},{swap_at:.3f})'[ma]",
                    f"[1:v]scale=-2:{mh},setsar=1,fps={fps},format=rgba[b]",
                    f"[ma][b]overlay=x={_mascot_x(mp_b, mh)}:y='{y}':"
                    f"enable='between(t,{swap_at:.3f},{sp0['end']:.3f})'[mb]"]
            frags.append(dict(inputs=m_in, fg=m_fg, in_label=cur_in, out_label="mb", n_inputs=2))
            cur_in = "mb"
    # Reply: mục sau được báo trước bằng chính card của nó — hiện mờ, nhỏ bên dưới, nối
    # với card đang đọc bằng một sợi dây; sang mục thì nó trượt lên thay card cũ, card
    # cũ trượt theo cùng quãng như một lần cuộn feed. Comment chính thì nảy vào tại chỗ
    # (pop) và không có card chờ. Nhịp zoom giữ nguyên; card kế tiếp chỉ trượt lên sau
    # khi zoom xong.
    plan = _next_card_plan(spans, opt) if opt.next_card and opt.threads and len(spans) > 2 else None
    for k, sp in enumerate(spans):
        s_in: list[str] = []
        s_fg: list[str] = []
        entry_in = cur_in
        p = Path(sp["clip"])
        img = p.suffix.lower() in IMAGE_EXT
        dur = sp["end"] - sp["start"]
        step = plan[k] if plan else None
        out = step["out"] if step and img else None
        tail_t = out["t"] if out else 0.0
        zoom = opt.threads_zoom / 100 if sp.get('zoom') else 1.0
        box_h = opt.meme_h
        if opt.threads and not sp.get("subs"):
            box_h = _threads_box([sp], opt)
        width = round(opt.meme_w * zoom)
        if opt.threads:
            # Bóng đổ độn thêm viền trong suốt: bù lại để bề ngang card thật đúng meme_w.
            width = round(width * _card_pad(str(p)))
        fit = f"scale={width}:{round(box_h)}:force_original_aspect_ratio=decrease"

        pv = step["pv"] if step else None
        if pv:
            pv_start = pv["start"]
            pv_dur = sp["start"] - pv_start
            y_link = str(pv["top"] - NEXT_CARD_GAP)
            y_card = str(pv["top"])
            s_in += ["-loop", "1", "-framerate", "1", "-t", f"{pv_dur:.2f}", "-i", str(p)]
            pi = 0
            try:
                cpath = next_card.connector(W, NEXT_CARD_GAP, job / f"thread_{k}.png")
            except Exception:  # noqa: BLE001
                cpath = None          # thiếu Pillow -> vẫn có card chờ, chỉ thiếu dây nối
            if cpath is not None:
                s_in += ["-loop", "1", "-framerate", "1", "-t", f"{pv_dur:.2f}", "-i", str(cpath)]
                ci = 1
                # Dây nối tắt trước khi card trượt để không chạy ngược hướng với card.
                s_fg.append(f"[{ci}:v]format=rgba,fps={fps},"
                            f"fade=t=in:st=0:d=0.18:alpha=1,"
                            f"fade=t=out:st={max(0.0, pv_dur - 0.2):.2f}:d=0.2:alpha=1,"
                            f"setpts=PTS-STARTPTS+{pv_start:.3f}/TB[c{k}]")
                s_fg.append(f"[{cur_in}][c{k}]overlay=x=0:y='{y_link}':"
                            f"enable='between(t,{pv_start:.3f},{sp['start']:.3f})'[d{k}]")
                cur_in = f"d{k}"
            # Card chờ không tắt dần ở cuối: đến đúng mốc sang mục thì card chính tiếp
            # quản đúng vị trí/độ sáng này rồi trượt lên, nhờ vậy không bị nháy.
            s_fg.append(f"[{pi}:v]{fit},"
                        f"scale=w='trunc(in_w*{NEXT_CARD_SCALE})':h='trunc(in_h*{NEXT_CARD_SCALE})',"
                        f"setsar=1,fps={fps},"
                        f"eq=brightness={-NEXT_CARD_DIM}:saturation={NEXT_CARD_SAT},"
                        f"format=yuva420p,"
                        f"fade=t=in:st=0:d={min(0.22, pv_dur * 0.4):.2f}:alpha=1,"
                        f"setpts=PTS-STARTPTS+{pv_start:.3f}/TB[p{k}]")
            s_fg.append(f"[{cur_in}][p{k}]overlay=x='(W-w)/2':y='{y_card}':"
                        f"enable='between(t,{pv_start:.3f},{sp['start']:.3f})'[q{k}]")
            cur_in = f"q{k}"

        main_dur = dur + tail_t
        i = s_in.count("-i")
        if img:
            s_in += ["-loop", "1", "-framerate", "1", "-t", f"{main_dur:.2f}", "-i", str(p)]
        else:
            s_in += ["-stream_loop", "-1", "-t", f"{dur:.2f}", "-i", str(p)]
        chain = f"[{i}:v]{fit},setsar=1,fps={fps}"
        # Fade tắt dần phải nằm TRƯỚC bước scale chạy theo thời gian: fade đòi kích
        # thước khung không đổi, còn card trượt/nảy thì đổi cỡ từng khung.
        if out:
            # Card cũ trượt lên trong lúc card kế tiếp lên thay: tắt dần ở cuối để mép
            # còn sót lại không biến mất đột ngột.
            chain += f",fade=t=out:st={max(0.0, main_dur - 0.3):.3f}:d=0.3:alpha=1"
        new_section = k == 0 or sp.get("clip") != spans[k - 1].get("clip")
        entering = bool(step and step["in"])
        if entering:
            # Trượt lên từ vị trí chờ (hoặc từ đáy khung khi không còn chỗ chờ) và sáng
            # dần tới màu thật. Chạy theo thời gian riêng của card (mốc 0 = lúc vào mục).
            s0 = NEXT_CARD_SCALE if pv else 0.94
            tint = step["in"]["t"]
            ease = f"(1-pow(1-min(max(t/{tint:.3f},0),1),3))"
            # eq cũng đòi kích thước khung cố định nên đặt trước bước scale theo thời gian.
            chain += (f",eq=brightness='{NEXT_CARD_DIM:.3f}*{ease}-{NEXT_CARD_DIM:.3f}':"
                      f"saturation='{NEXT_CARD_SAT:.3f}+{1 - NEXT_CARD_SAT:.3f}*{ease}':eval=frame")
            chain += (f",scale=w='trunc(in_w*({s0:.3f}+{1 - s0:.3f}*{ease}))':"
                      f"h='trunc(in_h*({s0:.3f}+{1 - s0:.3f}*{ease}))':eval=frame")
        elif sp.get("zoom") and new_section and dur > 0.3:
            # Nhịp chỉ có ảnh: không có bước hiện-ra riêng — card đứng sẵn ở cỡ thường
            # rồi phóng ngay, cú phóng tự vọt quá cỡ và trở lại nên có độ nảy.
            grow = _zoom_scale(zoom)
            chain += (f",scale=w='trunc(in_w*{grow})':"
                      f"h='trunc(in_h*{grow})':eval=frame")
        elif opt.pop_in and opt.threads and new_section and dur > 0.6:
            # Card nảy vào: hơi nhỏ -> phóng quá cỡ -> về đúng cỡ. Chạy theo thời gian
            # riêng của card (mốc 0 ở đầu mục) nên khớp đúng lúc card xuất hiện.
            pop = ("(if(lt(t,0.18),0.65+0.40*t/0.18,"
                   "max(1.05-0.05*(t-0.18)/0.16,1)))")
            chain += f",scale=w='trunc(in_w*{pop})':h='trunc(in_h*{pop})':eval=frame"
        elif opt.card_motion and p.suffix.lower() in IMAGE_EXT and dur > 0.4:
            # Card nảy nhẹ rồi về đúng cỡ: nảy nhanh nên mắt thấy liền mạch. Trôi rất
            # chậm kiểu trước (vài px/giây) bị giật từng khung do phải làm tròn kích thước.
            enter = min(0.20, max(0.12, dur * 0.15))
            up, down = enter * 0.4, enter * 0.6
            # Nhánh hoàn lại phải kẹp ở 1.0: không kẹp thì cả mục card teo/nở dần
            # (khoảng 37%/giây) chứ không đứng yên.
            if k % 2:
                grow = (f"(if(lt(t,{up:.3f}),1.04-0.06*t/{up:.3f},"
                        f"min(0.98+0.02*(t-{up:.3f})/{down:.3f},1)))")
            else:
                grow = (f"(if(lt(t,{up:.3f}),0.96+0.07*t/{up:.3f},"
                        f"max(1.03-0.03*(t-{up:.3f})/{down:.3f},1)))")
            chain += f",scale=w='trunc(in_w*{grow})':h='trunc(in_h*{grow})':eval=frame"
        chain += f",format=yuva420p,setpts=PTS-STARTPTS+{sp['start']:.3f}/TB[m{k}]"
        s_fg.append(chain)
        # Threads có chữ: card dính đáy khung chung; không chữ: card canh giữa dọc.
        # Video thường giữ cách cũ: ảnh canh hơi lệch LÊN giữa màn hình khi không có chữ.
        # Bài post mở đầu: đẩy card lên trên đỉnh mascot, không để card đè lên đầu mascot.
        hook_card = opt.mascot and k == 0 and dur > 2.0 and not sp.get("subs")
        if step and img and (entering or out):
            top = step["geo"]["top"]
            if hook_card:
                top = min(top, MASCOT_TOP - MASCOT_CARD_GAP - step["geo"]["h"])
            y = str(top)
            if out and out["delta"]:
                te, ot = sp["end"], out["t"]
                eo = f"(1-pow(1-min(max((t-{te:.3f})/{ot:.3f},0),1),3))"
                y = f"if(lt(t,{te:.3f}),{y},{top}-{out['delta']}*{eo})"
            if entering:
                y0, t0, it = step["in"]["y0"], sp["start"], step["in"]["t"]
                ei = f"(1-pow(1-min(max((t-{t0:.3f})/{it:.3f},0),1),3))"
                y = (f"if(lt(t,{t0:.3f}),{y0},"
                     f"if(lt(t,{t0 + it:.3f}),{y0}+({top}-{y0})*{ei},{y}))")
        elif opt.threads:
            y = _overlay_y_threads(opt, bool(sp.get("subs")))
            if hook_card:
                y = f"min({y},{MASCOT_TOP - MASCOT_CARD_GAP}-h)"
        else:
            y = "(H-h)*0.40" if not sp.get("subs", True) else _overlay_y(opt)
        xs = "(W-w)/2"
        s_fg.append(
            f"[{cur_in}][m{k}]overlay=x='{xs}':y='{y}':"
            f"enable='between(t,{sp['start']:.3f},{sp['end'] + tail_t:.3f})'[v{k + 1}]"
        )
        frags.append(dict(inputs=s_in, fg=s_fg, in_label=entry_in,
                          out_label=f"v{k + 1}", n_inputs=s_in.count("-i")))
        cur_in = f"v{k + 1}"

    tail = "ass=subs.ass:fontsdir=fonts"
    if preview:
        tail += ",scale=540:960"

    # 6) dựng theo cụm: video nhiều mục (kịch bản Threads dài) sinh graph hàng trăm
    # node overlay nối tiếp — gộp một lần vừa vượt giới hạn dòng lệnh của Windows,
    # vừa đòi RAM theo số node. Chia span thành cụm ~22 mục: pass đầu nướng nền và
    # cụm đầu, các pass sau overlay tiếp lên file trung gian (crf 12, hao hụt không
    # thấy được), pass cuối trộn âm thanh rồi mã hóa bằng encoder chính. Video ngắn
    # hơn ngưỡng vẫn đi đúng một pass như cũ.
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    if preview:
        out_name = f"preview_{stamp}.mp4"
    else:
        # tên file có chủ đề (tên Nội dung) để phân biệt video trong output/
        topic = norm_tag(opt.content)[:40] or "video"
        out_name = f"video_{topic}_{stamp}.mp4"
    out_path = (WORK_DIR if preview else OUT_DIR) / out_name

    n_spans = len(spans)
    # Mỗi mục card giữ buffer frame 1080x1920 trong graph, ~100MB lúc 60fps; dồn
    # hơn chục mục vào một pass là FFmpeg xin vài GB commit và báo "Cannot allocate
    # memory" trên máy đang chạy nhiều app. 60fps vì thế chia cụm nhỏ hơn 30fps
    # (tổng khối lượng overlay không đổi, chỉ thêm chi phí nền mỗi pass).
    bounds = _pass_bounds(n_spans, fps)
    pre = frags[:len(frags) - n_spans]      # nền + mascot
    body = frags[len(frags) - n_spans:]     # từng mục card
    prev_out: Path | None = None
    tmp_outs: list[Path] = []
    for pi_, b0 in enumerate(bounds):
        b1 = bounds[pi_ + 1] if pi_ + 1 < len(bounds) else n_spans
        is_first, is_last = pi_ == 0, pi_ == len(bounds) - 1
        p_args: list[str] = []
        fg_p: list[str] = []
        if is_first:
            # pass 1: nền là input đầu tiên (index 0), giọng đọc ngay sau (index 1)
            head, *rest = pre
            p_args += head["inputs"]
            off = p_args.count("-i") - head["n_inputs"]
            for c in head["fg"]:
                fg_p.append(re.sub(r"\[(\d+):", lambda m: f"[{int(m.group(1)) + off}:", c))
            if is_last:
                p_args += voice_args
            for fr in rest:
                p_args += fr["inputs"]
                off = p_args.count("-i") - fr["n_inputs"]
                for c in fr["fg"]:
                    fg_p.append(re.sub(r"\[(\d+):", lambda m: f"[{int(m.group(1)) + off}:", c))
        else:
            p_args += ["-i", str(prev_out)]
            if is_last:
                p_args += voice_args
        group = body[b0:b1]
        for si_, fr in enumerate(group):
            # Đánh số lại input trước, rồi mới thay nhãn incoming của span đầu:
            # làm ngược lại thì [0:v] vừa thay sẽ bị regex coi là chỉ số cục bộ
            # và bị dịch đi, trỏ nhầm vào ảnh card thay vì file cụm trước.
            off = p_args.count("-i")
            chains = [re.sub(r"\[(\d+):", lambda m: f"[{int(m.group(1)) + off}:", c)
                      for c in fr["fg"]]
            if si_ == 0 and not is_first:
                chains = [c.replace(f"[{fr['in_label']}]", "[0:v]") for c in chains]
            p_args += fr["inputs"]
            for c in chains:
                fg_p.append(c)
        last_out = f"v{b1}"
        if is_last:
            fg_p.append(f"[{last_out}]{tail}[vout]")
            # 5c) âm thanh: giọng đọc + tiếng chuyển mục (pop / whoosh) + nhạc nền
            fg_p.append("[1:a]anull[a0]")
            audio_mix = ["[a0]"]
            pop = opt.pop_in and opt.threads
            # Card nảy vào ngay từ đầu video (bài post) nên pop cũng kêu từ mục đầu tiên.
            section_starts = _pop_starts(spans, first=pop)
            sfx_path = next((m for m in list_music()
                             if m.name.lower().startswith("pop" if pop else "whoosh")), None)
            if opt.sfx and section_starts and sfx_path is not None:
                p_args += ["-i", str(sfx_path)]
                n = len(section_starts)
                labels = "".join(f"[w{j}]" for j in range(n))
                # Pop.mp3 có sẵn ~0.14s im lặng đầu file; cắt đi để tiếng nổ khớp lúc card
                # phóng tới cỡ lớn nhất chứ không trễ nửa nhịp.
                trim = ("atrim=start=0.14:end=0.5,afade=t=out:st=0.22:d=0.14,volume=0.50" if pop
                        else "atrim=0:0.8,volume=0.35")
                fg_p.append(f"[{p_args.count('-i') - 1}:a]{trim},asetpts=N/SR/TB,asplit={n}{labels}")
                for j, st in enumerate(section_starts):
                    ms_ = int(round(st * 1000))
                    fg_p.append(f"[w{j}]adelay={ms_}|{ms_}[s{j}]")
                    audio_mix.append(f"[s{j}]")
            music = list_music() if opt.use_music else []
            if music:
                mpath = rng.choice(music)
                p_args += ["-stream_loop", "-1", "-i", str(mpath)]
                fg_p.append(f"[{p_args.count('-i') - 1}:a]volume={opt.music_volume:.3f}[mu]")
                audio_mix.append("[mu]")
            fg_p.append("".join(audio_mix) + f"amix=inputs={len(audio_mix)}:duration=first:"
                                           f"dropout_transition=0:normalize=0[aout]")
            amap = "[aout]"
            if preview:
                venc = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30"]
            elif opt.nvenc:
                venc = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0"]
            else:
                venc = [*CPU_VENC]
            dst = out_path
        else:
            fg_p.append(f"[{last_out}]format=yuv420p[vout]")
            venc = ["-c:v", "libx264", "-crf", "12", "-preset", "veryfast"]
            amap = None
            dst = job / f"pass_{pi_}.mp4"
        filter_src = ";".join(fg_p)
        if len(filter_src) > 30000:
            # Windows chặn dòng lệnh ~32.767 ký tự; graph to vẫn ghi filter ra file,
            # ffmpeg đọc bằng -/filter_complex (bản ffmpeg 8+ bỏ -filter_complex_script).
            fpath = (job / f"filter_{pi_}.txt").resolve()
            fpath.write_text(filter_src, encoding="utf-8")
            p_args += ["-/filter_complex", str(fpath)]
        else:
            p_args += ["-filter_complex", filter_src]
        p_args += ["-map", "[vout]"]
        if is_last:
            p_args += ["-map", amap, "-c:a", "aac", "-q:a", "4", "-movflags", "+faststart"]
        else:
            p_args += ["-an"]
        p_args += [*venc, "-pix_fmt", "yuv420p", "-r", str(fps),
                   "-t", f"{total:.2f}", str(dst)]
        cb(0.6 + 0.35 * (pi_ + 1) / len(bounds),
           f"Đang dựng video… (cụm {pi_ + 1}/{len(bounds)})" if len(bounds) > 1
           else ("Đang xuất video…" if not preview else "Đang dựng bản xem thử…"))
        if len(fg_p) > 200:
            # Graph nhiều node: mỗi overlay cấp phát buffer theo số luồng filter;
            # các node chủ yếu là overlay bậc thang chỉ đưa ảnh qua nên chạy 1 luồng
            # gần như không mất tốc độ nhưng giảm mạnh RAM commit.
            p_args.insert(0, "-filter_complex_threads")
            p_args.insert(1, "1")
        try:
            run_ffmpeg(p_args, job)
        except RuntimeError as exc:
            # NVENC hỏng giữa chừng (CreateBitstreamBuffer failed: out of memory trên
            # card 4GB) thì xuất lại bằng CPU thay vì bỏ cả lần dựng.
            if preview or not is_last or not opt.nvenc:
                raise
            reason = next((line for line in str(exc).splitlines()
                           if "nvenc" in line.lower()), str(exc).splitlines()[-1])
            cb(0.96, f"GPU không xuất được ({reason.strip()[:140]}) — xuất lại bằng CPU…")
            run_ffmpeg(swap_encoder(p_args, venc, [*CPU_VENC]), job)
        if not is_last:
            tmp_outs.append(dst)
        prev_out = dst
    for t_ in tmp_outs:
        try:
            t_.unlink()
        except OSError:
            pass
    if not preview:
        # Ghi kèm nguồn nội dung để lúc đăng Facebook biết bài Threads nào đã tạo ra video.
        try:
            (job / 'output.json').write_text(json.dumps({'video': out_path.name}), encoding='utf-8')
            out_path.with_suffix(".json").write_text(json.dumps(
                {"content": opt.content or "",
                 "render_job": job.name,
                 "created": datetime.now().isoformat(timespec="seconds")},
                ensure_ascii=False, indent=2), "utf-8")
        except OSError:
            pass
    cb(1.0, "Xong")
    return out_path


def preview_frame(text: str, opt: Options, clip: str = "", context: str = "", *, zoom: bool = False) -> tuple[Path, list[str]]:
    """Dựng 1 khung hình PNG theo bố cục hiện tại — không cần giọng đọc, chạy ~1 giây.

    `clip` (tuỳ chọn) là file cụ thể trong thư viện meme / minh họa để đặt vào khung;
    bỏ trống thì lấy file đầu tiên như trước. `context` là ngữ cảnh cha của reply
    Threads ('@tên: trích đoạn') — có thì ghép khung nhỏ ↳ phía trên ảnh (chỉ vẽ
    trích đoạn, không hiện tên).
    `text` bỏ trống = xem bố cục KHÔNG phụ đề (nhịp `|| -`): không vẽ chữ, card phủ đủ
    bề ngang và canh giữa dọc khung, đúng như video sẽ dựng.
    Trả về (đường dẫn ảnh, danh sách cụm chữ video sẽ hiện).
    """
    text = (text or "").strip()
    bgs = list_backgrounds()
    if not bgs:
        raise ValueError("Chưa có video nền. Hãy thêm video vào assets/backgrounds "
                         "hoặc tải lên ở tab 'Thư viện'.")
    rng = random.Random(opt.seed)
    bg = next((c for c in bgs if c.name == opt.bg), None) or rng.choice(bgs)

    stamp = f"{datetime.now():%Y%m%d_%H%M%S_%f}"
    subs = WORK_DIR / f"frame_{stamp}.ass"
    out = WORK_DIR / f"frame_{stamp}.png"
    fonts = WORK_DIR / "fonts_preview"
    fonts.mkdir(exist_ok=True)
    for f in FONT_DIR.glob("*"):
        if f.suffix.lower() in {".ttf", ".otf", ".ttc"}:
            shutil.copy(f, fonts / f.name)

    clip_path: Path | None = None
    if (clip or "").strip():
        clip_path = resolve_clip(clip, opt.content)
    if clip_path is None:
        clip_path = next((files[0] for files in scan_memes().values() if files), None)
    if clip_path is None and opt.content:
        for files in scan_illust(opt.content).values():
            if files:
                clip_path = files[0]
                break
    if clip_path is not None and (context or "").strip() \
            and clip_path.suffix.lower() in IMAGE_EXT:
        try:
            from . import threads_shot as ts
            ctx_max = _threads_cap(bool(text), opt) if opt.threads else opt.meme_h
            clip_path = ts.context_card(clip_path, context.strip(),
                                        WORK_DIR / f"frame_{stamp}_ctx.png", max_h=ctx_max)
        except Exception:  # noqa: BLE001
            pass          # không ghép được thì xem thử ảnh reply nguyên bản
    if (opt.threads and (opt.threads_radius > 0 or opt.threads_shadow > 0 or any(opt.card_padding)) and clip_path is not None
            and clip_path.suffix.lower() in IMAGE_EXT):
        try:
            from . import threads_shot as ts
            clip_path = ts.style_card(clip_path, opt.threads_radius, opt.threads_shadow,
                                      WORK_DIR / f"frame_{stamp}_style.png", padding_sides=opt.card_padding)
        except Exception:  # noqa: BLE001
            pass
    if opt.threads and clip_path is not None:
        opt = _threads_opt(opt, [{"clip": str(clip_path), "subs": bool(text), "zoom": zoom}])

    chunks: list[str] = []
    if text:
        timed = [{"display": text, "start": 0.0, "dur": 9.0, "text_end": 9.0}]
        chunks = split_chunks(text, opt.max_words)
        # ảnh tĩnh không có mốc "đang đọc" nên tắt karaoke để hiện đủ chữ như video sẽ đọc
        subs.write_text(build_ass(timed, replace(opt, karaoke=False)), encoding="utf-8")

    bg_len = probe_duration(bg)
    start = rng.uniform(0, bg_len - 10) if bg_len > 11 else 0.0
    args = ["-ss", f"{start:.2f}", "-t", "9", "-i", str(bg)]
    filters = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
               f"crop={W}:{H},setsar=1[bg]"]
    label = "bg"
    if clip_path is not None:
        args += ["-i", str(clip_path)]
        factor = opt.threads_zoom / 100 if opt.threads and zoom else 1.0
        box_h = opt.meme_h if opt.threads else round(opt.meme_h * factor)
        width = round(opt.meme_w * factor)
        if opt.threads:
            width = round(width * _card_pad(str(clip_path)))
        filters.append(f"[1:v]scale={width}:{box_h}:"
                       f"force_original_aspect_ratio=decrease,setsar=1[m]")
        if opt.threads:
            y = _overlay_y_threads(opt, bool(text))
        else:
            # không có chữ -> ảnh canh hơi lệch lên, giống render() với nhịp '|| -'
            y = "(H-h)*0.40" if not text else _overlay_y(opt)
        filters.append(f"[bg][m]overlay=x=(W-w)/2:y={y}[c]")
        label = "c"
    if text:
        filters.append(f"[{label}]ass={subs.name}:fontsdir={fonts.name}[v]")
    else:
        filters.append(f"[{label}]null[v]")
    # lấy khung ở giây 0.6 để hiệu ứng nảy chữ đã chạy xong
    args += ["-filter_complex", ";".join(filters), "-map", "[v]",
             "-ss", "0.6", "-frames:v", "1", str(out)]
    try:
        run_ffmpeg(args, WORK_DIR)
    finally:
        subs.unlink(missing_ok=True)
    return out, chunks


def analyze(script: str, seed: int | None = None, content: str = "") -> list[list]:
    beats = parse_script(script)
    assign_clips(beats, seed, content)
    # Dấu - phải sống qua bảng chỉnh sửa; chuỗi rỗng khi render có nghĩa dùng lại lời đọc.
    return [[b.idx, b.spoken, b.display if b.display else "-", b.tag, b.clip] for b in beats]


