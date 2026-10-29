"""Đường dẫn dữ liệu tính từ thư mục dự án, độc lập với nơi chạy lệnh."""
from pathlib import Path
import os
import tempfile

APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_DIR / "config"
BROWSER_TEMP_DIR = APP_DIR / "work" / "browser_temp"


def configure_browser_temp() -> Path:
    """Set process-local temp paths before Playwright starts its Node driver."""
    directory = BROWSER_TEMP_DIR.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        os.environ[key] = str(directory)
    # Python may have cached a different temp directory before the browser task.
    tempfile.tempdir = str(directory)
    return directory
