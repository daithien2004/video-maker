"""Kiểm tra luồng Reels; mọi request Facebook đều được giả lập.

Chạy từ thư mục dự án: python -m unittest discover -s tools -p test_fb_reels.py
"""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import requests

from videomaker import fb_post as fb


def response(data, status=200):
    result = requests.Response()
    result.status_code = status
    result.encoding = "utf-8"
    result._content = json.dumps(data).encode()
    return result


class ReelUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.mp4"
        self.content = b"\x00\xff\r\n" * 600000
        self.path.write_bytes(self.content)
        self.when = datetime.now().replace(microsecond=0) + timedelta(days=1)
        self.start = {"video_id": "987654", "upload_url":
                      "https://rupload.facebook.com/video-upload/v24.0/987654"}
        self.cfg = {"graph_base": "https://graph.facebook.com", "version": "v24.0"}

    def upload(self, when=None):
        return fb.upload_reel("123456", "test-token", self.path,
                              "Caption tiếng Việt\n\n#kienthuc", when, cfg=self.cfg)

    def test_scheduled_reel_stream_and_finish(self):
        calls = []
        handles = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            self.assertIsNot(kwargs.get("verify"), False)
            self.assertFalse(kwargs["allow_redirects"])
            if len(calls) == 1:
                self.assertEqual(kwargs["data"]["upload_phase"], "start")
                return response(self.start)
            if len(calls) == 2:
                self.assertEqual(url, self.start["upload_url"])
                body = kwargs["data"]
                handles.append(body)
                self.assertTrue(hasattr(body, "read"))
                digest = hashlib.sha256()
                for chunk in iter(lambda: body.read(65536), b""):
                    digest.update(chunk)
                self.assertEqual(digest.digest(), hashlib.sha256(self.content).digest())
                self.assertNotIn("files", kwargs)
                self.assertEqual(kwargs["headers"]["Authorization"], "OAuth test-token")
                self.assertEqual(kwargs["headers"]["Content-Type"], "application/octet-stream")
                self.assertEqual(kwargs["headers"]["Content-Length"], str(len(self.content)))
                self.assertEqual(kwargs["headers"]["file_size"], str(len(self.content)))
                self.assertEqual(kwargs["headers"]["offset"], "0")
                return response({"success": True})
            data = kwargs["data"]
            self.assertEqual(data["upload_phase"], "finish")
            self.assertEqual(data["video_state"], "SCHEDULED")
            self.assertEqual(data["scheduled_publish_time"], str(int(self.when.timestamp())))
            self.assertEqual(data["video_id"], self.start["video_id"])
            self.assertIn("tiếng Việt", data["description"])
            self.assertNotIn("published", data)
            return response({"success": True})

        with patch.object(fb.requests, "post", side_effect=post):
            result = self.upload(self.when)
        self.assertEqual(result, {"id": "987654", "type": "reel", "success": True})
        self.assertEqual(len(calls), 3)
        self.assertTrue(handles[0].closed)
        for index in (0, 2):
            self.assertEqual(calls[index][0], "https://graph.facebook.com/v24.0/123456/video_reels")

    def test_publish_now(self):
        with patch.object(fb.requests, "post", side_effect=[
                response(self.start), response({"success": True}), response({"success": True})]) as post:
            self.upload()
        finish = post.call_args.kwargs["data"]
        self.assertEqual(finish["video_state"], "PUBLISHED")
        self.assertNotIn("scheduled_publish_time", finish)

    def test_reject_untrusted_upload_url_before_sending_token(self):
        for url in ("https://attacker.example/video-upload/1",
                    "http://rupload.facebook.com/video-upload/1",
                    "https://rupload.facebook.com.attacker.example/video-upload/1"):
            with self.subTest(url=url), patch.object(fb.requests, "post", return_value=response(
                    dict(self.start, upload_url=url))) as post:
                with self.assertRaises(fb.FbError):
                    self.upload()
                self.assertEqual(post.call_count, 1)

    def test_upload_rejection_never_finishes(self):
        for result in (response({}, 413), response({"success": False}),
                       response({"error": {"message": "Permission denied", "code": 200}}, 403)):
            with self.subTest(status=result.status_code), patch.object(fb.requests, "post", side_effect=[
                    response(self.start), result]) as post:
                with self.assertRaises(fb.FbError):
                    self.upload(self.when)
                self.assertEqual(post.call_count, 2)

    def test_network_failure_at_each_phase_no_automatic_replay(self):
        for phase in range(3):
            for error in (requests.exceptions.SSLError("test"),
                          requests.exceptions.ReadTimeout("test"),
                          requests.exceptions.ConnectionError("test")):
                responses = [response(self.start), response({"success": True})][:phase]
                with self.subTest(phase=phase, error=type(error)), patch.object(
                        fb.requests, "post", side_effect=[*responses, error]) as post:
                    with self.assertRaisesRegex(fb.FbError, "Meta Business Suite"):
                        self.upload(self.when)
                    self.assertEqual(post.call_count, phase + 1)

    def test_finish_requires_explicit_success(self):
        with patch.object(fb.requests, "post", side_effect=[
                response(self.start), response({"success": True}), response({"success": False})]):
            with self.assertRaises(fb.FbError):
                self.upload(self.when)

    def test_schedule_expires_during_upload_never_finishes(self):
        with patch.object(fb, "_validate_reel_time", side_effect=[
                None, fb.FbError("Schedule expired")]), patch.object(fb.requests, "post", side_effect=[
                response(self.start), response({"success": True})]) as post:
            with self.assertRaisesRegex(fb.FbError, "Schedule expired"):
                self.upload(self.when)
            self.assertEqual(post.call_count, 2)

    def test_invalid_schedule_or_empty_file_never_starts_upload(self):
        with patch.object(fb.requests, "post") as post:
            for when in (datetime.now(), datetime.now() + timedelta(days=31)):
                with self.assertRaises(fb.FbError):
                    fb.schedule_reel("123456", "test-token", self.path, "caption", when, cfg=self.cfg)
            self.path.write_bytes(b"")
            with self.assertRaises(fb.FbError):
                self.upload()
            post.assert_not_called()

    def test_check_uses_token_identity_and_requires_matching_page(self):
        with patch.object(fb.requests, "get", return_value=response(
                {"id": "123456", "name": "Test Page"})) as get:
            result = fb.check("123456", "test-token", cfg=self.cfg)
            self.assertEqual(result["id"], "123456")
            self.assertTrue(get.call_args.args[0].endswith("/me"))
        with patch.object(fb.requests, "get", return_value=response(
                {"id": "999999", "name": "Different identity"})):
            with self.assertRaises(fb.FbError):
                fb.check("123456", "test-token", cfg=self.cfg)

    def test_permission_error_never_uploads_file(self):
        with patch.object(fb.requests, "post", return_value=response({"error": {
                "code": 200,
                "message": "Subject does not have permission to post videos on this target"}}, 403)) as post:
            with self.assertRaisesRegex(fb.FbError, "pages_manage_posts"):
                self.upload(self.when)
            self.assertEqual(post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
