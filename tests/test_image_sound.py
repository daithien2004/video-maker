import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from videomaker import pipeline as pl, threads_shot as ts, app


class ImageSoundTests(unittest.TestCase):
    def test_image_only_source_and_empty_section_get_sound_beat(self):
        source = {'content': 'demo', 'post': {'text': 'Hello', 'image': 'post/main.png'},
                  'comments': [{'text': '', 'image': 'post/photo.png', 'depth': 2}]}
        script = ts.build_editable_script(source)
        sections = ts.parse_sections(script)
        self.assertEqual(sections[-1], ('post/photo.png', ['[sound] || -']))
        self.assertEqual(ts.parse_sections('# post/photo.png\n'), [('post/photo.png', ['[sound] || -'])])
        rows = app.on_threads_build(script, source)[1]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1:3], ['[sound]', '-'])
        self.assertEqual(rows[1][4], 'post/photo.png')

    def test_empty_spoken_line_becomes_sound_without_count_mismatch(self):
        source = {'post': {'text': '', 'image': 'post/photo.png'}, 'comments': []}
        rows = app.on_threads_build('# post/photo.png\n|| -', source)[1]
        self.assertEqual(rows[0][1:3], ['[sound]', '-'])

    def test_real_selected_sound_is_decoded_without_tts_or_speed_change(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pl, 'CACHE_DIR', Path(folder)), \
                patch.object(pl, 'synth', side_effect=AssertionError('Sound must not use TTS')):
            audio = pl.beat_audio('[sound]', pl.Options(threads=True, speed=1.4))
            self.assertEqual(audio.ndim, 1)
            self.assertGreater(len(audio) / 48000, 1.4)
            self.assertLess(len(audio) / 48000, 1.8)
            self.assertGreater(float(np.max(np.abs(audio))), 0.01)
            decoded, _ = sf.read(next(Path(folder).glob('sound_*_48000.wav')), dtype='float32')
            np.testing.assert_allclose(audio, decoded * 0.6)
            zoom_audio = pl.beat_audio('[zoom]', pl.Options(threads=True))
            np.testing.assert_array_equal(audio, zoom_audio)

    def test_zoom_beat_keeps_same_image_but_separate_visual_span(self):
        source = {'post': {'text': 'Hello', 'image': 'post/photo.png'}, 'comments': []}
        rows = app.on_threads_build('# post/photo.png\nHello || -\n[zoom] || -', source)[1]
        self.assertEqual([row[1] for row in rows], ['Hello', '[zoom]'])
        self.assertEqual(rows[0][4], rows[1][4])
        timed = [dict(clip='photo.png', display='', vis_start=0, vis_end=1, zoom=False),
                 dict(clip='photo.png', display='', vis_start=1, vis_end=2, zoom=True)]
        spans = pl._build_spans(timed, True)
        self.assertEqual(len(spans), 2)
        self.assertFalse(spans[0]['zoom'])
        self.assertTrue(spans[1]['zoom'])

    def test_speech_is_resampled_to_same_rate_as_sound(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / 'speech.wav'
            sf.write(source, np.sin(np.arange(24000) * 0.03).astype('float32'), 24000)
            with patch.object(pl, 'CACHE_DIR', folder), patch.object(pl, 'synth', return_value=source):
                audio = pl.beat_audio('speech', pl.Options())
            self.assertEqual(len(audio), 48000)

    def test_zoom_setting_is_validated_and_passed_to_renderer(self):
        self.assertEqual(app._clean('threads_zoom', 160), 160)
        self.assertEqual(app._clean('threads_zoom', 500), 200)
        cfg = {**app.DEFAULTS, 'threads_zoom': 160}
        opt = app.threads_opts('', *[cfg[key] for key in app.OPT_KEYS])
        self.assertEqual(opt.threads_zoom, 160)
