"""Tên riêng khai trong ten-rieng.txt phải đứng thành một cụm chữ riêng."""
import unittest

from videomaker import pipeline as pl


class CaptionNameTests(unittest.TestCase):
    @staticmethod
    def _chunks(display, names):
        items = pl.parse_emph(display)
        return [" ".join(w for w, _ in c)
                for c in pl.split_items(items, 4, pl._name_spans(items, names))]

    def test_name_gets_its_own_chunk(self):
        self.assertEqual(self._chunks("VIÊN ĐÁ CULLINAN NẶNG 621 GRAM", ("CULLINAN",)),
                         ["VIÊN ĐÁ", "CULLINAN", "NẶNG 621 GRAM"])

    def test_multiword_name_is_never_split(self):
        self.assertEqual(self._chunks("ĐẦU 1908 ABRAHAM ASSCHER MANG NÓ VỀ", ("ABRAHAM ASSCHER",)),
                         ["ĐẦU 1908", "ABRAHAM ASSCHER", "MANG NÓ VỀ"])

    def test_name_after_preposition_stays_with_it(self):
        # Tách tên khỏi "ở" sẽ bỏ giới từ đứng một mình, nên giữ nguyên cụm.
        self.assertEqual(self._chunks("TÌM THẤY NĂM 1905 Ở NAM PHI", ("NAM PHI",)),
                         ["TÌM THẤY NĂM 1905", "Ở NAM PHI"])

    def test_unknown_name_leaves_chunks_unchanged(self):
        plain = self._chunks("VIÊN ĐÁ CULLINAN NẶNG 621 GRAM", ())
        self.assertEqual(self._chunks("VIÊN ĐÁ CULLINAN NẶNG 621 GRAM", ("KHÔNG CÓ",)), plain)

    def test_adjacent_names_are_separated(self):
        self.assertEqual(self._chunks("THỦ HIẾN TRANSVAAL LOUIS BOTHA ĐỀ NGHỊ",
                                      ("TRANSVAAL", "LOUIS BOTHA")),
                         ["THỦ HIẾN", "TRANSVAAL", "LOUIS BOTHA", "ĐỀ NGHỊ"])

    def test_sentence_initial_connector_does_not_swallow_name(self):
        # "Nhưng" mở câu đứng riêng một cụm, tên theo sau vẫn tách khỏi nó.
        self.assertEqual(
            self._chunks("NHÀ VUA TỪ CHỐI. NHƯNG WINSTON CHURCHILL THUYẾT PHỤC ÔNG NHẬN",
                         ("WINSTON CHURCHILL",)),
            ["NHÀ VUA TỪ CHỐI.", "NHƯNG", "WINSTON CHURCHILL", "THUYẾT PHỤC ÔNG NHẬN"])

    def test_connector_inside_sentence_keeps_name_attached(self):
        # Giữa câu "nhưng" vẫn là từ nối phải dính cụm, chỉ mở câu mới đứng riêng.
        self.assertEqual(self._chunks("ÔNG TỪ CHỐI NHƯNG WINSTON CHURCHILL THUYẾT PHỤC",
                                      ("WINSTON CHURCHILL",)),
                         ["ÔNG TỪ CHỐI", "NHƯNG WINSTON CHURCHILL", "THUYẾT PHỤC"])


if __name__ == "__main__":
    unittest.main()
