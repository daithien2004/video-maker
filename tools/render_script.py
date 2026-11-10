"""CLI: dựng video từ file kịch bản.

Usage:
  python tools/render_script.py <kich-ban.txt> [--content <ten-noi-dung>] [--preview]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from videomaker import app, pipeline as pl, script_draft as sd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("script", help="file kịch bản .txt")
    parser.add_argument("--content", default="", help="tên nội dung (assets/illus/<content>/)")
    parser.add_argument("--preview", action="store_true", help="dựng preview thay vì video đầy đủ")
    parser.add_argument("--speed", type=float, default=None, help="tốc độ đọc (ghi đè settings.json)")
    parser.add_argument("--no-align", action="store_true",
                        help="tắt căn mốc giọng thật, dùng ước lượng trọng số cũ")
    parser.add_argument("--lint", action="store_true", help="in cảnh báo máy kiểm (mặc định tắt)")
    args = parser.parse_args()

    cfg = app.load_settings()
    if args.speed:
        cfg["speed"] = args.speed
    if args.content:
        content_dir = ROOT / "assets" / "illus" / args.content
        if not content_dir.is_dir():
            parser.error(f"Không tìm thấy thư viện minh họa: {content_dir}")
        cfg["content"] = args.content
    opt = app.make_opts(*[cfg[k] for k in app.OPT_KEYS])
    if args.no_align:
        opt.align_subs = False
    opt.backend = pl.BACKEND_DUMMY if cfg.get("backend") == "dummy" else opt.backend

    script = Path(args.script).read_text(encoding="utf-8")
    rows = pl.analyze(script, content=cfg.get("content", ""))
    if args.lint:
        for w in sd.lint_rows(rows, cfg.get("content", "")):
            print(f"⚠ {w}")
    out = pl.render(rows, opt, preview=args.preview)
    print(out)


if __name__ == "__main__":
    main()