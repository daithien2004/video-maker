import tempfile
import unittest
from pathlib import Path

from videomaker import app
from videomaker import threads_editorial as editorial
from videomaker import threads_shot as ts


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = dict(
            post=dict(id="ROOT", image="post/main.png", text="Original post", handle="author"),
            comments=[dict(id="P", image="post/parent.png", text="Parent", handle="p", depth=1,
                           parent_id="ROOT"),
                      dict(id="R", image="post/reply.png", text="Reply", handle="r", depth=2,
                           parent_id="P")],
            images=[dict(rel=f"post/{name}.png", path=str(root / f"{name}.png"))
                    for name in ("main", "parent", "reply")],
            stats={}, tag="post", dir=str(root), json=str(root / "threads.json"))
        for image in self.source["images"]:
            Path(image["path"]).write_bytes(b"image")
        self.text = ("# post/main.png\nA source-based introduction || *INTRO*\n"
                     "# post/parent.png\nAn edited parent statement || KEYWORD\n"
                     "# post/reply.png\nAn edited reply with context || -\n")

    def test_valid_script_keeps_subtitle_and_no_sub_marker(self):
        report = editorial.validate_script(self.source, self.text)
        self.assertEqual(report["comments"], 2)
        self.assertEqual(report["hidden_subtitle_beats"], 1)
        self.assertEqual(ts.split_beat(ts.parse_sections(self.text)[2][1][0])[1], "-")

    def test_prepare_groups_short_reply_with_its_parent_without_filtering(self):
        self.source["comments"][1]["text"] = "😂"
        package = editorial.prepare(self.source)
        self.assertEqual(package["comments"][1]["text"], "😂")
        self.assertEqual(package["conversations"], [dict(root_image="post/parent.png",
            images=["post/parent.png", "post/reply.png"], context_complete=True)])
        self.source["comments"][1]["parent_id"] = "MISSING"
        missing = editorial.conversation_groups(self.source)
        self.assertTrue(any(not group["context_complete"] for group in missing))

    def test_invalid_source_reference_or_missing_parent_rejected(self):
        cases = [self.text.replace("post/parent.png", "post/unknown.png"),
                 self.text.replace("# post/parent.png\nAn edited parent statement || KEYWORD\n", ""),
                 self.text.replace("An edited reply with context || -", "No separator"),
                 self.text + "# post/main.png\nRepeated || REPEATED\n"]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                editorial.validate_script(self.source, text)

    def test_empty_section_becomes_sound_beat(self):
        text = self.text.replace("A source-based introduction || *INTRO*", "")
        report = editorial.validate_script(self.source, text)
        self.assertEqual(report["images"], ["post/main.png", "post/parent.png", "post/reply.png"])
        self.assertEqual(ts.parse_sections(text)[0][1], ["[sound] || -"])


    def test_no_sub_survives_conversion_and_reorder(self):
        from unittest.mock import patch
        with patch.object(app.pl, "resolve_clip", return_value=Path(self.temp.name)), \
             patch.object(app.pl, "assign_clips", side_effect=lambda *a, **k: None):
            rows, *_ = app.on_threads_build(self.text, self.source)[1:]
        self.assertEqual(rows[-1][2], "-")
        reordered = ts.reorder_script_sections(self.text,
            ["post/main.png", "post/parent.png", "post/reply.png"], ts.build_editable_script(self.source))
        self.assertIn("An edited reply with context || -", reordered)


if __name__ == "__main__":
    unittest.main()
