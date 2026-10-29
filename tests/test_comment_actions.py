"""Kiểm tra nút hành động gắn với ảnh/ID của đúng comment, không dựa vào hàng chọn."""
import tempfile
import unittest
from pathlib import Path

from videomaker import app
from videomaker import comment_manager as cm


class CommentActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.state = dict(
            post=dict(handle="author", text="Post", image="post/main.png"),
            comments=[dict(handle=f"user{i}", text=f"Comment {i}", image=f"post/c{i}.png", likes=i)
                      for i in range(1, 4)],
            images=[dict(rel=f"post/{name}.png", path=str(root / f"{name}.png"))
                    for name in ("main", "c1", "c2", "c3")],
            stats={}, tag="post", json=str(root / "threads.json"), dir=str(root))
        self.rows = cm.table_rows(self.state)
        self.script = "# post/main.png\nEdited post\n" + "".join(
            f"\n# post/c{i}.png\nEdited comment {i}\n" for i in range(1, 4))

    def test_delete_applies_immediately_to_only_that_comment(self):
        result = app.on_threads_comment_action(
            self.state, self.rows, self.script, "post/c2.png", "delete")
        self.assertEqual([c["handle"] for c in result[0]["comments"]], ["user1", "user3"])
        self.assertNotIn("Edited comment 2", result[4])
        self.assertIn("Edited comment 1", result[4])
        self.assertEqual(len(result[2]), 3)  # post + two comments in preview
        self.assertEqual(result[7]["value"], [])
        self.assertIsNone(result[9])  # stale video cleared

    def test_delete_follows_same_comment_after_it_moves(self):
        moved = app.on_threads_comment_action(
            self.state, self.rows, self.script, "post/c2.png", "up")
        self.assertEqual([c["handle"] for c in moved[0]["comments"]], ["user2", "user1", "user3"])
        self.assertIn("Edited comment 2", moved[4])
        deleted = app.on_threads_comment_action(
            moved[0], moved[1]["value"], moved[4], "post/c2.png", "delete")
        self.assertEqual([c["handle"] for c in deleted[0]["comments"]], ["user1", "user3"])

    def test_missing_or_already_deleted_comment_does_not_affect_another(self):
        with self.assertRaises(app.gr.Error):
            app.on_threads_comment_action(
                self.state, self.rows, self.script, "post/missing.png", "delete")
        self.assertEqual(len(self.state["comments"]), 3)


if __name__ == "__main__":
    unittest.main()
