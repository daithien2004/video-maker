"""Tìm và chọn ảnh minh họa từ Wikimedia Commons (có nguồn + giấy phép).

  python tools/tai_anh.py tim "Bornholmer Strasse 1989" [--n 8]
      -> tải ứng viên vào work/anh-ung-vien/<truy-van>/, in danh sách và ghi sheet.png
         (một ảnh ghép đánh số) để XEM trước khi chọn.
  python tools/tai_anh.py chon <noi-dung> <the> <file-ung-vien>
      -> chép ảnh đã chọn vào assets/illus/<noi-dung>/<the>/ và ghi dòng nguồn vào SOURCES.txt.
"""
import argparse
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "VideoMaker/1.0 (local tool; https://commons.wikimedia.org)"}
OK_LICENSE = re.compile(r"public domain|pd|cc0|cc[- ]by|cc[- ]by[- ]sa|gfdl|attribution", re.I)
CAND = ROOT / "work" / "anh-ung-vien"


def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50] or "anh"


def tim(query: str, n: int) -> None:
    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": "6",
              "gsrsearch": query, "gsrlimit": str(max(n * 3, 12)), "prop": "imageinfo",
              "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "1280"}
    data = json.loads(_get(API + "?" + urllib.parse.urlencode(params)))
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = CAND / _slug(query)
    out.mkdir(parents=True, exist_ok=True)
    meta, shown = [], 0
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if min(info.get("width", 0), info.get("height", 0)) < 600:
            continue
        ext = info.get("extmetadata", {})
        lic = (ext.get("LicenseShortName", {}).get("value") or "").strip()
        if not OK_LICENSE.search(lic):
            continue
        shown += 1
        name = f"{shown:02d}.jpg"
        (out / name).write_bytes(_get(info.get("thumburl") or info["url"]))
        author = re.sub(r"<[^>]+>", "", ext.get("Artist", {}).get("value", "")).strip()
        desc = re.sub(r"<[^>]+>", "", ext.get("ImageDescription", {}).get("value", "")).strip()
        meta.append({"file": name, "title": p["title"], "page": info.get("descriptionurl", ""),
                     "license": lic, "author": author[:80], "desc": desc[:160]})
        if shown >= n:
            break
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if not meta:
        print("Không có ảnh phù hợp (cần jpg/png ≥600px, giấy phép mở). Đổi từ khóa.")
        return
    try:
        from PIL import Image, ImageDraw
        w, h, cols = 320, 240, 4
        rows = (len(meta) + cols - 1) // cols
        sheet = Image.new("RGB", (w * cols, (h + 18) * rows), "black")
        d = ImageDraw.Draw(sheet)
        for i, m in enumerate(meta):
            im = Image.open(out / m["file"]).convert("RGB")
            im.thumbnail((w, h))
            x, y = (i % cols) * w, (i // cols) * (h + 18)
            sheet.paste(im, (x, y))
            d.text((x + 3, y + h + 3), f"{m['file']}  {m['license']}", fill="white")
        sheet.save(out / "sheet.png")
    except ImportError:
        pass
    print(f"Ứng viên: {out}")
    for m in meta:
        print(f"  {m['file']}  [{m['license']}]  {m['title']}  | {m['desc'][:80]}")
    print(f"XEM {out / 'sheet.png'} rồi chọn bằng: tai_anh.py chon <noi-dung> <the> {out / '<file>'}")


def chon(content: str, tag: str, cand: str) -> None:
    src = Path(cand)
    meta_file = src.parent / "meta.json"
    dest_dir = ROOT / "assets" / "illus" / content / tag
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{tag}.jpg"
    shutil.copy(src, dest)
    note = f"{tag}: {src.name}"
    if meta_file.exists():
        for m in json.loads(meta_file.read_text(encoding="utf-8")):
            if m["file"] == src.name:
                note = f"{tag}: {m['title']} | {m['license']} | {m['author']} | {m['page']}"
    with (ROOT / "assets" / "illus" / content / "SOURCES.txt").open("a", encoding="utf-8") as f:
        f.write(note + "\n")
    print(f"Đã chọn -> {dest}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tim")
    t.add_argument("query")
    t.add_argument("--n", type=int, default=8)
    c = sub.add_parser("chon")
    c.add_argument("content")
    c.add_argument("tag")
    c.add_argument("cand")
    a = ap.parse_args()
    tim(a.query, a.n) if a.cmd == "tim" else chon(a.content, a.tag, a.cand)


if __name__ == "__main__":
    main()
