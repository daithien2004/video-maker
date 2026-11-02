"""Remove an exported video and same-name sidecars anywhere under output/."""
import time
from pathlib import Path


def related_files(video, output_dir):
    """Video MP4 trong output/ + các file cùng tên nằm cạnh nó (metadata, phụ đề, ảnh bìa)."""
    video, output_dir = Path(video), Path(output_dir).resolve()
    resolved = video.resolve()
    if video.is_symlink() or output_dir not in resolved.parents or video.suffix.lower() != '.mp4':
        raise ValueError('Chỉ được xóa video MP4 trong output.')
    if not video.is_file():
        raise ValueError('Video không còn tồn tại.')
    files = [video.resolve()]
    for suffix in ('.json', '.srt', '.ass', '.vtt', '.jpg', '.jpeg', '.png', '.webp'):
        sidecar = video.with_suffix(suffix)
        if sidecar.is_file() and not sidecar.is_symlink() and sidecar.resolve().parent == resolved.parent:
            files.append(sidecar.resolve())
    return files


def delete_output(video, output_dir, attempts: int = 6, delay: float = 0.4):
    """Windows giữ handle thêm vài trăm ms sau khi player/khung xem trước nhả file."""
    removed = []
    for path in related_files(video, output_dir):
        for attempt in range(attempts):
            try:
                path.unlink()
                break
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                time.sleep(delay)
        removed.append(path)
    return removed
