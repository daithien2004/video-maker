"""Kiểm tra khoảng nghỉ theo dấu câu cuối nhịp."""
import unittest

from videomaker import pipeline as pl


class PauseAfterTests(unittest.TestCase):
    def test_sentence_pause_longer_than_comma_than_none(self):
        sentence = pl._pause_after("Kết thúc bằng chấm.")
        comma = pl._pause_after("mệnh đề giữa,")
        none = pl._pause_after("cắt giữa cụm không dấu")
        self.assertGreater(sentence, comma)
        self.assertGreater(comma, none)
        self.assertEqual(sentence, pl._pause_after("kết bằng hỏi?"))
        self.assertEqual(sentence, pl._pause_after("kết bằng cảm thán!"))

    def test_closing_quotes_do_not_hide_the_punctuation(self):
        self.assertEqual(pl._pause_after('Bảo đảm an toàn."'), pl._pause_after("Bảo đảm an toàn."))
        self.assertEqual(pl._pause_after("“xoa dịu thôi.”"), pl._pause_after("xoa dịu thôi."))

    def test_empty_text_is_zero(self):
        self.assertEqual(pl._pause_after(""), 0.0)
        self.assertEqual(pl._pause_after(None), 0.0)


if __name__ == "__main__":
    unittest.main()
