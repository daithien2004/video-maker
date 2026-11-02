"""Bảng nháp hẹn giờ phải hiện đúng khối hashtag chung sẽ đăng."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videomaker import app


class FbBatchTagsTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.video = Path(folder.name) / "video_a.mp4"
        self.video.write_bytes(b"x")

    def _rows(self, current=(), shared=None, tags="#test"):
        with patch.object(app, "_fb_caption_for", return_value=("Thân bài", "nguồn")):
            return app.on_fb_edit_rows([str(self.video)], "2/ngày", list(current),
                                       shared=shared, tags=tags)["value"]

    def test_draft_caption_includes_shared_hashtags(self):
        rows = self._rows()
        self.assertEqual(len(rows[0]), 3)
        self.assertTrue(rows[0][2].endswith("#fyp #xuhuong #funny #test"))

    def test_shared_caption_also_gets_the_tags(self):
        rows = self._rows(shared="Caption chung viết tay")
        self.assertEqual(rows[0][2], "Caption chung viết tay\n\n#fyp #xuhuong #funny #test")

    def test_rebuilding_rows_does_not_duplicate_tags(self):
        once = self._rows()
        again = self._rows(current=once)
        self.assertEqual(again[0][2], once[0][2])

    def test_empty_caption_is_not_only_tags(self):
        with patch.object(app, "_fb_caption_for", return_value=("", "—")):
            rows = app.on_fb_edit_rows([str(self.video)], "2/ngày", [], tags="#test")["value"]
        self.assertEqual(rows[0][2], "")


if __name__ == "__main__":
    unittest.main()
