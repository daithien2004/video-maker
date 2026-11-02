"""CLI: dựng video từ file kịch bản.

Usage:
  python tools/render_script.py <kich-ban.txt> [--content <ten-noi-dung>] [--preview]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from videomaker import app, pipeline as pl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("script", help="file kịch bản .txt")
    parser.add_argument("--content", default="", help="tên nội dung (assets/illus/<content>/)")
    parser.add_argument("--preview", action="store_true", help="dựng preview thay vì video đầy đủ")
    args = parser.parse_args()

    cfg = app.load_settings()
    if args.content:
        cfg["content"] = args.content
    opt = app.make_opts(*[cfg[k] for k in app.OPT_KEYS])
    opt.backend = pl.BACKEND_DUMMY if cfg.get("backend") == "dummy" else opt.backend

    script = Path(args.script).read_text(encoding="utf-8")
    rows = pl.analyze(script, content=cfg.get("content", ""))
    out = pl.render(rows, opt, preview=args.preview)
    print(out)


if __name__ == "__main__":
    main()