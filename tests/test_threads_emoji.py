import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from videomaker.threads_shot import _font, render_card, Run
from videomaker.threads_text import EmojiDraw, prepare_emojis


@unittest.skipUnless(Path('C:/Windows/Fonts/seguiemj.ttf').is_file(), 'Windows emoji font required')
class ThreadsEmojiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = ['😂', '❤️', '👍🏽', '👩‍💻']
        prepare_emojis(cls.tokens)

    def test_compound_emoji_is_measured_as_one_glyph(self):
        draw = EmojiDraw(ImageDraw.Draw(Image.new('RGB', (500, 200))))
        font = _font(52)
        for token in self.tokens:
            self.assertLess(draw.textlength(token, font), 52 * 1.6, token)
            self.assertGreater(draw.textlength(token, font), 20, token)

    def test_card_draws_colored_emoji_with_vietnamese_text(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'card.png'
            render_card({'text': 'Tiếng Việt ' + ' '.join(self.tokens), 'handle': 'test',
                         'likes': 0, 'replies': 0}, target, None, None)
            with Image.open(target) as image:
                body = image.crop((56, 200, 1024, image.height - 140))
                colored = sum(max(pixel) - min(pixel) > 70 for pixel in body.getdata())
                self.assertGreater(colored, 500)
                self.assertEqual(image.width, 1080)

    def test_default_comment_count(self):
        self.assertEqual(Run(url='https://www.threads.com/@test/post/1').top, 20)
