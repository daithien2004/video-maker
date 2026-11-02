"""Chuyển cảnh card Threads chốt theo loại: comment chính nảy vào, reply trượt từ dưới.

Comment chính (= không có khung ngữ cảnh cha) phải hiện tại chỗ, không có card chờ.
Reply phải có card chờ + dây nối, kể cả khi nhịp đọc rất ngắn ("=))", "tht sự") —
nhịp ngắn từng bị bỏ card chờ nên cùng một reply lúc thì có dây nối, lúc thì trượt
từ đáy khung lên.
"""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from videomaker import pipeline as pl

REPLY = '@cha: trích đoạn comment cha'


class NextCardPlanTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.cards = []
        for index in range(8):
            path = root / f'card{index}.png'
            Image.new('RGB', (1080, 900), (255, 255, 255)).save(path)
            self.cards.append(path)
        self.options = pl.Options(threads=True, meme_w=960, meme_h=640,
                                  threads_max_height=640, threads_zoom=140)

    def spans(self, durations, replies=(), zoom=()):
        spans, clock = [], pl.LEAD
        for index, duration in enumerate(durations):
            spans.append({'start': clock, 'end': clock + duration,
                          'clip': str(self.cards[index]), 'display': '-',
                          'context': REPLY if index in replies else '',
                          'zoom': index in zoom})
            clock += duration + pl.GAP
        return spans

    def test_main_comment_pops_without_waiting_card(self):
        spans = self.spans([2.0, 0.7, 3.0, 2.5])
        plan = pl._next_card_plan(spans, self.options)
        for k in (1, 2, 3):
            with self.subTest(card=k):
                self.assertIsNone(plan[k]['in'], 'comment chính không trượt lên')
                self.assertIsNone(plan[k]['pv'])
                self.assertIsNone(plan[k - 1]['out'], 'card trước đứng yên để card mới nảy')

    def test_reply_slides_from_waiting_card_even_when_short(self):
        spans = self.spans([2.0, 0.7, 0.7, 0.6], replies={1, 2, 3})
        plan = pl._next_card_plan(spans, self.options)
        for k in (1, 2, 3):
            with self.subTest(card=k):
                self.assertIsNotNone(plan[k]['in'], 'reply phải trượt lên')
                self.assertIsNotNone(plan[k]['pv'], f'reply {k} mất card chờ')
                self.assertEqual(plan[k]['in']['y0'], plan[k]['pv']['top'])
                self.assertGreaterEqual(plan[k]['pv']['start'], spans[k - 1]['start'])
                self.assertLess(plan[k]['pv']['start'], spans[k]['start'])
                self.assertGreater(plan[k - 1]['out']['delta'], 0)

    def test_reply_chain_then_new_main_comment(self):
        # post → comment · reply · reply → comment mới → reply của nó
        spans = self.spans([2.0, 3.0, 0.8, 0.7, 2.5, 1.0], replies={2, 3, 5})
        plan = pl._next_card_plan(spans, self.options)
        self.assertIsNone(plan[1]['pv'], 'comment chính nảy vào')
        self.assertIsNotNone(plan[2]['pv'], 'reply đầu tiên trượt từ dưới')
        self.assertIsNotNone(plan[3]['pv'], 'reply thứ hai cũng trượt từ dưới')
        self.assertIsNone(plan[4]['pv'], 'comment chính kế tiếp nảy vào')
        self.assertIsNone(plan[3]['out'], 'card trước comment mới đứng yên')
        self.assertIsNotNone(plan[5]['pv'], 'reply của comment mới trượt từ dưới')

    def test_reply_after_zoom_waits_under_the_zoomed_parent(self):
        # Nhịp zoom (card cha) vào khung rồi reply mới được báo trước bằng card chờ;
        # trước đây card chờ lấy mốc mục k-2 nên reply con hiện trước comment cha.
        spans = self.spans([2.0, 2.0, 0.8, 2.0, 0.6], replies={1, 3}, zoom={2})
        plan = pl._next_card_plan(spans, self.options)
        self.assertIsNone(plan[2]['pv'], 'nhịp zoom không có card chờ riêng')
        after_zoom = plan[3]
        self.assertIsNotNone(after_zoom['pv'])
        self.assertGreaterEqual(after_zoom['pv']['start'], spans[2]['start'],
                               'card chờ không được hiện trước card cha (nhịp zoom)')
        self.assertNotIn('move', after_zoom['pv'], 'card chờ nép dưới card cha, không bị đẩy')
        self.assertEqual(after_zoom['in']['y0'], after_zoom['pv']['top'])

    def test_sound_spans_do_not_add_pop_on_top_of_zoom_sound(self):
        spans = [
            {'start': 0.25, 'clip': 'a', 'sound': False},
            {'start': 2.0, 'clip': 'a', 'sound': False},    # nhịp zoom cùng ảnh -> không pop
            {'start': 3.0, 'clip': 'b', 'sound': True},     # mục ảnh chỉ có [sound] -> không pop
            {'start': 4.6, 'clip': 'c'},
        ]
        self.assertEqual(pl._pop_starts(spans), [0.25, 4.6])
        self.assertEqual(pl._pop_starts(spans, first=False), [4.6])


if __name__ == '__main__':
    unittest.main()
