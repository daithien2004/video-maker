import tempfile
import unittest
from pathlib import Path

from videomaker.output_cleanup import delete_output, related_files


class OutputCleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'output'
        self.work = self.root / 'work'
        self.output.mkdir()
        self.work.mkdir()
        self.video = self.output / 'video_demo.mp4'
        self.video.write_bytes(b'video')

    def test_deletes_video_and_same_name_companions_only(self):
        metadata = self.video.with_suffix('.json')
        subtitle = self.video.with_suffix('.srt')
        for path in (metadata, subtitle):
            path.write_text('sidecar')
        other = self.output / 'video_demo_other.mp4'
        other.write_bytes(b'keep')
        unrelated = self.output / 'notes.txt'
        unrelated.write_text('keep')
        job = self.work / 'job_20261028_120000'
        job.mkdir()
        (job / 'voice.wav').write_bytes(b'keep')
        files = related_files(self.video, self.output)
        self.assertEqual(files, [self.video.resolve(), metadata.resolve(), subtitle.resolve()])
        delete_output(self.video, self.output)
        self.assertFalse(self.video.exists())
        self.assertFalse(metadata.exists())
        self.assertFalse(subtitle.exists())
        self.assertTrue(other.exists())
        self.assertTrue(unrelated.exists())

    def test_render_job_folder_is_kept_for_cache_cleanup(self):
        job = self.work / 'job_20261028_120000'
        job.mkdir()
        (job / 'voice.wav').write_bytes(b'keep')
        self.video.with_suffix('.json').write_text('{"render_job": "job_20261028_120000"}')
        delete_output(self.video, self.output)
        self.assertTrue(job.exists())
        self.assertTrue((job / 'voice.wav').exists())

    def test_refuses_video_outside_output_or_nonvideo(self):
        outside = self.work / 'source.mp4'
        outside.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            delete_output(outside, self.output)
        text = self.output / 'secret.json'
        text.write_text('keep')
        with self.assertRaises(ValueError):
            delete_output(text, self.output)
        self.assertTrue(outside.exists())
        self.assertTrue(text.exists())
