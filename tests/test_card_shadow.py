import tempfile
import unittest
from pathlib import Path

from PIL import Image

from videomaker.threads_shot import style_card


class CardShadowTests(unittest.TestCase):
    def test_shadow_follows_rounded_card_and_falls_below_it(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.png'
            target = Path(folder) / 'shadow.png'
            Image.new('RGB', (300, 180), 'white').save(source)
            style_card(source, 40, 70, target)
            with Image.open(target) as result:
                pad = (result.width - 300) // 2
                alpha = result.getchannel('A')
                # Shadow extends outside the card, with more weight below it.
                self.assertGreater(alpha.getpixel((pad + 150, pad + 185)), 0)
                self.assertGreater(alpha.getpixel((pad + 150, pad + 185)),
                                   alpha.getpixel((pad + 150, pad - 6)))
                self.assertLess(alpha.getpixel((pad, pad)), 100)
                self.assertEqual(alpha.getpixel((pad + 150, pad + 90)), 255)
                self.assertLessEqual(alpha.getpixel((0, 0)), 1)

    def test_padding_keeps_card_bounds_without_shadow(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.png'
            target = Path(folder) / 'padded.png'
            Image.new('RGB', (300, 180), 'red').save(source)
            style_card(source, 20, 0, target, padding_sides=(10, 20, 30, 40))
            with Image.open(target) as result:
                self.assertEqual(result.size, (300, 180))
                self.assertEqual(result.getpixel((150, 5)), (255, 255, 255, 255))
                self.assertEqual(result.getpixel((150, 80)), (255, 0, 0, 255))

