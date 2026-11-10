"""Bộ chia cụm: trần 4 từ, không cắt từ ghép, cổng lint báo cụm cắt hỏng."""
import unittest

from videomaker import pipeline as pl, script_draft as sd


def _chunks(display, content=""):
    items = pl.parse_emph(display)
    return [" ".join(w for w, _ in c)
            for c in pl.split_items(items, 4, pl._name_spans(items, ()), content=content)]


def _boundaries(chunks):
    return {(pl._word_key(a.split()[-1]), pl._word_key(b.split()[0]))
            for a, b in zip(chunks, chunks[1:])}


class ChunkSplitTests(unittest.TestCase):
    def test_compound_in_override_is_never_cut(self):
        got = _chunks("TÀU MANG THEO NHIỀU THIẾT BỊ ĐO")
        self.assertNotIn(("thiết", "bị"), _boundaries(got))
        self.assertNotIn(("bị", "đo"), _boundaries(got))

    def test_chunks_never_exceed_four_words(self):
        got = _chunks("MỘT ĐOÀN XE TẢI CHỞ HÀNG ĐI QUA CẦU VÀO BUỔI SÁNG HÔM ĐÓ")
        self.assertEqual(max(len(c.split()) for c in got), 4)
        self.assertEqual(" ".join(got),
                         "MỘT ĐOÀN XE TẢI CHỞ HÀNG ĐI QUA CẦU VÀO BUỔI SÁNG HÔM ĐÓ")

    def test_lint_flags_dangling_function_word(self):
        rows = [[1, "viên thật đi bằng bưu phẩm bảo đảm",
                 "VIÊN THẬT ĐI BẰNG BƯU PHẨM BẢO ĐẢM.", "t", "c", ""]]
        warns = [w for w in sd.lint_rows(rows) if "cụm kết thúc bằng hư từ" in w]
        self.assertTrue(warns)
        self.assertIn("BẰNG", warns[0])

    def test_number_with_counter_may_end_chunk(self):
        got = _chunks("CHỈ CÒN 2.000 NGƯỜI LÀM CA BẢY NGÀY.")
        self.assertIn("CHỈ CÒN 2.000 NGƯỜI", got)
        self.assertFalse([c for c in got if pl._is_glue(c.split()[-1])])

    def test_lint_accepts_clean_sentence(self):
        rows = [[1, "chỉ còn hai nghìn người, làm ca bảy ngày",
                 "CHỈ CÒN HAI NGHÌN NGƯỜI, LÀM CA BẢY NGÀY.", "t", "c", ""]]
        self.assertFalse([w for w in sd.lint_rows(rows) if "cụm" in w])

    def test_determiner_may_end_chunk(self):
        got = _chunks("LẠI MỞ RA VÌ MỘT LỜI NÓI NHẦM.")
        self.assertEqual(got, ["LẠI MỞ RA", "VÌ MỘT", "LỜI NÓI NHẦM."])
        self.assertFalse([c for c in got if pl._is_glue(c.split()[-1])])


if __name__ == "__main__":
    unittest.main()
