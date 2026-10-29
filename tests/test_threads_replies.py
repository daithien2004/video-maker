import unittest

from videomaker import comment_manager as cm
from videomaker import threads_replies as tr
from videomaker import threads_shot as ts


def card(code, *, replies=0, parent=None, date=None):
    return dict(id=code, handle=code, text="Content " + code, likes=5, replies=replies,
                url=f"https://www.threads.com/@user/post/{code}", datetime=date,
                parent_id=parent, pagelet="threads_post_page_main")


class NestedReplyTests(unittest.TestCase):
    def test_focus_excludes_ancestors_and_related_cards(self):
        root, parent, reply, related = [card(c) for c in ("ROOT", "P", "R", "OTHER")]
        related["pagelet"] = "related_posts"
        self.assertEqual(tr.focused_replies(parent["url"], [root, parent, reply, related]), [reply])
        self.assertIsNone(tr.focused_replies(parent["url"], [root, reply]))
        parent["pagelet"] = "threads_post_page_1"
        reply["pagelet"] = "threads_post_page_{n}"
        self.assertEqual(tr.focused_replies(parent["url"], [root, parent, reply, related]), [reply])

    def test_recursive_collection_deduplicates_and_keeps_ancestry(self):
        root, parent, reply, grandchild = card("ROOT"), card("P", replies=2), card("R", replies=1), card("G")
        pages = {parent["url"]: [reply, reply], reply["url"]: [parent, grandchild]}
        result, stats = tr.collect([parent], root, lambda url: pages[url], max_depth=2)
        self.assertEqual([r["id"] for r in result], ["P", "R", "G"])
        self.assertEqual([r["parent_id"] for r in result], ["ROOT", "P", "R"])
        self.assertEqual(stats["replies_added"], 2)
        self.assertEqual(stats["pages"], 2)
        self.assertEqual(result[2]["depth"], 3)

    def test_already_selected_reply_not_duplicated(self):
        root, parent, reply = card("ROOT"), card("P", replies=1), card("R")
        result, stats = tr.collect([parent, reply], root, lambda url: [reply])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["parent_id"], "P")
        self.assertEqual(stats["replies_added"], 0)

    def test_parent_context_is_refined_when_deeper_thread_is_opened(self):
        root, parent, reply, correction = card("ROOT"), card("P", replies=2), card("R", replies=1), card("FIX")
        correction["text"] = "1789"
        pages = {parent["url"]: [reply, correction], reply["url"]: [correction]}
        result, stats = tr.collect([parent], root, lambda url: pages[url], max_depth=2)
        fix = next(c for c in result if c["id"] == "FIX")
        self.assertEqual(fix["parent_id"], "R")
        self.assertEqual(fix["text"], "1789")
        self.assertEqual(fix["depth"], 3)

    def test_depth_page_and_reply_limits(self):
        root, parent, reply = card("ROOT"), card("P", replies=2), card("R", replies=2)
        result, stats = tr.collect([parent], root, lambda url: [reply], max_depth=1)
        self.assertEqual(len(result), 2)
        self.assertTrue(stats["depth_limit"])
        result, stats = tr.collect([parent], root, lambda url: self.fail("unexpected request"), max_pages=0)
        self.assertTrue(stats["limited"])
        result, stats = tr.collect([parent], root, lambda url: [reply, card("R2")], max_replies=1)
        self.assertEqual(stats["replies_added"], 1)
        self.assertTrue(stats["limited"])

    def test_failures_and_bad_urls_are_reported_without_losing_roots(self):
        parent, root = card("P", replies=1), card("ROOT")
        result, stats = tr.collect([parent], root, lambda url: None)
        self.assertEqual(len(result), 1)
        self.assertEqual(stats["failures"], 1)
        parent["url"] = "https://attacker.example/post/P"
        result, stats = tr.collect([parent], root, lambda url: self.fail("unsafe URL followed"))
        self.assertEqual(stats["skipped_no_url"], 1)
        self.assertEqual(stats["pages"], 0)

    def test_expansion_never_matches_composer_or_send_controls(self):
        for label in ("View 3 replies", "See replies", "Xem 2 câu trả lời", "Xem thêm phản hồi"):
            self.assertRegex(label, tr.EXPAND_REPLIES)
        for label in ("Reply", "Trả lời", "Send", "Gửi", "Like", "View profile"):
            self.assertNotRegex(label, tr.EXPAND_REPLIES)

    def test_chronological_keeps_parent_before_reply_even_newest_first(self):
        parent = card("P", date=None)
        child = card("R", parent="P", date="2026-10-27T03:00:00Z")
        other = card("OTHER", date="2026-10-27T04:00:00Z")
        ordered = cm.chronological([child, other, parent], newest=True)
        self.assertEqual([c["id"] for c in ordered], ["OTHER", "P", "R"])

    def test_short_reply_emoji_and_source_link_are_not_filtered(self):
        root, parent = card("ROOT"), card("P", replies=3)
        replies = [dict(card("R1"), text="chuẩn"), dict(card("R2"), text="😂"),
                   dict(card("R3"), text="Nguồn: https://example.com/reference")]
        result, stats = tr.collect([parent], root, lambda url: replies)
        self.assertEqual([c["text"] for c in result[1:]], [r["text"] for r in replies])
        self.assertEqual(stats["replies_added"], 3)
        for reply in replies:
            self.assertFalse(ts.is_junk(reply["text"]))
        raw = dict(handle="a", spans=["😂"], btns=[], datetime=None, postHref="/@a/post/A")
        self.assertEqual(ts.card_from_raw(raw)["text"], "😂")
        raw.update(body_spans=["1789"], spans=["a", "1789", "18"], btns=["18"])
        self.assertEqual(ts.card_from_raw(raw)["text"], "1789")


if __name__ == "__main__":
    unittest.main()
