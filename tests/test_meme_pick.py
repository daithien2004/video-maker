"""Kiểm tra chọn meme theo catalog: khớp mô tả, không lặp, vay thẻ láng giềng."""
import unittest
from pathlib import Path

from videomaker import pipeline as pl


class MemePickTests(unittest.TestCase):
    """Chạy trên thư viện thật trong assets/memes (đã có _catalog.json 50 clip)."""

    @classmethod
    def setUpClass(cls):
        cls.lib = pl.scan_memes()
        cls.catalog = pl.load_meme_catalog()

    def test_catalog_matches_library_exactly(self):
        files = {p.relative_to(pl.MEME_DIR).as_posix()
                 for cands in self.lib.values() for p in cands}
        self.assertEqual(files, set(self.catalog), "catalog lệch với thư viện — chạy lại đồng bộ")

    def test_every_catalog_entry_has_description(self):
        empty = [f for f, e in self.catalog.items() if not e["desc"].strip()]
        self.assertEqual(empty, [])

    def test_pick_by_desc_prefers_matching_description(self):
        cands = self.lib.get("hoang", [])
        pick = pl._pick_by_desc(cands, "con cừu hét toáng hoảng loạn", self.catalog, set())
        self.assertIsNotNone(pick)
        self.assertEqual(pick.name, "Screaming Sheep.mp4")
        # không khớp ≥2 từ -> None, để caller bốc ngẫu nhiên trong thẻ
        self.assertIsNone(pl._pick_by_desc(cands, "một câu hoàn toàn không liên quan gì",
                                           self.catalog, set()))

    def test_assign_clips_do_not_repeat_until_pool_exhausted(self):
        n_cuoi = len(self.lib.get("cuoi", []))
        beats = pl.parse_script("\n".join(f"[cuoi] câu cười thứ {i}" for i in range(n_cuoi * 2)))
        pl.assign_clips(beats, seed=7)
        picks = [b.clip for b in beats]
        # n nhịp đầu phải đi đủ n clip khác nhau (chưa lặp khi còn pool)
        self.assertEqual(len(set(picks[:n_cuoi])), n_cuoi)

    def test_neighbor_tag_fills_empty_folder(self):
        beats = pl.parse_script("[ngan] câu bất lực mà tag đã rỗng")
        pl.assign_clips(beats, seed=1)
        self.assertTrue(beats[0].clip, "thẻ rỗng phải vay được clip của thẻ láng giềng")


if __name__ == "__main__":
    unittest.main()
