"""Kiểm tra sắp xếp / bỏ comment và giữ kịch bản đã chỉnh."""
import copy
import unittest

from videomaker import comment_manager as cm
from videomaker import threads_shot as ts


class CommentManagerTests(unittest.TestCase):
    def setUp(self):
        self.result = {
            "post": {"handle": "author", "text": "Original post", "image": "post/main.png"},
            "comments": [{"handle": f"user{i}", "likes": likes,
                          "text": f"Original comment {i}", "image": f"post/c{i}.png"}
                         for i, likes in ((1, 5), (2, 90), (3, 20))],
            "images": [{"rel": f"post/{name}.png", "path": f"/images/{name}.png"}
                       for name in ("main", "c1", "c2", "c3")],
            "stats": {"comments_used": 3, "comments_found": 8}, "tag": "post",
        }
        self.rows = cm.table_rows(self.result)
        self.script = ("# post/main.png (post)\nMy edited post\n\n"
                       "# post/c1.png (comment one)\nEdited first line\nSecond line\n\n"
                       "# post/c2.png\nEdited second comment\n\n"
                       "# post/c3.png\nEdited third comment\n")

    def test_moves_keep_identity_and_delete_marks(self):
        self.rows[1][1] = True
        moved = cm.move_row(self.rows, 2, -1)
        self.assertEqual([r[0] for r in moved], [2, 1, 3])
        self.assertEqual([r[2] for r in moved], [1, 2, 3])
        self.assertTrue(moved[0][1])
        self.assertEqual(cm.move_row(moved, 2, -1), moved)
        self.assertEqual([r[0] for r in cm.move_row(moved, 2, 1)], [1, 2, 3])
        self.assertEqual(self.rows[0][0], 1)

    def test_sort_likes(self):
        self.assertEqual([r[0] for r in cm.sort_likes(self.rows)], [2, 3, 1])

    def test_top_like_selection_then_chronological_order(self):
        pool = [dict(handle='old-low-like', likes=1, datetime='2020-01-01T00:00:00Z'),
                dict(handle='new-high-like', likes=100, datetime='2026-10-27T10:00:00Z'),
                dict(handle='old-high-like', likes=90, datetime='2026-10-27T08:00:00Z')]
        selected = sorted(pool, key=lambda c: -c['likes'])[:2]
        ordered = cm.chronological(selected)
        self.assertEqual([c['handle'] for c in ordered], ['old-high-like', 'new-high-like'])
        self.assertEqual([c['handle'] for c in selected], ['new-high-like', 'old-high-like'])

    def test_time_sort_uses_real_instants_and_keeps_unknowns_last(self):
        self.result['comments'][0]['datetime'] = '2026-10-27T10:00:00+07:00'
        self.result['comments'][1]['datetime'] = '2026-10-27T04:00:00Z'
        self.result['comments'][2]['datetime'] = 'unknown'
        rows = cm.table_rows(self.result)
        rows[1][1] = True
        self.assertEqual([r[0] for r in cm.sort_time(self.result, rows)], [1, 2, 3])
        newest = cm.sort_time(self.result, rows, newest=True)
        self.assertEqual([r[0] for r in newest], [2, 1, 3])
        self.assertTrue(newest[0][1])
        self.assertEqual(rows[1][6], '27/10/2026 11:00')
        self.assertEqual(rows[2][6], '—')

    def test_missing_times_are_stable_and_no_timestamp_is_invented(self):
        rows = cm.move_row(self.rows, 3, -1)
        self.assertEqual(cm.sort_time(self.result, rows), rows)
        self.assertIsNone(cm.comment_time({'datetime': None}))
        self.assertEqual(cm.comment_time({'datetime': '2026-10-27T04:00:00'}),
                         cm.comment_time({'datetime': '2026-10-27T04:00:00Z'}))

    def test_scroll_merge_preserves_known_datetime(self):
        first = dict(handle='a', text='A comment', likes=10, datetime='2026-10-27T01:00:00Z')
        acc = {}
        ts._merge_comment(acc, first)
        ts._merge_comment(acc, dict(first, likes=20, datetime=None))
        item = next(iter(acc.values()))
        self.assertEqual(item['datetime'], first['datetime'])
        self.assertEqual(item['likes'], 20)

    def test_apply_reorders_and_removes_comments_with_matching_images(self):
        original = copy.deepcopy(self.result)
        self.rows[0][2] = 3
        self.rows[2][2] = 1
        self.rows[1][1] = True
        result = cm.apply_draft(self.result, self.rows)
        self.assertEqual([c["handle"] for c in result["comments"]], ["user3", "user1"])
        self.assertEqual([i["rel"] for i in result["images"]],
                         ["post/main.png", "post/c3.png", "post/c1.png"])
        self.assertEqual(result["stats"]["comments_used"], 2)
        self.assertEqual(result["stats"]["comments_found"], 8)
        self.assertEqual(self.result, original)

    def test_script_reorder_preserves_edits_and_removes_only_deleted_section(self):
        script = ts.reorder_script_sections(
            self.script, ["post/main.png", "post/c3.png", "post/c1.png"],
            ts.build_editable_script(self.result), ["post/c2.png"])
        sections = ts.parse_sections(script)
        self.assertEqual([s[0] for s in sections], ["post/main.png", "post/c3.png", "post/c1.png"])
        self.assertEqual(sections[0][1], ["My edited post"])
        self.assertEqual(sections[2][1], ["Edited first line", "Second line"])
        self.assertNotIn("Edited second comment", script)

    def test_missing_sections_fallback_and_extra_manual_sections_survive(self):
        script = "# post/c1.png\nEdited comment\n\n# custom/extra.png\nAdded manually\n"
        reordered = ts.reorder_script_sections(
            script, ["post/main.png", "post/c1.png"], ts.build_editable_script(self.result))
        sections = ts.parse_sections(reordered)
        self.assertEqual([s[0] for s in sections], ["post/main.png", "post/c1.png", "custom/extra.png"])
        self.assertEqual(sections[1][1], ["Edited comment"])
        self.assertEqual(sections[2][1], ["Added manually"])

    def test_all_comments_can_be_removed_but_post_is_retained(self):
        for row in self.rows:
            row[1] = True
        result = cm.apply_draft(self.result, self.rows)
        self.assertEqual(result["comments"], [])
        self.assertEqual(result["images"], self.result["images"][:1])
        self.assertEqual(result["post"], self.result["post"])
        self.assertEqual(cm.apply_draft(result, [])["comments"], [])

    def test_invalid_or_stale_table_is_rejected(self):
        for rows in (self.rows[:2], [self.rows[0], self.rows[0], self.rows[2]],
                     [[0, False, 1, "@fake", 1, "fake"], *self.rows[1:]]):
            with self.assertRaises(ValueError):
                cm.apply_draft(self.result, rows)
        for rank in (0, -1, "bad", float("nan"), float("inf")):
            rows = copy.deepcopy(self.rows)
            rows[0][2] = rank
            with self.assertRaises(ValueError):
                cm.apply_draft(self.result, rows)
        with self.assertRaises(ValueError):
            cm.move_row(self.rows, None, -1)


if __name__ == "__main__":
    unittest.main()
