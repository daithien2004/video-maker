import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videomaker import pipeline as pl


class PronounceTest(unittest.TestCase):
    def _with_file(self, content: str):
        f = Path(tempfile.mkdtemp()) / "phat-am.txt"
        f.write_text(content, encoding="utf-8")
        return mock.patch.object(pl, "PRONOUNCE_FILE", f)

    def test_replaces_whole_word_case_insensitive(self):
        with self._with_file("# ghi chú\nSchabowski = Sa-bốp-xki\n"):
            self.assertEqual(pl._pronounce("phát ngôn viên Schabowski nói"),
                             "phát ngôn viên Sa-bốp-xki nói")
            self.assertEqual(pl._pronounce("schabowski."), "Sa-bốp-xki.")

    def test_keeps_word_count(self):
        with self._with_file("Schabowski = Sa-bốp-xki\n"):
            text = "ông Schabowski đáp"
            self.assertEqual(len(pl._pronounce(text).split()), len(text.split()))

    def test_missing_file_changes_nothing(self):
        with mock.patch.object(pl, "PRONOUNCE_FILE", Path("khong-ton-tai.txt")):
            self.assertEqual(pl._pronounce("Schabowski"), "Schabowski")


class SentenceSplitTest(unittest.TestCase):
    def test_voice_date_numbers_not_split_by_dot(self):
        import re
        parts = re.split(r"(?<=[.!?…])\s+", "Có 20.000 người. Họ đi.")
        self.assertEqual(parts, ["Có 20.000 người.", "Họ đi."])


if __name__ == "__main__":
    unittest.main()
