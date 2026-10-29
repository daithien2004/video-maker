"""Kiểm tra cảnh báo TTS trên bảng nhịp: nhịp quá dài + viết tắt còn sót."""
import unittest

from videomaker import script_draft as sd


class ScriptDraftTests(unittest.TestCase):
    def test_lint_rows_flags_long_beats_and_leftover_abbrevs(self):
        rows = [[1, "một dòng ngắn bình thường thôi", "-", "", "x", ""],
                [2, " ".join(["từ"] * 16), "-", "", "x", ""],
                [3, "đc chưa k đó", "-", "", "x", ""]]
        warns = sd.lint_rows(rows)
        self.assertTrue(any("quá dài" in w and "2" in w for w in warns))
        self.assertTrue(any("viết tắt" in w and "đc" in w for w in warns))


if __name__ == "__main__":
    unittest.main()
