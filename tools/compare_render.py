"""Measure real MP4 exports before/after compositor changes; retain samples for review."""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from videomaker import app, pipeline as pl


def execute(args, cwd, timeout=180):
    return subprocess.run([pl.ffmpeg_path(), '-y', '-hide_banner', '-nostdin', *args], cwd=cwd,
                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)


def main():
    root = pl.WORK_DIR / 'render-optimization' / datetime.now().strftime('%Y%m%d_%H%M%S')
    root.mkdir(parents=True)
    cfg = app.load_settings()
    opt = replace(app.threads_opts('', *[cfg[key] for key in app.OPT_KEYS]),
                  backend=pl.BACKEND_DUMMY, content='', seed=0, fps=60, nvenc=True, bg_motion=True)
    source_file = pl.ILLUS_DIR / 'mua-do/post/threads.json'
    source = json.loads(source_file.read_text(encoding='utf-8'))
    images = [pl.ILLUS_DIR / source['content'] / item['image'] for item in [source['post']] + source['comments'][:2]]
    rows = [[index + 1, 'Sample audio', 'KIỂM TRA *CHẤT LƯỢNG* CHỮ' if index == 1 else '-', '', str(image)]
            for index, image in enumerate(images)]
    captured = []
    with patch.object(pl, 'WORK_DIR', root), patch.object(pl, 'OUT_DIR', root), \
            patch.object(pl, 'beat_audio', return_value=np.zeros(120000, dtype=np.float32)), \
            patch.object(pl, 'run_ffmpeg', side_effect=lambda command, cwd: captured.append((command, cwd))):
        pl.render(rows, opt, preview=False)
    original, cwd = next(item for item in captured if '-filter_complex' in item[0])
    duration_at = len(original) - 1 - original[::-1].index('-t')
    total = float(original[duration_at + 1])
    fps, width, height = opt.fps, pl.W * 2, pl.H * 2
    zoom = f'(1+0.10*min(t,{total:.2f})/{total:.2f})'
    legacy_bg = (f'[0:v]fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase,'
                 f'crop={width}:{height},'
                 f"scale=w='trunc({width}*{zoom})':h='trunc({height}*{zoom})':eval=frame,"
                 f'crop={width}:{height}:(in_w-{width})/2:(in_h-{height})/2,'
                 f'scale={pl.W}:{pl.H},setsar=1,format=yuv420p[v0]')
    variants = {}
    for name in ('legacy', 'image_reuse', 'optimized'):
        command = list(original)
        graph_at = command.index('-filter_complex') + 1
        if name != 'optimized':
            command[graph_at] = legacy_bg + ';' + command[graph_at].split(';', 1)[1]
        if name == 'legacy':
            for index, value in enumerate(command):
                if value == '-framerate':
                    command[index + 1] = str(fps)
        command[duration_at + 1] = '8'
        variants[name] = command
    results = []
    for repeat in range(2):
        order = list(variants) if repeat == 0 else list(reversed(variants))
        for name in order:
            command = variants[name][:-1] + [str(root / f'{name}_{repeat}.mp4')]
            print(f'Encoding {name}, repeat {repeat + 1}', flush=True)
            started = time.perf_counter()
            process = execute(['-loglevel', 'error', *command], cwd)
            if process.returncode:
                raise RuntimeError(process.stderr[-2500:])
            result = {'name': name, 'repeat': repeat, 'wall_seconds': round(time.perf_counter() - started, 3),
                      'bytes': Path(command[-1]).stat().st_size}
            results.append(result)
            print(json.dumps(result), flush=True)
            if repeat:
                Path(command[-1]).unlink() # Repeats are timed; only the first samples are needed for review.
    quality = {}
    for name in ('image_reuse', 'optimized'):
        process = execute(['-i', str(root / 'legacy_0.mp4'), '-i', str(root / f'{name}_0.mp4'),
                           '-filter_complex', '[0:v][1:v]ssim', '-an', '-f', 'null', '-'], root)
        match = re.search(r'All:([\d.]+)', process.stderr)
        quality[name] = {'ssim_against_legacy': float(match.group(1)) if match else None}
        if process.returncode:
            raise RuntimeError(process.stderr[-2500:])
    # Stable second-card interval: inspect text/card separately from background resampling.
    for region, crop in (('card', '800:800:140:210'), ('subtitles', '860:300:110:1100')):
        filters = (f'[0:v]trim=start=3.2:end=4.5,setpts=PTS-STARTPTS,crop={crop}[a];'
                   f'[1:v]trim=start=3.2:end=4.5,setpts=PTS-STARTPTS,crop={crop}[b];[a][b]ssim')
        process = execute(['-i', str(root / 'legacy_0.mp4'), '-i', str(root / 'optimized_0.mp4'),
                           '-filter_complex', filters, '-an', '-f', 'null', '-'], root)
        match = re.search(r'All:([\d.]+)', process.stderr)
        quality['optimized'][region] = {'crop': crop, 'interval': [3.2, 4.5],
                                        'ssim_against_legacy': float(match.group(1)) if match else None}
        if process.returncode:
            raise RuntimeError(process.stderr[-2500:])
    for name in variants:
        process = execute(['-ss', '3.2', '-i', str(root / f'{name}_0.mp4'), '-frames:v', '1',
                           str(root / f'{name}.png')], root)
        if process.returncode:
            raise RuntimeError(process.stderr[-2500:])
    median = {name: statistics.median(item['wall_seconds'] for item in results if item['name'] == name) for name in variants}
    report = {'sample_seconds': 8, 'fps': fps, 'resolution': [pl.W, pl.H], 'nvenc_preset': 'p5',
              'scope': 'Real Threads cards, subtitles, mascot, next-card transitions, zoom background; silent voice stub',
              'runs': results, 'median_wall_seconds': median, 'quality': quality,
              'speedup': median['legacy'] / median['optimized']}
    audio_hashes = []
    for name in ('legacy', 'optimized'):
        sample = root / f'{name}_0.mp4'
        metadata = json.loads(subprocess.check_output([pl.ffprobe_path(), '-v', 'error',
                                '-show_streams', '-of', 'json', str(sample)]))
        report.setdefault('media', {})[name] = [{key: stream.get(key) for key in
            ('codec_type', 'codec_name', 'width', 'height', 'avg_frame_rate', 'duration', 'pix_fmt')}
            for stream in metadata['streams']]
        process = execute(['-v', 'error', '-i', str(sample), '-map', '0:a', '-c:a', 'pcm_s16le',
                           '-f', 'hash', '-hash', 'sha256', '-'], root)
        if process.returncode:
            raise RuntimeError(process.stderr[-2500:])
        audio_hashes.append(process.stdout.strip())
    report['decoded_audio_identical'] = audio_hashes[0] == audio_hashes[1]
    (root / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(root / 'report.json'), **report}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
