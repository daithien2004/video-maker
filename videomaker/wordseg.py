"""Nhận biết từ ghép tiếng Việt để bộ chia cụm không cắt giữa cụm từ.

Hai bộ tách từ (underthesea, pyvi) mỗi bộ sai một kiểu: underthesea gộp cả cụm
("hộp thường", "ba người"), pyvi bỏ sót từ ghép ("đánh lạc hướng"). Chỉ tin cặp
mà **cả hai** cùng ghép: hợp của hai bộ chặn oan nhiều hơn hẳn (269 so với 217
cặp trên 13 kịch bản) mà không bớt được cụm cắt hỏng nào. File `tu-ghep.txt` ghi
đè cho những chỗ cả hai cùng sai.

Thiếu thư viện (máy chưa cài) thì chỉ còn file ghi đè — pipeline vẫn chạy.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from .paths import APP_DIR

GLOBAL_OVERRIDE = APP_DIR / "assets" / "tu-ghep.txt"
CONTENT_DIR = APP_DIR / "assets" / "illus"


def normalize(word: str) -> str:
    return re.sub(r"[^\w]", "", word or "").lower()


def _token_pairs(tokens: list[str]) -> tuple[list[str], set[tuple[str, str]]]:
    """Từ đã tách (theo thứ tự) và các cặp nằm chung một token ghép."""
    parts: list[str] = []
    pairs: set[tuple[str, str]] = set()
    for token in tokens:
        words = [normalize(w) for w in token.split("_")]
        words = [w for w in words if w]
        if not words:
            continue
        for a, b in zip(words, words[1:]):
            pairs.add((a, b))
        parts.extend(words)
    return parts, pairs


def _pyvi_pairs(words: list[str], joined: str) -> set[tuple[str, str]]:
    try:
        from pyvi import ViTokenizer
    except Exception:
        return set()
    parts, pairs = _token_pairs(ViTokenizer.tokenize(joined).split())
    return pairs if parts == words else set()


def _underthesea_pairs(words: list[str], joined: str) -> set[tuple[str, str]]:
    try:
        from underthesea import word_tokenize
    except Exception:
        return set()
    parts, pairs = _token_pairs(word_tokenize(joined, format="text").split())
    return pairs if parts == words else set()


def _override_pairs(content: str) -> frozenset[tuple[str, str]]:
    files = [GLOBAL_OVERRIDE]
    if content:
        files.append(CONTENT_DIR / content / "tu-ghep.txt")
    pairs: set[tuple[str, str]] = set()
    for path in files:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            words = [normalize(w) for w in line.split()]
            words = [w for w in words if w]
            pairs.update(zip(words, words[1:]))
    return frozenset(pairs)


@lru_cache(maxsize=8192)
def compound_pairs(words: tuple[str, ...], content: str = "") -> frozenset[tuple[str, str]]:
    """Các cặp từ liền nhau thuộc cùng một từ ghép (cả hai bộ cùng ghép)."""
    clean = [normalize(w) for w in words]
    clean = [w for w in clean if w]
    if len(clean) < 2:
        return _override_pairs(content)
    joined = " ".join(clean)
    pairs = _override_pairs(content)
    pairs |= _pyvi_pairs(clean, joined) & _underthesea_pairs(clean, joined)
    return frozenset(pairs)


def boundaries(words: list[str], content: str = "",
               skip: set[int] | None = None) -> set[int]:
    """Vị trí i (ranh giới giữa words[i-1] và words[i]) nằm giữa một từ ghép.

    `skip` là các vị trí luật khác đã chặn sẵn (hư từ, số + đơn vị) — bỏ qua để
    không phải mang cả bộ tách từ ra soát những chỗ không cần. Từ ghép do người
    viết khai trong `tu-ghep.txt` không bị bỏ qua: đó là chỗ bộ tách từ sai.
    """
    keys = [normalize(w) for w in words]
    if len(keys) < 2:
        return set()
    over = _override_pairs(content)
    pairs = compound_pairs(tuple(keys), content)
    out: set[int] = set()
    for i in range(1, len(keys)):
        a, b = keys[i - 1], keys[i]
        if not a or not b:
            continue
        if (a, b) not in pairs:
            continue
        if (a, b) in over or skip is None or i not in skip:
            out.add(i)
    return out
