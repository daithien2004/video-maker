import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from videomaker import threads_shot as ts


class ThreadsMediaTests(unittest.TestCase):
    def photo(self):
        output = io.BytesIO()
        Image.new('RGB', (200, 100), (10, 90, 220)).save(output, format='PNG')
        return output.getvalue()

    def test_image_only_comment_is_retained(self):
        raw = {'handle': 'author', 'body_spans': [], 'media': 1,
               'media_urls': ['https://scontent.cdninstagram.com/photo.jpg'], 'postHref': '/@author/post/1'}
        comment = ts.card_from_raw(raw)
        self.assertIsNotNone(comment)
        self.assertEqual(comment['text'], '')
        self.assertEqual(comment['media_urls'], raw['media_urls'])
        _, comments = ts.split_post('https://www.threads.com/@root/post/ROOT', [
            {'handle': 'root', 'text': 'post', 'url': 'https://www.threads.com/@root/post/ROOT'}, comment])
        self.assertEqual(len(comments), 1)

    def test_authenticated_download_keeps_images_and_ignores_bad_response(self):
        request = Mock()
        request.get.return_value = Mock(ok=True, body=lambda: self.photo())
        photos = ts.download_card_media(request, ['https://scontent.cdninstagram.com/photo.jpg'])
        self.assertEqual(len(photos), 1)
        request.get.return_value = Mock(ok=True, body=lambda: b'not an image')
        self.assertEqual(ts.download_card_media(request, ['https://scontent.cdninstagram.com/bad.jpg']), [])
        request.reset_mock()
        self.assertEqual(ts.download_card_media(request, ['http://127.0.0.1/private']), [])
        request.get.assert_not_called()

    def test_anonymous_reply_card_includes_attachment(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'reply.png'
            item = {'text': 'Reply with photo', 'handle': 'private-user', 'likes': 0, 'replies': 0,
                    'depth': 2, '_media_pngs': [self.photo()]}
            ts.render_card(item, target, None, None, ident='anon')
            with Image.open(target) as image:
                self.assertEqual(image.getpixel((540, image.height - 220)), (10, 90, 220))
                self.assertEqual(image.width, 1080)

    def test_scroll_merge_keeps_attachments_from_earlier_pass(self):
        acc = {}
        item = {'handle': 'a', 'text': 'photo', 'media_urls': ['https://scontent.cdninstagram.com/p.jpg']}
        ts._merge_comment(acc, item)
        ts._merge_comment(acc, {**item, 'media_urls': []})
        self.assertEqual(next(iter(acc.values()))['media_urls'], item['media_urls'])
