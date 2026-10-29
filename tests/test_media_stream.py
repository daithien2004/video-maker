import asyncio
import tempfile
import unittest
from pathlib import Path

from videomaker.api import _open_shared


class SharedMediaFileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.file = Path(temporary.name) / 'video.mp4'
        self.file.write_bytes(b'video-bytes')

    def test_video_can_be_deleted_while_browser_streams_it(self):
        async def scenario():
            handle = _open_shared(str(self.file))
            try:
                self.assertEqual(await handle.read(5), b'video')
                self.file.unlink()
                self.assertFalse(self.file.exists())
            finally:
                await handle.aclose()

        asyncio.run(scenario())
