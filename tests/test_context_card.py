"""Kiểm tra khung ngữ cảnh cha ghép trên ảnh reply lúc dựng video."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from videomaker import threads_shot as ts


def _reply_image(path: Path, w: int = 1080, h: int = 400) -> Path:
    img = Image.new("RGB", (w, h), (255, 255, 255))
    ImageDraw.Draw(img).rectangle([0, 0, w - 1, h - 1], outline=(200, 200, 200))
    img.save(path)
    return path


class ContextCardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def test_parse_context_splits_handle_and_snippet(self):
        self.assertEqual(ts.parse_context("@cha: hai dòng trích"), ("cha", "hai dòng trích"))
        self.assertEqual(ts.parse_context("@cha"), ("cha", ""))
        self.assertEqual(ts.parse_context("chỉ trích đoạn không có tên"), ("", "chỉ trích đoạn không có tên"))
        self.assertEqual(ts.parse_context("  "), ("", ""))

    def test_context_card_stacks_card_above_reply_and_fits_max_height(self):
        reply = _reply_image(self.dir / "reply.png", h=400)
        out = self.dir / "out.png"
        result = ts.context_card(reply, "@cha: dòng đang được trả lời", out, max_h=640)
        self.assertEqual(result, out)
        with Image.open(out) as im:
            w, h = im.size
            self.assertEqual(w, 1080)
            self.assertLessEqual(h, 640)
            self.assertGreater(h, 400)          # có thêm khung ngữ cảnh phía trên
            # nền khung ngữ cảnh (xám nhạt, thụt lề trái 72px) nằm trên ảnh reply (trắng viền xám)
            self.assertEqual(im.getpixel((200, 10)), (241, 243, 245))
            self.assertEqual(im.getpixel((10, 10)), (255, 255, 255))   # vùng thụt lề còn nền trắng
            self.assertEqual(im.getpixel((540, h - 5)), (255, 255, 255))  # đáy vẫn là ảnh reply

    def test_tall_reply_is_shrunk_to_keep_whole_cluster_in_frame(self):
        reply = _reply_image(self.dir / "tall.png", h=700)
        out = self.dir / "tall_out.png"
        ts.context_card(reply, "@cha: trích", out, max_h=640)
        with Image.open(out) as im:
            self.assertLessEqual(im.size[1], 640)

    def test_empty_context_returns_original_clip(self):
        reply = _reply_image(self.dir / "keep.png")
        self.assertEqual(ts.context_card(reply, "   ", self.dir / "none.png"), reply)

    def test_handle_only_context_draws_nothing_name_is_never_shown(self):
        reply = _reply_image(self.dir / "anon.png")
        # chỉ có '@tên' không có trích -> không ghép; tên không bao giờ được vẽ vào khung
        self.assertEqual(ts.context_card(reply, "@cha", self.dir / "anon_out.png"), reply)
        out = self.dir / "snippet_only.png"
        ts.context_card(reply, "@cha: trích đoạn cha", out, max_h=640)
        with Image.open(out) as im:
            self.assertLess(im.size[1], 640)   # khung thấp hơn vì không còn dòng tên

    def test_editable_script_marks_reply_with_its_parent(self):
        result = dict(
            post=dict(handle="author", text="Post", image="post/main.png"),
            comments=[dict(handle="cha", text="Comment cha", image="post/cha.png", likes=9,
                           depth=1),
                      dict(handle="con", text="Reply con", image="post/con.png", likes=3,
                           depth=2, parent_id="cha-id", parent_handle="cha")],
            tag="post")
        script = ts.build_editable_script(result)
        self.assertIn("# post/cha.png   (comment 1 · @cha · 9 like)", script)
        self.assertIn("# post/con.png   (reply · ↳ @cha · @con · 3 like)", script)


if __name__ == "__main__":
    unittest.main()
