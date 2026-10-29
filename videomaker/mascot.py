"""Mascot mở đầu: bảng sprite 3x2 trong assets/mascot, cắt sẵn ra từng biểu cảm.

Mỗi ô là một biểu cảm (nhìn, thắc mắc, giải thích, uống nước, gõ máy, xem điện
thoại). Ảnh cắt sẵn nằm ở assets/mascot/faces/<số>.png và được dùng thẳng khi
dựng video; chỉ cắt lại khi ảnh bảng sprite mới hơn. Nhân vật đã có sẵn viền
trắng trong ảnh gốc.
"""
from __future__ import annotations

from pathlib import Path

from .paths import APP_DIR

MASCOT_DIR = APP_DIR / "assets" / "mascot"
FACES_DIR = MASCOT_DIR / "faces"
COLS, ROWS = 3, 2


def sheet() -> Path | None:
    for p in sorted(MASCOT_DIR.glob("*.png")):
        return p
    return None


def count() -> int:
    return COLS * ROWS


def _canvas(im, aspect: float = 1.45):
    """Đặt nhân vật vào khung chung cùng tỉ lệ để đổi biểu cảm không bị giật ngang.

    Các biểu cảm rộng hẹp khác nhau (có ô có bong bóng "?", "!" bên phải) nên nếu
    canh theo khung bao thì cả người sẽ nhảy sang trái lúc đổi mặt. Ở đây canh theo
    tâm khối tối màu (tóc + áo); bong bóng trắng/xanh vàng không kéo tâm.
    """
    import numpy as np
    from PIL import Image
    a = np.asarray(im)
    dark = (a[:, :, 3] > 128) & (a[:, :, :3].mean(2) < 110)
    cx = float(np.where(dark)[1].mean()) if dark.any() else im.width / 2
    wc = round(im.height * aspect)
    out = Image.new("RGBA", (max(wc, im.width), im.height), (0, 0, 0, 0))
    left = round(wc / 2 - cx)
    left = min(max(left, 0), out.width - im.width)
    out.alpha_composite(im, (left, 0))
    return out


def _splits(al):
    """Tìm đường cắt giữa các ô theo chỗ trống, không cắt đúng lưới 1/3, 1/2.

    Ảnh sprite vẽ tay/AI: đầu nhân vật hàng dưới thò lên quá nửa, tóc ô bên cạnh
    thò sang ô bên này, nên cắt đúng lưới sẽ cụt tóc và dính viền của nhân vật kế
    bên. Mỗi đường cắt dò trong ±80px quanh mốc lưới, chọn giữa khoảng trống nếu có,
    không thì chỗ thưa nhất.
    """
    import numpy as np
    h, w = al.shape
    margin = 80
    ys = (al > 40).sum(1)
    gy = round(h / ROWS)
    lo, hi = max(1, gy - margin), min(h - 1, gy + margin)
    y_cut = lo + int(np.argmin(ys[lo:hi]))
    rows = [0, y_cut, h]
    xs = {}
    for b in range(ROWS):
        cols = (al[rows[b]:rows[b + 1]] > 40).sum(0)
        splits = []
        for c in range(1, COLS):
            bx = round(c * w / COLS)
            lo, hi = max(1, bx - margin), min(w - 1, bx + margin)
            seg = cols[lo:hi]
            zero = np.where(seg == 0)[0]
            splits.append(lo + int(zero[len(zero) // 2]) if len(zero)
                          else lo + int(np.argmin(seg)))
        xs[b] = [0, *splits, w]
    return rows, xs


def _despeckle(cell, min_frac: float = 0.004):
    """Xoá mẩu vụn rời rạc (vệt trắng sót lại khi vẽ bảng sprite) khỏi ảnh cắt.

    Bong bóng "!"/"..." cũng rời khỏi người nhưng to hơn nhiều nên vẫn được giữ;
    chỉ những đảo có diện tích dưới 0.4% đảo lớn nhất mới bị bỏ.
    """
    import numpy as np
    from collections import deque
    from PIL import Image
    a = np.array(cell)
    small = a[::2, ::2, 3] > 40
    hs, ws = small.shape
    seen = np.zeros_like(small)
    groups = []
    for y0 in range(hs):
        for x0 in np.flatnonzero(small[y0] & ~seen[y0]):
            if seen[y0, x0]:
                continue
            queue, pts = deque([(y0, x0)]), []
            seen[y0, x0] = True
            while queue:
                y, x = queue.popleft()
                pts.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < hs and 0 <= nx < ws and small[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            queue.append((ny, nx))
            groups.append(pts)
    if len(groups) < 2:
        return cell
    biggest = max(len(g) for g in groups)
    drop = np.zeros_like(small)
    for g in groups:
        if len(g) < min_frac * biggest:
            for y, x in g:
                drop[y, x] = True
    if not drop.any():
        return cell
    # Nới 1 px ở nửa tỉ lệ để xoá luôn viền khử răng cưa của mẩu vụn.
    grown = drop.copy()
    grown[1:, :] |= drop[:-1, :]
    grown[:-1, :] |= drop[1:, :]
    grown[:, 1:] |= drop[:, :-1]
    grown[:, :-1] |= drop[:, 1:]
    mask = np.repeat(np.repeat(grown, 2, 0), 2, 1)[:a.shape[0], :a.shape[1]]
    pad = np.zeros(a.shape[:2], bool)
    pad[:mask.shape[0], :mask.shape[1]] = mask
    a[:, :, 3][pad] = 0
    return Image.fromarray(a, "RGBA")


def _slice(index: int, im, rows, xs):
    import numpy as np
    row, col = divmod(index % count(), COLS)
    cell = im.crop((xs[row][col], rows[row], xs[row][col + 1], rows[row + 1]))
    cell = _despeckle(cell)
    # getbbox() tính cả alpha = 1 rải rác ở mép ô nên gần như luôn trả về cả ô;
    # cắt theo ngưỡng alpha mới ra đúng thân nhân vật.
    a = np.asarray(cell)[:, :, 3]
    ys, xl = np.where(a > 12)
    if len(xl):
        cell = cell.crop((int(xl.min()), int(ys.min()),
                          int(xl.max()) + 1, int(ys.max()) + 1))
    return _canvas(cell)


def build(force: bool = False) -> list[Path]:
    """Cắt cả bảng sprite ra assets/mascot/faces/ (bỏ qua ô đã cắt và còn mới)."""
    src = sheet()
    if src is None:
        return []
    from PIL import Image
    import numpy as np
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    with Image.open(src) as im:
        full = im.convert("RGBA")
        rows, xs = _splits(np.asarray(full)[:, :, 3])
        for index in range(count()):
            path = FACES_DIR / f"{index}.png"
            if force or not path.exists() or path.stat().st_mtime < src.stat().st_mtime:
                _slice(index, full, rows, xs).save(path)
            paths.append(path)
    return paths


def face(index: int) -> Path | None:
    """Đường dẫn ảnh biểu cảm đã cắt sẵn; thiếu thì cắt lại rồi trả về."""
    src = sheet()
    if src is None:
        return None
    path = FACES_DIR / f"{index % count()}.png"
    if not path.exists() or path.stat().st_mtime < src.stat().st_mtime:
        build()
    return path if path.exists() else None
