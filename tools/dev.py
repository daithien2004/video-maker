"""Chạy app.py ở chế độ tự khởi động lại khi sửa code — dùng lúc đang phát triển.

    run_dev.bat        (hoặc: .venv\\Scripts\\python.exe tools/dev.py)

Sửa app.py / pipeline.py rồi lưu -> app tự tắt và bật lại sau ~1 giây.
Lưu ý: phải F5 lại trang web sau khi app bật lại, và không nên lưu file lúc đang xuất video.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
WATCH = sorted((APP_DIR / "videomaker").glob("*.py"))
WATCH += sorted((APP_DIR / "frontend" / "src").glob("*"))
WATCH += [APP_DIR / "frontend" / "vite.config.js", APP_DIR / "frontend" / "index.html"]
URL = "http://127.0.0.1:7860"
POLL = 0.8

# console Windows có thể là cp1252 -> in tiếng Việt sẽ lỗi, ép sang UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def _log(message: str) -> None:
    print(message, flush=True)


def _stamps() -> dict[Path, float]:
    return {p: p.stat().st_mtime for p in WATCH if p.exists()}


def _start() -> subprocess.Popen:
    env = dict(os.environ, VIDEOMAKER_NO_BROWSER="1", PYTHONUTF8="1")
    return subprocess.Popen([sys.executable, "-m", "videomaker"], cwd=str(APP_DIR), env=env)


def _build_frontend() -> bool:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        _log("[dev] Khong tim thay npm. Cai Node.js de build giao dien React.")
        return False
    return subprocess.run([npm, "run", "build"], cwd=str(APP_DIR / "frontend")).returncode == 0


def _stop(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def main() -> int:
    if not _build_frontend():
        return 1
    _log(f"[dev] Theo dõi: {', '.join(p.name for p in WATCH)} — sửa và lưu là app tự khởi động lại.")
    _log(f"[dev] Địa chỉ: {URL}  (Ctrl+C để tắt)")
    # chỉ tự mở trình duyệt khi chạy trong cửa sổ console thật (không mở khi chạy nền/lấy log)
    if sys.stdout.isatty():
        threading.Timer(4.0, lambda: webbrowser.open(URL)).start()

    child = _start()
    _log(f"[dev] App PID {child.pid} đang khởi động...")
    last = _stamps()
    try:
        while True:
            time.sleep(POLL)
            if child.poll() is not None:
                _log(f"[dev] App đã dừng (mã {child.returncode}). Sửa lỗi rồi chạy lại, hoặc Ctrl+C để thoát.")
                return child.returncode or 0
            now = _stamps()
            if now != last:
                changed = {p for p in now.keys() | last.keys() if now.get(p) != last.get(p)}
                if any(APP_DIR / "frontend" in p.parents for p in changed):
                    if not _build_frontend():
                        _log("[dev] Build React loi. Sua code roi luu de thu lai.")
                        last = now
                        continue
                _log("[dev] Có thay đổi -> khởi động lại app...")
                _stop(child)
                child = _start()
                last = _stamps()
                _log(f"[dev] Đã bật lại (PID {child.pid}). F5 lại trang web.")
    except KeyboardInterrupt:
        _log("\n[dev] Đang thoát...")
        return 0
    finally:
        _stop(child)


if __name__ == "__main__":
    raise SystemExit(main())
