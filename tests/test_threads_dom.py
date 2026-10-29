"""Chạy extractor thật trên DOM cục bộ; không truy cập Threads."""
import unittest

from playwright.sync_api import sync_playwright

from videomaker import threads_shot as ts


class ExtractionDOMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def extract(self, text):
        page = self.browser.new_page()
        try:
            page.set_content('''<div data-pagelet="threads_post_page_1">
              <div data-pressable-container="true">
                <a href="/@author"><span dir="auto">author</span></a>
                <span dir="auto"><a href="/@author/post/ABC"><time datetime="2026-10-11T23:58:54Z">12/10/2026</time></a></span>
                <span dir="auto">''' + text + '''</span>
                <div role="button"><span dir="auto">18</span></div>
                <div role="button"><span dir="auto">1</span></div>
              </div></div>''')
            raw = page.evaluate(ts.EXTRACT_JS)[0]
            return ts.card_from_raw(raw)
        finally:
            page.close()

    def test_numeric_reply_survives_header_and_counter_removal(self):
        item = self.extract("<span>1789</span>")
        self.assertEqual(item["text"], "1789")
        self.assertEqual(item["datetime"], "2026-10-11T23:58:54Z")
        self.assertEqual(item["likes"], 18)
        self.assertEqual(item["replies"], 1)

    def test_emoji_image_and_short_reply_survive(self):
        self.assertEqual(self.extract('<img alt="😂" src="data:,">')["text"], "😂")
        self.assertEqual(self.extract('chuẩn')["text"], "chuẩn")
        self.assertEqual(self.extract('12/10/2026')["text"], "12/10/2026")

    def test_meta_ai_platform_hint_is_dropped(self):
        # dải "Nhắc đến @meta.ai …" là chữ nền tảng chèn kèm card, không phải lời tác giả
        self.assertIsNone(self.extract(
            "Nhắc đến @meta.ai trong bài viết để nhận câu trả lời ngay tại đây"))
        raw = dict(handle="x", btns=[],
                   spans=["Bài thật",
                          "Nhắc đến @meta.ai trong bài viết để nhận câu trả lời ngay tại đây",
                          "Mention @meta in your post to get a response right here"])
        self.assertEqual(ts.card_from_raw(raw)["text"], "Bài thật")


if __name__ == "__main__":
    unittest.main()
