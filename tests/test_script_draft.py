"""Kiểm tra bảng nhịp: đọc TTS (nhịp quá dài, viết tắt sót), đại từ treo và cổng mềm
giọng kể — chữ văn viết, bình luận cảm xúc, cặp số đối chiếu, cỡ nhịp."""
import unittest

from videomaker import script_draft as sd


class ScriptDraftTests(unittest.TestCase):
    @staticmethod
    def _rows(lengths):
        """Bảng nhịp chỉ khác nhau ở số từ, dùng riêng cho cổng cỡ nhịp.
        Nhịp 1 gắn sẵn hai con số để không kích hoạt cổng cặp số đối chiếu."""
        rows = [[i, " ".join(["bàn"] * n), "CHỮ", "t", "c"] for i, n in enumerate(lengths, 1)]
        if rows and lengths[0] >= 2:
            rows[0][1] = " ".join(["66", "50"] + ["bàn"] * (lengths[0] - 2))
        return rows

    def test_line_without_display_column_is_its_own_caption(self):
        from videomaker import pipeline as pl
        beat = pl.parse_script("[hook] một thành phố xây trên *cọc thép*.")[0]
        self.assertEqual(beat.spoken, "một thành phố xây trên cọc thép.")
        self.assertEqual(beat.display, "MỘT THÀNH PHỐ XÂY TRÊN *CỌC THÉP*.")

    def test_explicit_display_column_is_kept_verbatim(self):
        from videomaker import pipeline as pl
        beat = pl.parse_script("[hook] ngoài khơi Ca-xpi || NGOÀI KHƠI CASPI")[0]
        self.assertEqual(beat.display, "NGOÀI KHƠI CASPI")

    def test_speech_syllables_splits_hyphens_and_expands_numbers(self):
        self.assertEqual(sd.speech_syllables("A-bi Rốc-ke-phe-lơ"), 6)
        self.assertEqual(sd.speech_syllables("năm 1929"), 7)
        self.assertEqual(sd.speech_syllables("gần 2,8 triệu"), 5)

    def test_lint_rows_flags_long_beats_and_leftover_abbrevs(self):
        rows = [[1, "một dòng ngắn bình thường thôi", "-", "", "x", ""],
                [2, " ".join(["từ"] * 26), "-", "", "x", ""],
                [3, "đc chưa k đó", "-", "", "x", ""],
                [4, "Năm 1929, 1935, 1939 và 2023, bảo tàng dời trụ sở, đổi phòng trưng bày.",
                 "-", "", "x", ""]]
        warns = sd.lint_rows(rows)
        self.assertTrue(any("nhịp 2 quá dài" in w for w in warns))
        self.assertTrue(any("nhịp 4 quá dài" in w for w in warns))
        self.assertTrue(any("viết tắt" in w and "đc" in w for w in warns))

    def test_uniform_beat_lengths_are_flagged(self):
        warns = sd.rhythm_warnings(self._rows([8, 8, 9, 8, 8]))
        self.assertTrue(any("nhịp 1–5" in w and "cùng độ dài" in w for w in warns), warns)

    def test_varied_lengths_with_a_punch_beat_pass(self):
        self.assertEqual(sd.rhythm_warnings(self._rows([11, 3, 13, 4, 10, 2])), [])

    def test_no_punch_beat_is_flagged(self):
        warns = sd.rhythm_warnings(self._rows([11, 12, 13, 12]))
        self.assertTrue(any("không nhịp nào ≤6 từ" in w for w in warns), warns)

    def test_written_style_words_are_flagged(self):
        rows = self._rows([8, 8, 8])
        rows[0][1] = "Quân đội Úc được điều đi đối phó với một đàn chim."
        warns = sd.rhythm_warnings(rows)
        self.assertTrue(any("chữ văn viết" in w and "được điều đi" in w for w in warns), warns)

    def test_emotional_commentary_is_flagged(self):
        rows = self._rows([8, 8, 8])
        rows[1][1] = "Đó thật là một chiến thắng kinh ngạc."
        warns = sd.rhythm_warnings(rows)
        self.assertTrue(any("bình luận cảm xúc" in w and "nhịp 2" in w for w in warns), warns)
        self.assertFalse(any(w.count("kinh ngạc") > 1 for w in warns), warns)

    def test_the_word_that_is_a_noun_is_not_flagged(self):
        """"sự thật" là danh từ; chặn từ trần "thật" sẽ báo sai những câu thế này."""
        rows = self._rows([8, 8, 8])
        rows[1][1] = "Hơn 40 năm sau, Nga mới công bố sự thật."
        warns = sd.rhythm_warnings(rows)
        self.assertFalse(any("bình luận cảm xúc" in w for w in warns), warns)

    def test_script_without_a_number_pair_is_flagged(self):
        rows = [[i, " ".join(["bàn"] * n), "CHỮ", "t", "c"]
                for i, n in enumerate([11, 3, 13, 4], 1)]
        warns = sd.rhythm_warnings(rows)
        self.assertTrue(any("hai con số" in w for w in warns), warns)

    def test_beat_with_a_number_pair_passes_that_gate(self):
        warns = sd.rhythm_warnings(self._rows([11, 3, 13, 4]))
        self.assertFalse(any("hai con số" in w for w in warns), warns)

    def test_three_emphasis_spans_in_a_short_beat_are_flagged(self):
        rows = self._rows([8, 8, 8])
        rows[1][2] = "ĐÓ LÀ *VAN GOGH*, VÀ *GAUGUIN* CÙNG *THEO*"
        warns = sd.lint_rows(rows)
        self.assertTrue(any("cụm nhấn mạnh" in w and "nhịp 2" in w for w in warns), warns)

    def test_two_emphasis_spans_in_one_beat_are_allowed(self):
        rows = self._rows([8, 8, 8])
        rows[1][2] = "ĐÓ LÀ *VAN GOGH*, VÀ *GAUGUIN*"
        self.assertFalse(any("cụm nhấn mạnh" in w for w in sd.lint_rows(rows)))

    def test_a_long_beat_may_carry_three_spans(self):
        rows = self._rows([8, sd._LONG_BEAT_SYLLABLES, 8])
        rows[1][2] = "CHIỀU 8 THÁNG 11 *NĂM 1895*, ÔNG LÀM THÍ NGHIỆM TRONG *PHÒNG TỐI* *RỒI TẮT ĐÈN*"
        self.assertFalse(any("cụm nhấn mạnh" in w for w in sd.lint_rows(rows)))

    def test_a_long_beat_still_flags_a_fourth_span(self):
        rows = self._rows([8, sd._LONG_BEAT_SYLLABLES, 8])
        rows[1][2] = "*A* *B* *C* *D*"
        warns = sd.lint_rows(rows)
        self.assertTrue(any("cụm nhấn mạnh" in w for w in warns), warns)

    def test_one_emphasis_span_holding_several_words_is_enough(self):
        rows = self._rows([8, 8, 8])
        rows[1][2] = "ĐÓ LÀ VAN GOGH, VÀ *HAI NGƯỜI BẠN*"
        self.assertFalse(any("cụm nhấn mạnh" in w for w in sd.lint_rows(rows)))

    def test_caption_rows_more_than_one_word_apart_are_flagged(self):
        rows = self._rows([8, 8, 8])
        rows[1][2] = "SÂN BÓNG, CẢ *XƯỞNG NƯỚC CHANH*"
        warns = [w for w in sd.lint_rows(rows) if "hàng trên" in w]
        self.assertEqual(len(warns), 1, warns)
        self.assertIn("nhịp 2", warns[0])

    def test_balanced_or_single_row_caption_passes(self):
        for disp in ("SÂN BÓNG, XƯỞNG *NƯỚC CHANH*", "SÂN BÓNG, *CẢ XƯỞNG NƯỚC CHANH*"):
            rows = self._rows([8, 8, 8])
            rows[1][2] = disp
            self.assertFalse(any("hàng trên" in w for w in sd.lint_rows(rows)), disp)

    def test_date_next_to_a_per_day_rate_is_flagged(self):
        rows = self._rows([8, 8, 8])
        rows[1][1] = "Ngày 7 tháng 11, giếng cho dầu, 100 tấn một ngày."
        self.assertTrue(any("mốc ngày" in w and "nhịp 2" in w for w in sd.lint_rows(rows)))
        rows[1][1] = "Từ 7 tháng 11, giếng chảy đều, 100 tấn một ngày."
        self.assertFalse(any("mốc ngày" in w for w in sd.lint_rows(rows)))

    def test_beat_one_opening_with_a_date_is_flagged(self):
        rows = self._rows([8, 8, 8])
        rows[0][1] = "Năm 1932, quân đội Úc ra tay."
        warns = sd.rhythm_warnings(rows)
        self.assertTrue(any("mốc thời gian" in w for w in warns), warns)
        rows[0][1] = "Quân đội Úc mang súng máy ra đánh một đàn chim."
        self.assertFalse(any("mốc thời gian" in w for w in sd.rhythm_warnings(rows)))

    def test_card_script_skips_rhythm_gate(self):
        rows = [[i, " ".join(["bàn"] * 8), "-", "post", "c"] for i in range(1, 8)]
        self.assertEqual(sd.rhythm_warnings(rows), [])

    def test_pronoun_without_recent_name_is_flagged(self):
        rows = [[1, "Năm 1929, Anna lập ra một bảo tàng", "CHỮ", "t", "c"],
                [2, "Phòng đầu tiên chỉ có tranh đi mượn", "CHỮ", "t", "c"],
                [3, "Khách đến đông hơn dự kiến nhiều lần", "CHỮ", "t", "c"],
                [4, "Nó phải dời đi chỗ khác", "CHỮ", "t", "c"]]
        warns = sd.narrative_warnings(rows)
        self.assertTrue(any("nhịp 4" in w and "nó" in w for w in warns), warns)

    def test_pronoun_near_a_named_beat_passes(self):
        rows = [[1, "Anna quyên góp cho dự án bảo tàng", "CHỮ", "t", "c"],
                [2, "Họ mượn tranh từ các galeri", "CHỮ", "t", "c"],
                [3, "Phòng trưng bày mở đúng hạn", "CHỮ", "t", "c"]]
        self.assertEqual(sd.narrative_warnings(rows), [])

    def test_threads_card_script_skips_narrative_gate(self):
        rows = [[i, f"nhịp thứ {i} kể một dữ kiện", "-", "post", "c"] for i in range(1, 8)]
        self.assertEqual(sd.narrative_warnings(rows), [])


if __name__ == "__main__":
    unittest.main()
