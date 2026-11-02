"""Real FFmpeg checks: sparse still-image inputs must preserve short beats and the tail."""
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from videomaker import pipeline as pl


class EncoderFallbackTests(unittest.TestCase):
    def test_swap_encoder_replaces_only_the_encoder_flags(self):
        args = ["-i", "a.png", "-map", "[vout]", "-c:a", "aac",
                "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0",
                "-pix_fmt", "yuv420p", "out.mp4"]
        old = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0"]
        new = pl.swap_encoder(args, old, pl.CPU_VENC)
        self.assertEqual(new[:4], args[:4])
        self.assertEqual(new[-3:], ["-pix_fmt", "yuv420p", "out.mp4"])
        self.assertNotIn("h264_nvenc", new)
        self.assertIn("aac", new)
        self.assertEqual(pl.swap_encoder(args, ["-c:v", "libx264"], pl.CPU_VENC), args)


class PassBoundsTests(unittest.TestCase):
    def test_60fps_uses_smaller_clusters_than_30fps(self):
        self.assertEqual(pl._pass_bounds(46, 60), [0, 10, 20, 30, 40])
        self.assertEqual(pl._pass_bounds(15, 60), [0, 10])
        self.assertEqual(pl._pass_bounds(14, 60), [0])
        self.assertEqual(pl._pass_bounds(45, 30), [0])
        self.assertEqual(pl._pass_bounds(46, 30), [0, 22, 44])


class RenderTimingTests(unittest.TestCase):
    def test_background_zoom_preserves_video_motion_frame_count_and_aspect(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pl, 'W', 180), patch.object(pl, 'H', 320):
            target = Path(folder) / 'zoom.mkv'
            subprocess.run([pl.ffmpeg_path(), '-y', '-loglevel', 'error', '-f', 'lavfi',
                '-i', 'testsrc2=size=180x320:rate=30:duration=3',
                '-filter_complex', pl._background_filter(30, 3, True), '-map', '[v0]',
                '-c:v', 'ffv1', str(target)], check=True)
            info = json.loads(subprocess.check_output([pl.ffprobe_path(), '-v', 'error', '-count_frames',
                '-show_streams', '-show_format', '-of', 'json', str(target)]))
            stream = info['streams'][0]
            self.assertEqual(int(stream['nb_read_frames']), 90)
            self.assertEqual(stream['avg_frame_rate'], '30/1')
            self.assertEqual(stream['sample_aspect_ratio'], '1:1')
            self.assertEqual((stream['width'], stream['height']), (180, 320))
            self.assertAlmostEqual(float(info['format']['duration']), 3, places=2)
            hashes = subprocess.check_output([pl.ffmpeg_path(), '-v', 'error', '-i', str(target),
                '-f', 'framemd5', '-'], text=True)
            frames = [line.rsplit(',', 1)[-1].strip() for line in hashes.splitlines() if not line.startswith('#')]
            self.assertGreater(len(set(frames)), 85)

    def test_still_image_reuse_keeps_short_cards_last_frame_audio_and_requested_fps(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder)
            for name in ('WORK_DIR', 'OUT_DIR', 'FONT_DIR'):
                directory = root / name
                directory.mkdir()
                stack.enter_context(patch.object(pl, name, directory))
            stack.enter_context(patch.object(pl, 'W', 180))
            stack.enter_context(patch.object(pl, 'H', 320))
            background = root / 'background.mp4'
            subprocess.run([pl.ffmpeg_path(), '-y', '-loglevel', 'error', '-f', 'lavfi',
                            '-i', 'color=c=black:s=180x320:r=60', '-t', '2',
                            '-c:v', 'libx264', '-preset', 'ultrafast', str(background)], check=True)
            stack.enter_context(patch.object(pl, 'list_backgrounds', return_value=[background]))
            stack.enter_context(patch.object(pl, 'beat_audio', return_value=np.zeros(10560, dtype=np.float32)))
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
            rows = []
            for index, color in enumerate(colors):
                image = root / f'{index}.png'
                Image.new('RGB', (80, 80), color).save(image)
                rows.append([index + 1, 'sample', '-', '', str(image)])
            options = pl.Options(backend=pl.BACKEND_DUMMY, gap=0, meme_w=80, meme_h=80,
                                 nvenc=False, card_motion=False, bg_motion=False,
                                 pop_in=False, mascot=False, next_card=False, sfx=False)
            expected_duration = pl.LEAD + 3 * 0.22 + pl.TAIL
            for requested_fps, preview in ((24, False), (60, False), (60, True)):
                with self.subTest(fps=requested_fps, preview=preview):
                    path = pl.render(rows, replace(options, fps=requested_fps), preview=preview)
                    info = json.loads(subprocess.check_output([pl.ffprobe_path(), '-v', 'error',
                        '-show_streams', '-show_format', '-of', 'json', str(path)]))
                    video = next(stream for stream in info['streams'] if stream['codec_type'] == 'video')
                    audio = next(stream for stream in info['streams'] if stream['codec_type'] == 'audio')
                    fps = min(30, requested_fps) if preview else requested_fps
                    self.assertEqual(video['avg_frame_rate'], f'{fps}/1')
                    self.assertLess(abs(float(video['duration']) - expected_duration), 1 / fps + 0.01)
                    self.assertLess(abs(float(audio['duration']) - expected_duration), 0.04)
                    for timestamp, channel in ((0.30, 0), (0.55, 1), (0.85, 2), (1.40, 2)):
                        png = subprocess.check_output([pl.ffmpeg_path(), '-v', 'error', '-ss', str(timestamp),
                            '-i', str(path), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'])
                        with Image.open(io.BytesIO(png)) as image:
                            # No-subtitle cards are centered at 40% of the unused height.
                            x = round(image.width * 0.5)
                            y = round(image.height * ((320 - 80) * 0.4 + 40) / 320)
                            pixel = image.convert('RGB').getpixel((x, y))
                            self.assertGreater(pixel[channel], 220, (timestamp, pixel))
                            self.assertLess(max(pixel[(channel + 1) % 3], pixel[(channel + 2) % 3]), 35)
