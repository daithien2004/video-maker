"""Sợi dây nối giữa card đang đọc và card kế tiếp đang chờ phía dưới.

Card kế tiếp hiện ra mờ dần ở dưới card hiện tại, nối bằng một đường dọc mảnh kiểu
thread của Threads; khi sang mục nó trượt lên thay card cũ.
"""
from __future__ import annotations

from pathlib import Path


def connector(width: int, height: int, out: Path) -> Path:
    """Ảnh trong suốt `width` × `height`: đường dọc giữa khung, chấm tròn ở đáy."""
    from PIL import Image, ImageDraw

    s = 2                                   # vẽ gấp đôi rồi hạ mẫu -> mép mượt
    img = Image.new("RGBA", (width * s, height * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = width * s / 2
    lw = 3 * s
    r = 7 * s
    bottom = height * s
    # Viền tối mảnh phía sau để sợi dây còn thấy trên nền sáng.
    d.rounded_rectangle([cx - lw / 2 - s, -lw, cx + lw / 2 + s, bottom - r],
                        radius=lw, fill=(0, 0, 0, 70))
    d.rounded_rectangle([cx - lw / 2, -lw, cx + lw / 2, bottom - r],
                        radius=lw / 2, fill=(255, 255, 255, 150))
    d.ellipse([cx - r - s, bottom - 2 * r - s, cx + r + s, bottom],
              fill=(0, 0, 0, 70))
    d.ellipse([cx - r, bottom - 2 * r, cx + r, bottom], fill=(255, 255, 255, 190))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((width, height), Image.LANCZOS).save(out)
    return out