"""Đăng / hẹn giờ Facebook Reels lên Page qua Reels Publishing API.

Chỉ Page mới đăng được bằng API (trang cá nhân không có quyền này).

Page ID + token lấy theo thứ tự ưu tiên:
1. biến môi trường của máy: `FB_PAGE_ID`, `FB_PAGE_TOKEN` (+ `FB_GRAPH_VERSION`);
2. file `work/fb.env` (cùng dạng `KEY=VALUE`, đọc lại mỗi lần gọi);
3. `work/fb_config.json` do app lưu khi bạn nhập tay.

Token lấy từ (1) hoặc (2) **không bao giờ bị ghi xuống** `fb_config.json`.

Hẹn giờ là hẹn giờ *của Facebook*: video được tải lên ngay, Facebook tự đăng lúc đã hẹn
nên app có tắt cũng không ảnh hưởng.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlsplit
from datetime import datetime, timedelta
from pathlib import Path

import requests

from .paths import APP_DIR
CONFIG_PATH = APP_DIR / "work" / "fb_config.json"
ENV_PATH = APP_DIR / "work" / "fb.env"

DEFAULT_VERSION = "v24.0"
GRAPH = "https://graph.facebook.com"

# Meta: thời điểm hẹn phải sau ít nhất 10 phút và trong vòng 30 ngày (Pages API).
MIN_LEAD = timedelta(minutes=11)
MAX_AHEAD = timedelta(days=30)
MAX_BYTES = 1_000_000_000          # giới hạn file của app

ENV_KEYS = {
    "page_id": ("FB_PAGE_ID", "FACEBOOK_PAGE_ID"),
    "token": ("FB_PAGE_TOKEN", "FACEBOOK_PAGE_TOKEN", "FB_ACCESS_TOKEN"),
    "version": ("FB_GRAPH_VERSION", "FACEBOOK_GRAPH_VERSION"),
}

DEFAULTS = {
    "page_id": "",
    "token": "",
    "version": DEFAULT_VERSION,
    "hashtags": "",
    "graph_base": GRAPH,
}


class FbError(RuntimeError):
    """Lỗi trả về từ Graph API (kèm gợi ý cho các mã thường gặp)."""


# --------------------------------------------------------------------------- cấu hình
def _file_config() -> dict:
    """Chỉ đọc `work/fb_config.json` (không trộn env)."""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    return data


def _env_file() -> dict:
    """Đọc `work/fb.env` dạng KEY=VALUE, bỏ dòng trống và dòng bắt đầu bằng #."""
    out: dict[str, str] = {}
    try:
        text = ENV_PATH.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        out[key] = val.strip().strip('"').strip("'")
    return out


def env_creds() -> dict:
    """Page ID / token / version từ biến môi trường, thiếu thì lấy từ `work/fb.env`."""
    data: dict[str, str] = {}
    for field, keys in ENV_KEYS.items():
        for key in keys:
            val = (os.environ.get(key) or "").strip()
            if val:
                data[field] = val
                break
    file = _env_file()
    for field, keys in ENV_KEYS.items():
        if field in data:
            continue
        for key in keys:
            if (file.get(key) or "").strip():
                data[field] = file[key].strip()
                break
    return data


def creds_source() -> str:
    """'env' | 'env-file' | 'config' | '' — nguồn Page ID/token đang dùng."""
    if any((os.environ.get(k) or "").strip() for keys in ENV_KEYS.values() for k in keys):
        return "env"
    file = _env_file()
    if any((file.get(k) or "").strip() for keys in ENV_KEYS.values() for k in keys):
        return "env-file"
    if (_file_config().get("token") or "").strip():
        return "config"
    return ""


def load_config() -> dict:
    """Cấu hình đang dùng: mặc định → file → env (env thắng)."""
    cfg = {**DEFAULTS, **_file_config()}
    cfg.update(env_creds())
    return cfg


def save_config(**fields) -> dict:
    """Ghi `work/fb_config.json`; không bao giờ ghi giá trị lấy từ env."""
    cfg = {**DEFAULTS, **_file_config()}
    cfg.update({k: v for k, v in fields.items() if v is not None})
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")
    return load_config()


# --------------------------------------------------------------------------- sổ video đã hẹn
POSTED_PATH = APP_DIR / "work" / "fb_posted.json"


def posted_log() -> dict:
    """{tên file video: {id, when, at}} — để lần sau không hẹn lại video cũ."""
    try:
        data = json.loads(POSTED_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def mark_posted(video: str, post_id: str, when: datetime | None = None) -> None:
    """Ghi lại video vừa đăng/hẹn (chỉ trên máy, không phải dữ liệu của Facebook)."""
    log = posted_log()
    log[Path(video).name] = {
        "id": (post_id or "").strip(),
        "when": when.strftime("%d/%m/%Y %H:%M") if when else "ngay",
        "at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    try:
        POSTED_PATH.parent.mkdir(parents=True, exist_ok=True)
        POSTED_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), "utf-8")
    except OSError:
        pass


def unmark_posted(post_id: str) -> None:
    """Huỷ hẹn -> trả video về danh sách chưa đăng (để hẹn lại được)."""
    post_id = (post_id or "").strip()
    if not post_id:
        return
    log = posted_log()
    keep = {name: item for name, item in log.items()
            if not (isinstance(item, dict) and (item.get("id") or "") == post_id)}
    if len(keep) == len(log):
        return
    try:
        POSTED_PATH.write_text(json.dumps(keep, ensure_ascii=False, indent=2), "utf-8")
    except OSError:
        pass


def booked_times() -> set[str]:
    """Các mốc giờ đã hẹn (dạng `YYYY-MM-DD HH:MM`) để xếp lịch không trùng."""
    out: set[str] = set()
    for item in posted_log().values():
        when = (item or {}).get("when") if isinstance(item, dict) else ""
        try:
            out.add(datetime.strptime(when, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M"))
        except (TypeError, ValueError):
            continue
    return out


def _base(cfg: dict) -> str:
    return (cfg.get("graph_base") or GRAPH).rstrip("/")


def _ver(version: str | None, cfg: dict) -> str:
    v = (version or cfg.get("version") or DEFAULT_VERSION).strip()
    return v if v.startswith("v") else "v" + v


# --------------------------------------------------------------------------- lỗi API
_HINTS = {
    190: "Token sai hoặc đã hết hạn — lấy Page access token mới.",
    200: "Token chưa có quyền cho thao tác trên Page đích. Kiểm tra đúng Page access token, "
         "pages_manage_posts / pages_read_engagement và quyền tạo nội dung trên Page.",
    10: "Thiếu quyền hoặc app chưa được cấp quyền cho Page này.",
    100: "Tham số không hợp lệ — xem chi tiết lỗi Facebook ở trên.",
    368: "Page đang bị tạm khoá đăng bài.",
    4: "Đã chạm giới hạn gọi API — thử lại sau ít phút.",
    17: "Đã chạm giới hạn gọi API — thử lại sau ít phút.",
    32: "Đã chạm giới hạn gọi API — thử lại sau ít phút.",
    613: "Đã chạm giới hạn gọi API — thử lại sau ít phút.",
}


def _raise_for(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if resp.status_code == 413:
        raise FbError("HTTP 413: máy chủ từ chối dung lượng yêu cầu tải lên. "
                      "Chưa thể xác nhận Reel đã được tải thành công.")
    if resp.ok and not (isinstance(data, dict) and data.get("error")):
        return data
    err = (data.get("error") if isinstance(data, dict) else None) or {}
    msg = err.get("message") or f"HTTP {resp.status_code} từ Facebook"
    code = err.get("code")
    sub = err.get("error_subcode")
    bits = [msg]
    if code is not None:
        bits.append(f"mã {code}" + (f"/{sub}" if sub else ""))
    hint = _HINTS.get(code) if isinstance(code, int) else None
    if hint:
        bits.append(hint)
    trace = err.get("fbtrace_id")
    if trace:
        bits.append(f"fbtrace {trace}")
    raise FbError(" — ".join(bits))


def _page_params(page_id: str, token: str) -> dict:
    page_id = (page_id or "").strip()
    token = (token or "").strip()
    if not page_id:
        raise FbError("Chưa nhập Page ID.")
    if not token:
        raise FbError("Chưa nhập Page access token.")
    return {"access_token": token, "page_id": page_id}


# --------------------------------------------------------------------------- API
def check(page_id: str, token: str, version: str | None = None,
          cfg: dict | None = None) -> dict:
    """Đọc danh tính của token và đối chiếu Page đích, không tạo bài để thử quyền."""
    cfg = cfg or load_config()
    page_id = (page_id or "").strip()
    token = (token or "").strip()
    if not page_id or not token:
        raise FbError("Nhập Page ID và Page access token trước đã.")
    r = requests.get(
        f"{_base(cfg)}/{_ver(version, cfg)}/me",
        params={"fields": "id,name", "access_token": token},
        timeout=30)
    data = _raise_for(r)
    if not data.get("id"):
        raise FbError("Facebook không trả về Page nào — kiểm tra lại Page ID.")
    if str(data["id"]) != page_id:
        raise FbError(
            f"Token đang đại diện cho ID {data['id']}, khác Page ID {page_id}. "
            "Hãy lấy Page access token của đúng Page cần đăng; không dùng User token "
            "hoặc token của Page khác.")
    return data


def upload_reel(page_id: str, token: str, path: str | Path, caption: str,
                 when: datetime | None = None, version: str | None = None,
                 cfg: dict | None = None) -> dict:
    """Reel: start qua Graph → binary stream tới rupload → finish PUBLISHED/SCHEDULED.

    Không tự lặp start/finish khi mất phản hồi: có thể tạo Reel trùng.
    Chỉ trả ID cho bên gọi sau khi Facebook xác nhận finish thành công.
    """
    cfg = cfg or load_config()
    p = _page_params(page_id, token)
    src = Path(path)
    if not src.is_file():
        raise FbError(f"Không thấy file video: {src}")
    size = src.stat().st_size
    if size <= 0:
        raise FbError("File video rỗng (0 byte) — chọn file khác.")
    if size > MAX_BYTES:
        raise FbError(f"Video {size / 1e9:.2f} GB — app hiện hỗ trợ file tối đa 1 GB. "
                      f"Hãy nén bớt rồi đăng lại.")
    if when:
        _validate_reel_time(when)

    url = f"{_base(cfg)}/{_ver(version, cfg)}/{p['page_id']}/video_reels"
    video_id = None
    phase = "tạo phiên Reel"
    try:
        started = _raise_for(requests.post(
            url, data={"access_token": token, "upload_phase": "start"},
            timeout=(30, 60), allow_redirects=False))
        video_id = str(started.get("video_id") or "")
        upload_url = started.get("upload_url") or ""
        if not video_id.isdigit() or not isinstance(upload_url, str):
            raise FbError("Facebook không trả về video_id / upload_url hợp lệ cho Reel.")
        # Chỉ gửi Page token tới máy chủ tải Reel chính thức, không theo redirect.
        parsed = urlsplit(upload_url)
        if (parsed.scheme != "https" or parsed.netloc != "rupload.facebook.com"
                or not parsed.path.startswith("/video-upload/")):
            raise FbError("Facebook trả về upload_url không hợp lệ cho Reel.")
        phase = "tải file Reel"
        with src.open("rb") as body:
            uploaded = _raise_for(requests.post(
                upload_url, data=body,
                headers={"Authorization": f"OAuth {token}", "offset": "0",
                         "file_size": str(size), "Content-Length": str(size),
                         "Content-Type": "application/octet-stream"},
                timeout=(30, 1800), allow_redirects=False))
        if uploaded.get("success") is not True:
            raise FbError("Facebook chưa xác nhận tải file Reel thành công.")
        phase = "chốt lịch Reel" if when else "đăng Reel"
        finish = {"access_token": token, "upload_phase": "finish", "video_id": video_id,
                  "video_state": "SCHEDULED" if when else "PUBLISHED",
                  "description": (caption or "").strip()}
        if when:
            # Upload có thể mất vài phút; kiểm tra lại trước khi chốt lịch.
            _validate_reel_time(when)
            finish["scheduled_publish_time"] = str(int(when.timestamp()))
        result = _raise_for(requests.post(url, data=finish, timeout=(30, 120),
                                          allow_redirects=False))
        if result.get("success") is not True:
            raise FbError("Facebook chưa xác nhận hoàn tất Reel. Kiểm tra Meta Business Suite trước khi thử lại.")
        return {"id": video_id, "success": True, "type": "reel"}
    except requests.exceptions.SSLError:
        detail = "Kết nối SSL bị gián đoạn"
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        detail = "Mất kết nối hoặc quá thời gian chờ"
    except FbError as e:
        identity = f" (Reel ID {video_id})" if video_id and video_id.isdigit() else ""
        raise FbError(f"Lỗi ở bước {phase}{identity}: {e}") from None
    identity = f" Reel ID {video_id}." if video_id else ""
    raise FbError(f"{detail} ở bước {phase}.{identity} Chưa xác nhận kết quả. "
                  "Kiểm tra Meta Business Suite trước khi thử lại để tránh trùng Reel.") from None


def _validate_reel_time(when: datetime) -> None:
    now = datetime.now()
    if when <= now + MIN_LEAD:
        raise FbError("Giờ hẹn phải cách hiện tại ít nhất ~11 phút.")
    if when > now + MAX_AHEAD:
        raise FbError("Chọn giờ hẹn trong vòng 30 ngày tới.")


def schedule_reel(page_id: str, token: str, path: str | Path, caption: str,
                   when: datetime, version: str | None = None,
                   cfg: dict | None = None) -> dict:
    """Hẹn Facebook Reel, không gọi endpoint video thường."""
    _validate_reel_time(when)
    return upload_reel(page_id, token, path, caption, when, version, cfg)


def list_scheduled(page_id: str, token: str, version: str | None = None,
                   cfg: dict | None = None) -> list[dict]:
    """Các bài đang chờ đăng (kể cả video đã hẹn giờ)."""
    cfg = cfg or load_config()
    p = _page_params(page_id, token)
    r = requests.get(
        f"{_base(cfg)}/{_ver(version, cfg)}/{p['page_id']}/promotable_posts",
        params={"is_published": "false", "limit": 50, "access_token": token,
                "fields": "id,message,created_time,scheduled_publish_time,"
                          "is_published,attachments{media_type,title}"},
        timeout=60)
    data = _raise_for(r)
    rows: list[dict] = []
    for it in data.get("data") or []:
        ts = it.get("scheduled_publish_time")
        if not ts:
            continue
        try:
            when = datetime.fromtimestamp(int(ts))
        except (TypeError, ValueError, OSError):
            continue
        rows.append({
            "id": it.get("id") or "",
            "message": (it.get("message") or "").strip(),
            "timestamp": int(ts),
            "when": when.strftime("%d/%m/%Y %H:%M"),
            "type": ((it.get("attachments") or {}).get("data") or [{}])[0].get("media_type")
                    or "post",
        })
    rows.sort(key=lambda r: r["timestamp"])
    return rows


def cancel_scheduled(post_id: str, token: str, version: str | None = None,
                     cfg: dict | None = None) -> bool:
    """Huỷ một bài đã hẹn (xoá luôn bài chưa đăng)."""
    cfg = cfg or load_config()
    post_id = (post_id or "").strip()
    token = (token or "").strip()
    if not post_id or not token:
        raise FbError("Chọn bài cần huỷ và nhập token.")
    r = requests.delete(f"{_base(cfg)}/{_ver(version, cfg)}/{post_id}",
                        params={"access_token": token}, timeout=60)
    _raise_for(r)
    return True


# --------------------------------------------------------------------------- tiện ích
def parse_when(text: str) -> datetime:
    """'28/10/2026 20:00' | '2026-10-28 20:00' | '28-10-2026 20:00' -> datetime."""
    s = (text or "").strip()
    if not s:
        raise FbError("Chưa nhập thời gian đăng (hoặc tích 'Đăng ngay').")
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise FbError("Không đọc được thời gian. Ghi kiểu `28/10/2026 20:00`.")


def normalize_tags(tags: str, limit: int = 5) -> str:
    """Giữ ba tag cố định theo yêu cầu; lọc trùng/rác và giới hạn tag bổ sung."""
    return " ".join("#" + t for t in keep_tags(tags, limit))


def keep_tags(tags: str, limit: int = 5) -> list[str]:
    """Ưu tiên hashtag cố định, sau đó các tag bổ sung hợp lệ."""
    from .caption import FIXED_TAGS, GENERIC_TAGS

    seen: list[str] = list(FIXED_TAGS)
    for raw in re.split(r"[\s,;]+", tags or ""):
        t = raw.strip().lstrip("#")
        if not t or not re.fullmatch(r"\w+", t) or len(t) > 24:
            continue
        if t.lower() in GENERIC_TAGS:
            continue
        if t.lower() not in {s.lower() for s in seen}:
            seen.append(t)
    return seen[:limit]


def dropped_tags(tags: str, limit: int = 5) -> list[str]:
    """Tag bị bỏ (chung chung / vượt quá `limit`) để hiện cảnh báo cho người dùng."""
    from .caption import FIXED_TAGS, GENERIC_TAGS

    valid: list[str] = list(FIXED_TAGS)
    dropped: list[str] = []
    for raw in re.split(r"[\s,;]+", tags or ""):
        t = raw.strip().lstrip("#")
        if not t:
            continue
        if not re.fullmatch(r"\w+", t) or len(t) > 24:
            dropped.append(t)
        elif t.lower() in GENERIC_TAGS:
            dropped.append(t)
        elif t.lower() not in {s.lower() for s in valid}:
            valid.append(t)
    dropped.extend(valid[limit:])
    return dropped


def append_tags(caption: str, tags: str) -> str:
    """Thêm khối hashtag vào cuối caption nếu chưa có."""
    cap = (caption or "").rstrip()
    block = normalize_tags(tags)
    if not block:
        return cap
    have = {w.lower() for w in re.split(r"[\s,]+", cap)}
    add = [t for t in block.split() if t.lower() not in have]
    if not add:
        return cap
    return (cap + "\n\n" + " ".join(add)).strip()


def describe_video(path: str | Path) -> str:
    """'video_...mp4 · 126 MB' cho dropdown."""
    p = Path(path)
    try:
        mb = p.stat().st_size / 1e6
    except OSError:
        return p.name
    return f"{p.name} · {mb:.0f} MB"
