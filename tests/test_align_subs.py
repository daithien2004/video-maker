"""Căn mốc phụ đề theo giọng thật: đọc số, ánh xạ từ, và mốc dùng trong ASS."""
import re
import unittest
from dataclasses import replace

from videomaker import pipeline as pl


def _marks(pairs):
    return [{"word": w, "start": s, "end": e, "real": True} for w, s, e in pairs]


def _strip_overrides(line: str) -> str:
    """Bỏ mọi thẻ ASS trong ngoặc {}, chỉ giữ chữ thật sự lên hình."""
    return re.sub(r"\{[^{}]*\}", "", line)


class SayNumberTests(unittest.TestCase):
    def test_reads_numbers_as_words(self):
        self.assertEqual(pl._say_number("11"), "mười một")
        self.assertEqual(pl._say_number("66"), "sáu mươi sáu")
        self.assertEqual(pl._say_number("1929"), "một nghìn chín trăm hai mươi chín")
        self.assertEqual(pl._say_number("1929,"), "một nghìn chín trăm hai mươi chín")
        self.assertEqual(pl._say_number("50%"), "năm mươi phần trăm")
        self.assertEqual(pl._say_number("500.000"), "năm trăm nghìn")
        self.assertEqual(pl._say_number("1.5"), "một phẩy năm")
        self.assertEqual(pl._say_int(105), "một trăm linh năm")
        self.assertEqual(pl._say_int(1005), "một nghìn không trăm linh năm")
        self.assertEqual(pl._say_int(21), "hai mươi mốt")
        self.assertEqual(pl._say_int(25), "hai mươi lăm")

    def test_expanded_words_keep_pointing_at_the_written_token(self):
        said = pl._said_words(["Tháng", "11", "năm", "1929."])
        self.assertEqual([i for _, i in said], [0, 1, 1, 2, 3, 3, 3, 3, 3, 3, 3])


class AlignGateTests(unittest.TestCase):
    def test_missing_model_is_not_an_error_just_no_marks(self):
        old = pl._ALIGN_MODEL
        pl._ALIGN_MODEL = None
        try:
            def boom():
                raise ImportError("no torch")
            pl._ALIGN_MODEL = old
            real_load = pl._align_load
            pl._align_load = boom
            try:
                self.assertIsNone(pl._align_words(None, "hai từ lời đọc"))
            finally:
                pl._align_load = real_load
        finally:
            pl._ALIGN_MODEL = old


class BuildAssMarkTests(unittest.TestCase):
    def _row(self, align):
        return {
            "idx": 1, "start": 10.0, "dur": 2.0, "text_end": 12.0, "vis_end": 12.0,
            "spoken": "một hai ba bốn", "display": "MỘT HAI BA BỐN", "pauses": [],
            "align": align, "tag": "", "clip": None, "context": None, "threads": False,
        }

    def _starts(self, align, opt=None):
        opt = opt or replace(pl.Options(), max_words=2, karaoke=False, upper=False)
        text = pl.build_ass([self._row(align)], opt)
        out = []
        for line in text.splitlines():
            if line.startswith("Dialogue:"):
                out.append(line.split(",", 3)[1])
        return out

    def test_chunk_boundaries_come_from_the_real_marks(self):
        marks = _marks([("một", 0.0, 0.3), ("hai", 0.3, 0.6), ("ba", 1.4, 1.7), ("bốn", 1.7, 2.0)])
        self.assertEqual(self._starts(marks), ["0:00:10.00", "0:00:11.40"])

    def test_without_marks_the_old_estimate_still_runs(self):
        self.assertEqual(self._starts(None), ["0:00:10.00", "0:00:11.00"])

    def test_marks_for_a_different_word_count_are_ignored(self):
        marks = _marks([("một", 0.0, 0.3), ("hai", 0.3, 0.6)])
        self.assertEqual(self._starts(marks), ["0:00:10.00", "0:00:11.00"])


class TierLineTests(unittest.TestCase):
    """Video thường: cụm cắt tại từ *nhấn mạnh* — hàng trên chữ thường, hàng dưới chữ to."""

    def _text(self, display, karaoke=False, max_words=4, **over):
        opt = replace(pl.Options(), upper=False, pop=False, max_words=max_words,
                      karaoke=karaoke, **over)
        row = {"idx": 1, "start": 0.0, "dur": 2.0, "text_end": 2.0, "vis_end": 2.0,
               "spoken": "một hai ba", "display": display, "pauses": [], "align": None,
               "tag": "", "clip": None, "context": None, "threads": False}
        return [_strip_overrides(ln.split(",", 9)[9])
                for ln in pl.build_ass([row], opt).splitlines() if ln.startswith("Dialogue:")]

    def _ys(self, display, max_words=4, **over):
        opt = replace(pl.Options(), upper=False, pop=False, max_words=max_words,
                      karaoke=False, **over)
        row = {"idx": 1, "start": 0.0, "dur": 2.0, "text_end": 2.0, "vis_end": 2.0,
               "spoken": "một hai ba bon nam sau", "display": display, "pauses": [],
               "align": None, "tag": "", "clip": None, "context": None, "threads": False}
        return [int(m.group(1)) for ln in self._raw_lines(row, opt)
                for m in [re.search(r"\\pos\(\d+,(\d+)\)", ln)] if m]

    @staticmethod
    def _raw_lines(row, opt):
        return [ln for ln in pl.build_ass([row], opt).splitlines() if ln.startswith("Dialogue:")]

    def test_emphasis_starts_the_lower_line_and_keeps_word_order(self):
        self.assertEqual(self._text("NHO MOT *TO* NHO"), ["NHO MOT", "TO NHO"])

    def test_a_cluster_without_emphasis_stays_on_one_line(self):
        self.assertEqual(self._text("NHO NHO"), ["NHO NHO"])

    def test_a_fully_emphasized_cluster_is_one_big_line(self):
        self.assertEqual(self._text("*TO TO*"), ["TO TO"])

    def test_karaoke_shows_the_same_words_in_the_same_order(self):
        self.assertEqual(self._text("NHO MOT *TO* NHO", karaoke=True), ["NHO MOT", "TO NHO"])

    def test_bottom_row_sits_on_text_y_and_the_block_grows_upward(self):
        """Hàng đáy luôn ở text_y như bản 1 hàng; hàng nhỏ xếp lên trên theo tier_gap_scale."""
        self.assertEqual(self._ys("NHO MOT *TO* NHO", text_y=880, tier_gap_scale=1.0), [736, 880])
        self.assertEqual(self._ys("NHO MOT *TO* NHO", text_y=880, tier_gap_scale=0.8), [765, 880])
        self.assertEqual(self._ys("NHO NHO", text_y=880), [880])

    def test_a_cluster_too_long_still_lands_on_two_rows(self):
        """Cụm dài được co chữ để mỗi bậc nằm gọn một hàng: hàng luôn là 1 dòng."""
        self.assertEqual(len(self._text("nho " * 12, max_words=16)), 1)

    def _raw(self, display):
        opt = replace(pl.Options(), upper=False, pop=False, max_words=4, karaoke=False)
        row = {"idx": 1, "start": 0.0, "dur": 2.0, "text_end": 2.0, "vis_end": 2.0,
               "spoken": "một hai ba bon", "display": display, "pauses": [], "align": None,
               "tag": "", "clip": None, "context": None, "threads": False}
        return next(ln for ln in pl.build_ass([row], opt).splitlines()
                    if ln.startswith("Dialogue:"))

    def test_space_between_two_tiers_always_takes_the_larger_size(self):
        self.assertEqual(pl._tier_space(120, 168), r"{\fs168} ")
        self.assertEqual(pl._tier_space(168, 120), " ")
        self.assertEqual(pl._tier_space(120, 120), " ")

    def test_a_mixed_line_lifts_only_at_the_small_to_big_junction(self):
        lifts = len(re.findall(r"\{\\fs\d+\} ", self._raw("*TO* NHO *TO*")))
        self.assertEqual(lifts, 1)

    def test_layout_measures_emphasized_words_at_their_real_size(self):
        opt = replace(pl.Options(), max_words=9)
        avail = pl.W - 240 - 2 * opt.outline_w
        big = pl._tier_size(opt, True)
        n = 2
        while True:
            flat = (sum(pl._text_width("nho", opt.font_size, opt.font) for _ in range(n))
                    + (n - 1) * pl._text_width(" ", opt.font_size, opt.font))
            wide = (sum(pl._text_width("nho", big, opt.font) for _ in range(n))
                    + (n - 1) * pl._tier_space_width(big, big, opt.font))
            if flat <= avail < wide or n > 60:
                break
            n += 1
        self.assertLessEqual(flat, avail, "không tìm được cụm biên để đo")
        self.assertEqual(len(pl.layout_lines([("nho", False)] * n, opt)), 1)
        self.assertGreater(len(pl.layout_lines([("nho", True)] * n, opt)), 1)


if __name__ == "__main__":
    unittest.main()
