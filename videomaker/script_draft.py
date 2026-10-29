"""Kiểm tra nhanh cách đọc TTS trên bảng nhịp: nhịp quá dài, viết tắt còn sót.

Bảng viết tắt dưới đây là nguồn tra cứu của bước kiểm tra; glossary người dùng tự thêm
(`work/tts_glossary.json`) được gộp vào cùng.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import threads_shot as ts

GLOSSARY_FILE = ts.WORK_DIR / "tts_glossary.json"

# Viết tắt phổ biến — chỉ những từ KHÔNG lệch nghĩa theo ngữ cảnh mới để máy tự đổi;
# đại từ (t, m) và slang mơ hồ ("m10", "si"…) không tự đoán, để lại cho cổng duyệt.
_TEENCODE = {
    "đc": "được", "dc": "được", "ko": "không", "k": "không", "hok": "không",
    "hong": "không", "ms": "mới", "bh": "bây giờ", "bjo": "bây giờ",
    "nma": "nhưng mà", "vs": "với", "r": "rồi", "lun": "luôn", "z": "vậy",
    "j": "gì", "ny": "người yêu", "bsi": "bác sĩ", "cmt": "bình luận",
    "tym": "tim", "sori": "xin lỗi", "qtam": "quan tâm", "bít": "biết",
    "mn": "mọi người", "vk": "vợ", "ck": "chồng", "vc": "vãi", "tui": "tôi",
}

# Từ tiếng Anh hay gãy khi đọc — dịch theo nghĩa phổ biến trong câu; tên riêng
# (Love Story, Ronaldo…) KHÔNG nằm trong bảng này nên được giữ nguyên.
_ENGLISH = {
    "instrumental": "nhạc không lời", "sample": "nhạc mẫu", "replay": "bật lại",
    "intro": "đoạn mở đầu", "flex": "khoe", "lmao": "", "lol": "",
    "omg": "trời ơi",
}


def load_glossary(path=GLOSSARY_FILE) -> dict:
    """Glossary người dùng đã dạy (cặp 'viết tắt/sai' -> 'đúng'), hỏng thì bỏ qua."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k).lower(): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def lint_rows(rows) -> list[str]:
    """Cảnh báo nhanh trên bảng nhịp: nhịp quá dài, viết tắt sót trong glossary."""
    keys = {k for k in (set(_TEENCODE) | set(_ENGLISH) | set(load_glossary())) if len(k) >= 2}
    warnings: list[str] = []
    for r in rows or []:
        if len(r) < 2:
            continue
        spoken = " ".join(str(r[1] or "").split())
        if not spoken:
            continue
        index = r[0]
        words = spoken.split()
        if len(words) > 14:
            warnings.append(f"nhịp {index} quá dài ({len(words)} từ)")
        leftover = sorted({w.strip(".,!?;:…\"'()").lower() for w in words} & keys)
        if leftover:
            warnings.append(f"nhịp {index} còn viết tắt: {', '.join(leftover)}")
    return warnings[:12]
