"""Tự kiểm một video vừa dựng preview: kịch bản + ảnh + phụ đề + độ dài.

  python tools/kiem_video.py assets/illus/<noi-dung>/kich-ban.txt --content <noi-dung>

In từng dòng ĐẠT / LỖI / LƯU Ý. Mã thoát 1 nếu có LỖI. Chạy sau khi đã dựng preview
(đọc job_* và preview_* mới nhất trong work/).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from videomaker import pipeline as pl  # noqa: E402

WORK = ROOT / "work"
MIN_SUB, WARN_SUB = 0.15, 0.25     # giây: phụ đề ngắn hơn mức này là lỗi / lưu ý
MIN_LEN, MAX_LEN = 50.0, 80.0      # giây: độ dài video mong muốn (chuẩn ~1 phút)
WEAK_END = {"cái", "một", "của", "và", "là", "để", "cho", "trong", "với", "những", "các", "thì", "mà", "bị", "được", "ở", "từ", "như", "này", "ấy"}


def newest(pattern: str) -> Path | None:
    items = sorted(WORK.glob(pattern), key=lambda p: p.stat().st_mtime)
    return items[-1] if items else None


def ass_sec(t: str) -> float:
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def style_notes(rows, content: str) -> list[str]:
    """Soi ngắt nghỉ và nhấn mạnh: phụ đề cắt đúng chỗ giọng nghỉ, nhấn ít và đúng từ khóa."""
    out = []
    for i, r in enumerate(rows, 1):
        items = pl.parse_emph(str(r[1]))
        # đoạn giữa hai dấu câu quá dài: giọng không nghỉ, phụ đề bị cắt máy móc
        run = 0
        for w, _ in items:
            run += 1
            if w[-1] in ",;:.!?…":
                if run > 10:
                    out.append(f"nhịp {i}: có đoạn {run} từ không dấu phẩy (thêm dấu phẩy ở chỗ giọng nghỉ)")
                run = 0
        if run > 10:
            out.append(f"nhịp {i}: có đoạn {run} từ không dấu phẩy")
        groups, prev = [], False
        for w, e in items:
            if e and not prev:
                groups.append([])
            if e:
                groups[-1].append(w.strip(",;:.!?…").lower())
            prev = e
        if len(groups) > 2 or any(len(g) > 3 for g in groups):
            out.append(f"nhịp {i}: nhấn quá nhiều ({len(groups)} cụm) hoặc cụm nhấn quá dài")
        if any(g[0] in WEAK_END or g[-1] in WEAK_END for g in groups):
            out.append(f"nhịp {i}: nhấn vào từ phụ (cái/của/và…)")
        try:
            chunks = pl.split_items(items, 4, content=content)
        except ValueError:
            continue
        for c, nxt in zip(chunks, chunks[1:]):
            if c[-1][1] and nxt[0][1]:
                out.append(f"nhịp {i}: cụm nhấn bị cắt đôi ở '{c[-1][0]} | {nxt[0][0]}'")
            if c[-1][0][-1] not in ",;:.!?…" and c[-1][0].lower() in WEAK_END:
                out.append(f"nhịp {i}: phụ đề kết thúc bằng từ nối '{c[-1][0]}' (thêm dấu phẩy trước/đổi cách chia)")
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--content", required=True)
    a = ap.parse_args()
    bad, note = [], []

    rows = pl.analyze(Path(a.script).read_text(encoding="utf-8"), content=a.content)
    imgs = [str(r[4] or "") for r in rows]
    words = sum(len(str(r[1]).replace("*", "").split()) for r in rows)
    print(f"Kịch bản: {len(rows)} nhịp, {words} từ")
    for i, (r, im) in enumerate(zip(rows, imgs), 1):
        if not im:
            bad.append(f"nhịp {i} không có ảnh ({str(r[1])[:40]}…)")
        elif not (ROOT / "assets" / "illus" / a.content / im).is_file():
            bad.append(f"nhịp {i} trỏ tới ảnh không tồn tại: {im}")
    names = [Path(x).name for x in imgs if x]
    dup = {n for n in names[1:-1] if names.count(n) > 1} | ({names[0]} if names.count(names[0]) > 2 else set())
    if dup:
        bad.append("ảnh bị lặp ở giữa video: " + ", ".join(sorted(dup)))
    if names and names[0] != names[-1]:
        bad.append(f"ảnh đầu ({names[0]}) khác ảnh cuối ({names[-1]})")
    if not 235 <= words <= 320:
        bad.append(f"{words} từ — chuẩn 235–320 từ (khoảng 1 phút, đo thực tế ~4,3 từ/giây)")
    if not 12 <= len(rows) <= 22:
        note.append(f"{len(rows)} nhịp — chuẩn 12–22 nhịp")
    note += style_notes(rows, a.content)

    job, prev = newest("job_*"), newest("preview_*.mp4")
    if prev:
        out = subprocess.run([str(ROOT / "ffmpeg" / "bin" / "ffprobe.exe"), "-v", "error", "-show_entries",
                              "format=duration", "-of", "default=nw=1:nk=1", str(prev)],
                             capture_output=True, text=True).stdout.strip()
        dur = float(out or 0)
        print(f"Preview: {prev.name} — {dur:.1f} giây")
        if not MIN_LEN <= dur <= MAX_LEN:
            note.append(f"độ dài {dur:.1f}s ngoài khoảng {MIN_LEN:.0f}–{MAX_LEN:.0f}s")
    else:
        bad.append("chưa có preview để kiểm")
    if job and (job / "subs.ass").exists():
        lines = []
        for ln in (job / "subs.ass").read_text(encoding="utf-8").splitlines():
            m = re.match(r"Dialogue: \d+,([\d:.]+),([\d:.]+),Main,,0,0,0,,(.*)", ln)
            if m:
                lines.append((ass_sec(m[1]), ass_sec(m[2]), re.sub(r"\{[^}]*\}", "", m[3])))
        short = [(round(e - s, 2), t) for s, e, t in lines if e - s < MIN_SUB]
        tiny = [(round(e - s, 2), t) for s, e, t in lines if MIN_SUB <= e - s < WARN_SUB]
        if short:
            bad.append("phụ đề gần như không hiện: " + "; ".join(f"{t} ({d}s)" for d, t in short[:5]))
        if tiny:
            note.append("phụ đề rất ngắn: " + "; ".join(f"{t} ({d}s)" for d, t in tiny[:5]))
        if lines:
            gap = max((lines[i + 1][0] - lines[i][1] for i in range(len(lines) - 1)), default=0)
            if gap > 1.5:
                note.append(f"có khoảng trống phụ đề {gap:.1f}s")
        print(f"Phụ đề: {len(lines)} dòng")
    for n in note:
        print("LƯU Ý:", n)
    for b in bad:
        print("LỖI:", b)
    if not bad:
        print("ĐẠT: ảnh đủ, không lặp, đầu = cuối, phụ đề ổn.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
