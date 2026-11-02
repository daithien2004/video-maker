"""Mascot: ảnh biểu cảm cắt sẵn phải dùng được kể cả khi không còn bảng sprite."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from videomaker import mascot as ms
from videomaker import pipeline as pl


class MascotFaceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.faces = self.root / "faces"
        self.faces.mkdir()
        for index in (0, 1):
            Image.new("RGBA", (40, 30), (255, 0, 0, 255)).save(self.faces / f"{index}.png")

    def test_hand_edited_faces_work_without_sprite_sheet(self):
        with patch.object(ms, "MASCOT_DIR", self.root), patch.object(ms, "FACES_DIR", self.faces):
            self.assertIsNone(ms.sheet())
            with patch.object(ms, "build") as build:
                self.assertEqual(ms.face(0), self.faces / "0.png")
                self.assertEqual(ms.face(1), self.faces / "1.png")
                build.assert_not_called()
            self.assertIsNone(ms.face(2), "ô chưa có ảnh thì không bịa ra")

    def test_face_is_reshaped_from_a_newer_sheet(self):
        sheet = self.root / "mascot.png"
        Image.new("RGBA", (900, 600), (0, 0, 0, 0)).save(sheet)
        # Mốc thời gian cứng: chỉ dựa vào thứ tự ghi file thì đôi lúc trùng giây.
        os.utime(self.faces / "0.png", (1_000_000_000, 1_000_000_000))
        os.utime(sheet, (1_000_000_100, 1_000_000_100))
        with patch.object(ms, "MASCOT_DIR", self.root), patch.object(ms, "FACES_DIR", self.faces):
            with patch.object(ms, "build") as build:
                ms.face(0)
                build.assert_called_once()


class MascotCenterTests(unittest.TestCase):
    """Mascot phải đứng giữa khung theo mặt/thân nhân vật, không theo mép ảnh."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def _face(self, name: str, left: int, width: int, size=(100, 100)) -> Path:
        im = Image.new("RGBA", size, (0, 0, 0, 0))
        im.paste((0, 0, 0, 255), (left, 0, left + width, size[1]))
        path = self.root / name
        im.save(path)
        return path

    def test_offset_follows_the_character_not_the_canvas(self):
        thick = self._face("left.png", 20, 40)   # thân lệch trái 10px trong khung 100
        x = pl._mascot_x(thick, 100)
        self.assertEqual(x, "(W-w)/2+10.0", "phải đẩy ảnh sang phải bù phần lệch trái")

        thick = self._face("right.png", 40, 40)  # thân lệch phải 10px
        x = pl._mascot_x(thick, 100)
        self.assertEqual(x, "(W-w)/2-10.0")

    def test_offset_scales_with_the_rendered_height(self):
        thick = self._face("half.png", 20, 40)   # lệch 10px trên khung 100 -> scale x2
        self.assertEqual(pl._mascot_x(thick, 200), "(W-w)/2+20.0")

    def test_centered_or_empty_art_stays_put(self):
        centered = self._face("centered.png", 30, 40)
        self.assertEqual(pl._mascot_x(centered, 100), "(W-w)/2+0.0")
        empty = self._face("empty.png", 0, 0)
        self.assertEqual(pl._mascot_x(empty, 100), "(W-w)/2+0.0")

    def test_face_center_wins_over_the_alpha_box(self):
        """Ảnh cắt tay: thân quanh giữa khung nhưng mặt lệch phải -> canh theo mắt."""
        im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        im.paste((0, 0, 0, 255), (20, 60, 80, 100))          # thân: hộp alpha giữa khung
        im.paste((255, 255, 255, 255), (40, 20, 48, 28))     # mắt trái, tâm 43.5
        im.paste((255, 255, 255, 255), (62, 20, 70, 28))     # mắt phải, tâm 65.5
        path = self.root / "eyes.png"
        im.save(path)
        self.assertEqual(pl._mascot_eyes(im), 54.5)
        self.assertEqual(pl._mascot_x(path, 100), "(W-w)/2-4.5")

    def test_big_bright_areas_are_not_eyes(self):
        """Mảng trắng to (nền sáng, bong bóng) không được coi là cặp mắt."""
        im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        im.paste((0, 0, 0, 255), (20, 40, 80, 100))
        im.paste((255, 255, 255, 255), (24, 44, 76, 78))     # mặt sáng to gấp nhiều lần mắt
        path = self.root / "big.png"
        im.save(path)
        self.assertIsNone(pl._mascot_eyes(im))


if __name__ == "__main__":
    unittest.main()
