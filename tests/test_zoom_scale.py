"""Nhịp chỉ có ảnh: phóng ngay từ cỡ thường, vọt quá cỡ rồi trở lại (nảy)."""
import io
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from videomaker import pipeline as pl


def _eval(expr: str, t: float) -> float:
    """Chạy thẳng biểu thức FFmpeg (cú pháp số học giống Python)."""
    return eval(expr, {"__builtins__": {}}, {"t": t, "min": min, "max": max, "pow": pow})


class ZoomScaleTests(unittest.TestCase):
    def test_no_zoom_is_identity(self):
        self.assertEqual(pl._zoom_scale(1.0), "1")

    def test_starts_at_normal_size_and_bounces_past_the_zoom_size(self):
        expr = pl._zoom_scale(1.3)
        self.assertIn(f"t/{pl.ZOOM_IN:g}", expr)
        self.assertAlmostEqual(_eval(expr, 0.0), 1 / 1.3, places=3)
        peak = _eval(expr, pl.ZOOM_IN / 2)     # vọt quá cỡ zoom
        self.assertTrue(1.0 < peak < 1.1, peak)
        self.assertAlmostEqual(_eval(expr, pl.ZOOM_IN), 1.0, places=3)
        self.assertAlmostEqual(_eval(expr, 10.0), 1.0, places=3)


class ZoomOriginRenderTests(unittest.TestCase):
    """Card nhịp zoom đứng ở cỡ thường rồi phóng ngay, vọt quá rồi về cỡ zoom."""

    def _render(self, root: Path, image: Path, flag: str) -> Path:
        background = root / 'background.mp4'
        if not background.exists():
            subprocess.run([pl.ffmpeg_path(), '-y', '-loglevel', 'error', '-f', 'lavfi',
                            '-i', 'color=c=black:s=180x320:r=60', '-t', '3',
                            '-c:v', 'libx264', '-preset', 'ultrafast', str(background)], check=True)
        options = pl.Options(backend=pl.BACKEND_DUMMY, gap=0, meme_w=80, meme_h=80, nvenc=False,
                             card_motion=False, bg_motion=False, mascot=False, next_card=False,
                             sfx=False, threads=True, threads_zoom=140, pop_in=True, fps=30)
        with patch.object(pl, 'list_backgrounds', return_value=[background]):
            return pl.render([[1, '[sound]', '-', '', str(image), '', flag]], options, preview=True)

    def _green_width(self, video: Path, t: float) -> int:
        png = subprocess.check_output([pl.ffmpeg_path(), '-v', 'error', '-ss', f'{t:.2f}',
                                       '-i', str(video), '-frames:v', '1', '-f', 'image2pipe',
                                       '-vcodec', 'png', '-'])
        with Image.open(io.BytesIO(png)) as frame:
            a = np.asarray(frame.convert('RGB')).astype(int)
        mask = (a[:, :, 1] > 150) & (a[:, :, 0] < 120)
        cols = np.flatnonzero(mask.any(axis=0))
        return int(cols[-1] - cols[0] + 1) if len(cols) else 0

    def test_zoom_from_normal_size_with_a_bounce(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder)
            for name in ('WORK_DIR', 'OUT_DIR', 'FONT_DIR'):
                directory = root / name
                directory.mkdir()
                stack.enter_context(patch.object(pl, name, directory))
            stack.enter_context(patch.object(pl, 'W', 180))
            stack.enter_context(patch.object(pl, 'H', 320))
            stack.enter_context(patch.object(pl, 'THREADS_CARD_CENTER', 160))
            stack.enter_context(patch.object(pl, 'beat_audio',
                                             return_value=np.zeros(57600, dtype=np.float32)))
            image = root / 'card.png'
            Image.new('RGB', (80, 80), (0, 255, 0)).save(image)
            plain = self._render(root, image, '')
            # Đo ngay: hai bản preview có thể trùng tên file (tên chỉ tới giây).
            plain_end = self._green_width(plain, 1.00)
            zoomed_video = self._render(root, image, '1')
            start_w = self._green_width(zoomed_video, 0.00)
            peak_w = self._green_width(zoomed_video, 0.10)   # lúc vọt quá cỡ
            big_w = self._green_width(zoomed_video, 1.00)
            self.assertGreater(plain_end, 0)
            self.assertAlmostEqual(start_w, plain_end, delta=6)  # khung đầu = cỡ thường
            self.assertTrue(peak_w > big_w > start_w, (start_w, peak_w, big_w))
            self.assertAlmostEqual(big_w / plain_end, 1.4, delta=0.12)


if __name__ == '__main__':
    unittest.main()