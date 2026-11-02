"""Compare the real compositor on a short sample, without TTS or publishing a video."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from videomaker import app, pipeline as pl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=2.0)
    parser.add_argument('--report', type=Path, default=pl.WORK_DIR / 'render-profile.json')
    args = parser.parse_args()
    if not 0.5 <= args.seconds <= 10:
        parser.error('--seconds must be between 0.5 and 10')
    cfg = {**app.DEFAULTS, **json.loads(app.SETTINGS_FILE.read_text(encoding='utf-8'))}
    options = app.threads_opts('', *[cfg[key] for key in app.OPT_KEYS])
    options = replace(options, backend=pl.BACKEND_DUMMY, content='', seed=0)
    images = list(pl.ILLUS_DIR.rglob('*.png'))[:3]
    if not images:
        parser.error('Add at least one illustration first')
    rows = [[index + 1, 'Benchmark sample', '-', '', str(image)] for index, image in enumerate(images)]
    results = []
    pl.WORK_DIR.mkdir(parents=True, exist_ok=True)
    # TemporaryDirectory owns this newly-created workspace; existing jobs are never deleted.
    with tempfile.TemporaryDirectory(prefix='render_profile_', dir=pl.WORK_DIR) as directory:
        root = Path(directory)
        for name, opt in (
            ('nvenc_60_motion', replace(options, nvenc=True, fps=60, bg_motion=True)),
            ('nvenc_60_static', replace(options, nvenc=True, fps=60, bg_motion=False)),
            ('nvenc_30_motion', replace(options, nvenc=True, fps=30, bg_motion=True)),
            ('cpu_60_motion', replace(options, nvenc=False, fps=60, bg_motion=True)),
        ):
            trial = root / name
            trial.mkdir()
            captured = []
            with patch.object(pl, 'WORK_DIR', trial), patch.object(pl, 'OUT_DIR', trial), \
                    patch.object(pl, 'beat_audio', return_value=np.zeros(48000 * 3, dtype=np.float32)), \
                    patch.object(pl, 'run_ffmpeg', side_effect=lambda command, cwd: captured.append((command, cwd))):
                pl.render(rows, opt, preview=False)
            command, cwd = next(item for item in captured if '-filter_complex' in item[0])
            command = command[:-1]
            last_duration = len(command) - 1 - command[::-1].index('-t')
            command[last_duration + 1] = str(args.seconds)
            command += ['-f', 'null', '-']
            started = time.perf_counter()
            process = subprocess.run([pl.ffmpeg_path(), '-hide_banner', '-nostdin', '-loglevel', 'error', *command],
                                     cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
            result = {'name': name, 'wall_seconds': round(time.perf_counter() - started, 3),
                      'sample_seconds': args.seconds, 'ok': process.returncode == 0}
            if process.returncode:
                result['error'] = process.stderr[-1500:]
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'scope': '3 static illustration cards; real pipeline filters; silent cached audio; null output',
                                     'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
