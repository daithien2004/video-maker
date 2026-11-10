"""Kiểm tra nhanh cách đọc TTS trên bảng nhịp: nhịp quá dài, viết tắt còn sót, đại từ treo,
giọng văn viết, lời bình luận cảm xúc và cỡ nhịp đều nhau.

Bảng viết tắt dưới đây là nguồn tra cứu của bước kiểm tra; glossary người dùng tự thêm
(`work/tts_glossary.json`) được gộp vào cùng.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import threads_shot as ts

GLOSSARY_FILE = ts.WORK_DIR / "tts_glossary.json"

# Viết tắt phổ biến — chỉ những từ KHÔNG lệch nghĩa theo ngữ cảnh mới để máy tự đổi;
# đại từ (t, m) và slang mơ hồ ("m10", "si"…) không tự đoán, để lại cho cổng duyệt.
_TEENCODE = {
    "đc": "được", "dc": "được", "ko": "không", "k": "không", "hok": "không",
    "hong": "không", "ms": "mới", "bh": "bây giờ", "bjo": "bây giờ",
    "nma": "nhưng mà", "vs": "với", "r": "rồi", "lun": "luôn", "z": "vậy",
    "j": "gì", "ny": "người yêu", "bsi": "bác sĩ", "cmt": "bình luận",
    "tym": "tim", "sori": "xin lỗi", "qtam": "quan tâm", "bít": "biết",
    "mn": "mọi người", "vk": "vợ", "ck": "chồng", "vc": "vãi", "tui": "tôi",
}

# Từ tiếng Anh hay gãy khi đọc — dịch theo nghĩa phổ biến trong câu; tên riêng
# (Love Story, Ronaldo…) KHÔNG nằm trong bảng này nên được giữ nguyên.
_ENGLISH = {
    "instrumental": "nhạc không lời", "sample": "nhạc mẫu", "replay": "bật lại",
    "intro": "đoạn mở đầu", "flex": "khoe", "lmao": "", "lol": "",
    "omg": "trời ơi",
}


# Trần độ dài một nhịp tính bằng ÂM TIẾT, không bằng số từ: "Rốc-ke-phe-lơ" là 4 âm
# tiết nhưng chỉ 1 từ, còn "1929" là 1 từ mà phải đọc tới 6-7 âm tiết.
BEAT_SYLLABLE_BUDGET = 24
_DIGIT_SYLLABLES = {1: 1, 2: 3, 3: 4, 4: 6}

# --- gate mạch kể (chỉ cảnh báo, không chặn dựng) -------------------------------
_ANCHOR_WINDOW = 2   # đại từ phải tìm được tên riêng trong số nhịp này
_SUBJECT_PRONOUNS = {"nó", "ông", "bà", "họ", "anh", "chị", "cô", "cậu"}
# Chỉ tính cụm chỉ định đứng ĐẦU nhịp: "triển lãm đó" đã tự gọi tên đối tượng.
# "vậy" không nằm ở đây vì "Vậy mà…" là từ nối đối lập, còn "như vậy" đã bị bắt ở nhịp dài.
_DEMONSTRATIVES = {"đó", "này", "kia", "ấy", "nọ"}
# Từ mở đầu nhịp không dấu ở tiếng Việt — viết hoa đầu câu nhưng không phải tên riêng.
_HEAD_STOP = {"trong", "ngoai", "sau", "truoc", "khi", "hai", "ba", "bon", "nam",
              "con", "co", "khong", "lai", "thi", "gian", "nhu", "lam", "loi"}
_ASCII_ONLY = set("abcdefghijklmnopqrstuvwxyz")

# --- cổng mềm về giọng kể và cỡ nhịp (cảnh báo, không bao giờ chặn bàn giao) -----
# Lời đọc phải là giọng nói. Những chữ này thuộc văn viết — người kể thật không dùng.
_WRITTEN_STYLE = ("được điều đi", "tiến hành", "nhằm", "tuy nhiên", "do đó",
                  "đáng chú ý là", "cụ thể là")
# Giọng TTS phẳng: cảm xúc phải nằm trong dữ kiện, không trong lời bình luận.
# Chỉ chặn CỤM — "sự thật", "chân thật" là danh/từ tính từ hợp lệ, không phải cảm thán.
_EMOTIONAL_STYLE = ("thật bất ngờ", "thật kinh ngạc", "thật khó tin", "thật trớ trêu",
                    "thật vô lý", "thật đáng tiếc", "quả là", "kinh ngạc",
                    "không thể tin", "đáng ngạc nhiên", "nghe vô lý", "vô lý thay")
# Mở màn bằng mốc thời gian là lối bản tin: hook mất cặp NEO + LỆCH nên không còn tò mò.
_DATE_OPEN = re.compile(r"^(?:vào\s+)?(năm|ngày)\s+\d")
_PUNCH_MAX_WORDS = 6   # nhịp ≤ số từ này là "cú đấm"; cả bài không có cú đấm nào là nhịp đều
_UNIFORM_RUN = 4       # số nhịp liên tiếp cùng độ dài thì báo
_UNIFORM_TOLERANCE = 2
_NUMBER_RUN = re.compile(r"\d+")   # cặp số đối chiếu: "10.000 viên : 986 con"
_EMPHASIS = re.compile(r"\*[^*]+\*")   # một cặp * * = một lần nổ chữ to
# Chọn chữ nổ: mỗi câu 1–2 cụm, câu dài (≥ 3/4 ngân sách âm tiết) được 3. Câu chuyển
# tiếp không có cụm nào cũng đúng nên chỉ báo khi vượt trần, không báo khi thiếu.
_EMPHASIS_MAX = 2
_EMPHASIS_MAX_LONG = 3
_LONG_BEAT_SYLLABLES = BEAT_SYLLABLE_BUDGET * 3 // 4
# Bộ dựng cắt mỗi cụm thành 2 hàng tại từ *nhấn mạnh* đầu tiên. Hai hàng lệch nhau
# quá 1 từ thì hàng côi chữ nhìn như bị rơi (CHO / 100 TẤN DẦU).
_ROW_BALANCE_MAX = 1
_CHUNK_MAX_WORDS = 4   # khớp Options.max_words mặc định của bộ dựng
# "Ngày 7 tháng 11" (mốc chấm) đứng cùng nhịp với "100 tấn một ngày" (mức mỗi ngày)
# thì người nghe gộp thành "ngày đó cho 100 tấn" thay vì "mỗi ngày 100 tấn".
_POINT_DATE = re.compile(r"(?:^|[,.;:]\s)(?:vào\s+)?ngày\s+\d+", re.I)
_PER_DAY_RATE = re.compile(r"\b\d[\d.]*\s+(?:\S+\s+){0,2}(?:một|mỗi)\s+(ngày|tuần|tháng|năm|giờ)\b", re.I)


def _tokens(text: str) -> list[str]:
    return [t for t in (w.strip(".,!?;:…\"'()“”‘’") for w in text.split()) if t]


def _is_name(tok: str, at_head: bool) -> bool:
    if not tok[:1].isupper() or tok[:1].isdigit():
        return False
    low = tok.lower()
    if at_head:
        # Tên riêng nước ngoài thường không dấu ("Laika", "Anna"); từ Việt mở đầu câu
        # gần như luôn có dấu nên chỉ trường hợp không dấu mới cần loại theo danh sách.
        return all(c in _ASCII_ONLY for c in low) and low not in _HEAD_STOP
    return True


def _has_proper_name(tokens: list[str]) -> bool:
    """Có tên riêng trong nhịp: từ viết hoa giữa câu, hoặc từ mở đầu không dấu lạ."""
    return any(_is_name(tok, i == 0) for i, tok in enumerate(tokens))


def _display_chunks(disp: str, content: str = ""):
    """(items, chunks) đúng như bộ dựng cắt; chunks=None nếu bộ dựng bó tay.

    Truyền `content` để đọc cả tên riêng lẫn từ ghép riêng của nội dung — thiếu
    tham số này là cảnh báo đo trên một cách cắt khác với chữ thật lên hình.
    """
    from . import pipeline as pl

    items = pl.parse_emph(" ".join(disp.upper().split()))
    names = tuple(pl.load_names(content) or ()) if content else ()
    try:
        chunks = pl.split_items(items, _CHUNK_MAX_WORDS,
                                pl._name_spans(items, names), content=content)
    except ValueError:
        return items, None
    return items, chunks


def _tier_rows(chunks: list[list]) -> list[tuple[list[str], list[str]]]:
    """Cặp (hàng trên, hàng dưới) của mọi cụm mà bộ dựng sẽ cắt làm hai hàng."""
    from . import pipeline as pl

    rows = []
    for chunk in chunks:
        runs = pl._tier_groups(chunk)
        if len(runs) == 2 and runs[0][0]:
            up, dn = runs[0][1], runs[1][1]
        else:
            cut = next((i for i, (_, e) in enumerate(chunk) if e), len(chunk))
            up, dn = chunk[:cut], chunk[cut:]
        if up and dn:
            rows.append(([w for w, _ in up], [w for w, _ in dn]))
    return rows


def _chunk_warnings(index, items, chunks, content: str = "") -> list[str]:
    """Cụm chữ hiển thị cắt hỏng: cắt giữa từ ghép, còn đúng 1 từ, kết thúc bằng hư từ.

    Đo trên chính các cụm bộ dựng tạo ra, nên cảnh báo ở đây là thứ người xem thật
    sự đọc trên hình. Bộ chia cụm đã tránh ba lỗi này khi còn đường chia khác; cảnh
    báo nổ đúng lúc nó phải phá luật (nhịp tên riêng, câu không có dấu câu).
    """
    from . import pipeline as pl, wordseg

    warns: list[str] = []
    blocked = wordseg.boundaries([w for w, _ in items], content)
    pos = 0
    for chunk in chunks[:-1]:
        pos += len(chunk)
        # Dấu câu là ranh giới người viết đặt sẵn: cắt ở đó luôn đúng.
        if pos in blocked and not pl._is_break(items[pos - 1][0]):
            warns.append(f'nhịp {index}: cụm cắt giữa từ ghép '
                         f'"{items[pos - 1][0]} {items[pos][0]}"')
    named = {i for start, end in pl._name_spans(items, tuple(pl.load_names(content) or ())
                                                if content else ())
             for i in range(start, end)}
    pos = 0
    for chunk in chunks:
        end = pos + len(chunk)
        if (len(chunk) == 1 and pos not in named
                and not (pl._is_connector(chunk[0][0]) and end in named)):
            warns.append(f'nhịp {index}: cụm chỉ 1 từ "{chunk[0][0]}" — '
                         "viết lại câu cho cụm dài hơn hoặc thêm dấu câu")
        elif (len(chunk) > 1 and end < len(items)
              and pl._is_glue(chunk[-1][0]) and not pl._is_break(chunk[-1][0])):
            warns.append(f'nhịp {index}: cụm kết thúc bằng hư từ '
                         f'"{chunk[-1][0]}" — hư từ phải dính với từ theo sau')
        pos = end
    return warns


def _is_card_script(rows) -> bool:
    """Bài Threads để trống chữ hiển thị (`|| -`). Lời đọc là nguyên văn của người khác
    nên không xét mạch kể — chỉ sửa được cách đọc TTS."""
    return all(str(r[2] or "").strip() in ("", "-") for r in rows if len(r) > 2)


def _is_label_row(row) -> bool:
    """Beat kể có nhãn: chữ hiển thị 3–5 từ và ngắn hơn hẳn lời đọc."""
    if len(row) < 3:
        return False
    disp = " ".join(str(row[2] or "").split())
    spoken = " ".join(str(row[1] or "").split())
    if not disp or disp == "-" or not spoken:
        return False
    n_disp = len(disp.replace("*", "").split())
    return 3 <= n_disp <= 5 and n_disp < len(spoken.split())


def _label_script(rows) -> bool:
    rows = [r for r in rows or [] if len(r) > 2 and str(r[1] or "").strip()]
    return bool(rows) and sum(1 for r in rows if _is_label_row(r)) * 2 >= len(rows)


def _beats(rows) -> list[tuple[int, str, list[str]]]:
    """(số nhịp, lời đọc, token) cho mọi nhịp có lời."""
    beats = []
    for r in rows or []:
        if len(r) < 2:
            continue
        text = " ".join(str(r[1] or "").split())
        if text:
            beats.append((r[0], text, _tokens(text)))
    return beats


def narrative_warnings(rows) -> list[str]:
    """Đại từ/cụm chỉ định treo: nhịp trỏ về thứ không có tên riêng nào đứng gần."""
    beats = _beats(rows)
    if len(beats) < 3 or _is_card_script(rows):
        return []
    warns: list[str] = []
    for pos, (idx, _, tokens) in enumerate(beats):
        window = beats[max(0, pos - _ANCHOR_WINDOW):pos + 1]
        if any(_has_proper_name(tk) for _, _, tk in window):
            continue
        loose = [t.lower() for t in tokens[:1] if t.lower() in _DEMONSTRATIVES]
        loose += [t.lower() for t in tokens if t.lower() in _SUBJECT_PRONOUNS]
        if loose:
            warns.append(
                f"nhịp {idx}: '{loose[0]}' trỏ về thứ không có tên riêng nào trong "
                f"{_ANCHOR_WINDOW} nhịp trước — gọi lại tên hoặc thêm nhịp giới thiệu"
            )
    return warns


def rhythm_warnings(rows) -> list[str]:
    """Giọng kể và cỡ nhịp: chữ văn viết, lời bình luận cảm xúc, mốc thời gian mở màn,
    nhịp đều tăm tắp, thiếu cặp số đối chiếu."""
    beats = _beats(rows)
    if len(beats) < 3 or _is_card_script(rows):
        return []
    label_mode = _label_script(rows)
    warns: list[str] = []

    for idx, text, _ in beats:
        low = text.lower()
        stiff = [p for p in _WRITTEN_STYLE if p in low]
        if stiff:
            warns.append(f"nhịp {idx} dùng chữ văn viết: {', '.join(stiff)} — viết lại như đang nói chuyện")
        hot = [p for p in _EMOTIONAL_STYLE if p in low]
        hot = [p for p in hot if not any(p != q and p in q for q in hot)]
        if hot:
            warns.append(
                f"nhịp {idx} bình luận cảm xúc: {', '.join(hot)} — đặt hai dữ kiện cạnh nhau "
                "để sự lệch tự lộ, đừng nói cho người xem biết họ phải cảm thấy gì"
            )

    first = beats[0][1]
    if _DATE_OPEN.match(first.lower()):
        warns.append(
            f"nhịp 1 mở bằng mốc thời gian ('{first.split()[0]} {first.split()[1]}') — "
            "hook cần cái quen + cái lệch; chỉ giữ nếu mốc đó chính là chi tiết lệch"
        )

    lengths = [len(tk) for _, _, tk in beats]
    # Beat kể 2–3 câu có nhãn: cỡ beat do câu chuyện quyết, không đo bằng nhịp phụ đề.
    if not label_mode:
        if not any(n <= _PUNCH_MAX_WORDS for n in lengths):
            warns.append(
                f"không nhịp nào ≤{_PUNCH_MAX_WORDS} từ — cả bài cùng cỡ, thiếu cú đấm ở điểm đảo chiều"
            )
        start = 0
        for pos in range(1, len(lengths) + 1):
            same = pos < len(lengths) and abs(lengths[pos] - lengths[pos - 1]) <= _UNIFORM_TOLERANCE
            if same:
                continue
            if pos - start >= _UNIFORM_RUN:
                warns.append(
                    f"nhịp {beats[start][0]}–{beats[pos - 1][0]}: {pos - start} nhịp liên tiếp cùng độ dài "
                    f"(±{_UNIFORM_TOLERANCE} từ) — nhịp dài để giải thích, nhịp ngắn để nhấn"
                )
            start = pos

    if not any(len(_NUMBER_RUN.findall(text)) >= 2 for _, text, _ in beats):
        warns.append(
            "không nhịp nào chứa hai con số — thiếu cặp số đối chiếu (\"mười viên đạn mới trúng một con\"); "
            "nguồn không có cặp số thì đổi góc, đừng lấp bằng tính từ"
        )
    return warns


def speech_syllables(text: str) -> int:
    """Ước lượng số âm tiết TTS phải đọc: tách gạch nối, bành trướng chữ số."""
    total = 0
    for token in re.split(r"[\s\-–—]+", text.strip()):
        token = token.strip(".,!?;:…\"'()“”")
        if not token:
            continue
        num = re.fullmatch(r"(\d+)(?:[.,](\d+))?", token)
        if num:
            total += _DIGIT_SYLLABLES.get(len(num.group(1)), len(num.group(1)) + 2)
            if num.group(2):
                total += 1 + len(num.group(2))  # "phẩy" + từng chữ số thập phân
        else:
            total += 1
    return total


def load_glossary(path=GLOSSARY_FILE) -> dict:
    """Glossary người dùng đã dạy (cặp 'viết tắt/sai' -> 'đúng'), hỏng thì bỏ qua."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k).lower(): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def lint_rows(rows, content: str = "") -> list[str]:
    """Cảnh báo nhanh trên bảng nhịp: đại từ treo, giọng văn viết, cỡ nhịp, nhịp quá dài,
    quá nhiều cụm nhấn mạnh trong một nhịp, hai hàng chữ lệch nhau, mốc ngày đè mức mỗi ngày,
    cụm chữ hiển thị cắt hỏng, viết tắt sót trong glossary. Mọi mục đều là cảnh báo —
    người viết quyết, không chặn dựng.

    `content` là tên thư mục minh họa: cần để đọc tên riêng + `tu-ghep.txt` riêng của
    nội dung, nhờ vậy cảnh báo đo đúng cách cắt của bộ dựng.
    """
    keys = {k for k in (set(_TEENCODE) | set(_ENGLISH) | set(load_glossary())) if len(k) >= 2}
    warnings: list[str] = narrative_warnings(rows) + rhythm_warnings(rows)
    # Bài Threads giữ nguyên văn lời người khác nên không sửa được bố cục chữ hiển thị.
    card = _is_card_script(rows)
    for r in rows or []:
        if len(r) < 2:
            continue
        spoken = " ".join(str(r[1] or "").split())
        if not spoken:
            continue
        index = r[0]
        words = spoken.split()
        disp = " ".join(str(r[2] or "").split()) if len(r) > 2 else ""
        syl = speech_syllables(spoken)
        spans = _EMPHASIS.findall(disp)
        limit = _EMPHASIS_MAX_LONG if syl >= _LONG_BEAT_SYLLABLES else _EMPHASIS_MAX
        if len(spans) > limit:
            warnings.append(
                f"nhịp {index} có {len(spans)} cụm nhấn mạnh ({', '.join(s.strip('*') for s in spans)}) "
                f"— trần là {limit} với nhịp {syl} âm tiết; giữ cụm mang chỗ lệch mới nhất, "
                "các cụm còn lại để bậc nhỏ"
            )
        if syl > BEAT_SYLLABLE_BUDGET and not _is_label_row(r):
            warnings.append(f"nhịp {index} quá dài ({syl} âm tiết, nên ≤ {BEAT_SYLLABLE_BUDGET})")
        if disp and not card and _POINT_DATE.search(spoken) and _PER_DAY_RATE.search(spoken):
            warnings.append(
                f"nhịp {index} có cả mốc ngày và mức mỗi ngày — người nghe đọc số thành "
                f"tổng của riêng ngày đó; mở mốc bằng \"Từ/Sau\" hoặc dời mốc sang nhịp khác"
            )
        items = chunks = None
        if disp and not card:
            items, chunks = _display_chunks(disp, content)
            if chunks is None:
                warnings.append(f"nhịp {index}: không chia được cụm 2–{_CHUNK_MAX_WORDS} từ "
                                f"cho \"{disp}\" — ngắt bớt bằng dấu câu")
        if chunks:
            warnings.extend(_chunk_warnings(index, items, chunks, content))
        for up, dn in ([] if not chunks else _tier_rows(chunks)):
            if abs(len(up) - len(dn)) > _ROW_BALANCE_MAX:
                warnings.append(
                    f"nhịp {index}: hàng trên {len(up)} từ ({' '.join(up)}), hàng dưới "
                    f"{len(dn)} từ ({' '.join(dn)}) — hai bậc lệch quá {_ROW_BALANCE_MAX} từ; "
                    "viết lại cho hai hàng gần bằng nhau hoặc bọc trọn cụm bằng *...* để nổ một hàng"
                )
        leftover = sorted({w.strip(".,!?;:…\"'()").lower() for w in words} & keys)
        if leftover:
            warnings.append(f"nhịp {index} còn viết tắt: {', '.join(leftover)}")
    return warnings[:20]
