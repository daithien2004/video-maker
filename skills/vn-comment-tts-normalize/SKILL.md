---
name: vn-comment-tts-normalize
description: Chuyển bản thô (raw) các comment/bài đăng mạng xã hội tiếng Việt sang bản đã chỉnh để đọc thành tiếng / làm voice-over / làm video (TTS). Converts raw Vietnamese social-media comment transcripts (lines like "# post/04-cmt-xxx.png (comment 3 · @user · 135 like)" followed by text lines ending with "|| -") into a clean, speakable version - expands slang and abbreviations phonetically (vcl → vờ cờ lờ, cmt → còm men, k → không), strips emoji, replaces laughter/emoji-only comments with [sound], leaves image comments untouched (the app auto-zooms those beats), removes off-topic or sensitive comment threads, and re-wraps lines. Use whenever the user pastes a raw comment dump in this format, or says "bản thô", "bản đã chỉnh", "chỉnh sửa comment", "viết lại để đọc", "làm script đọc comment", even if they don't mention TTS.
---

# Chuẩn hóa comment tiếng Việt để đọc thành tiếng

Biến **bản thô** (copy từ ảnh chụp/OCR comment) thành **bản đã chỉnh**: người đọc/giọng TTS đọc trơn tru, không vấp teencode, không đọc emoji, không đọc nội dung nhạy cảm.

## Định dạng đầu vào / đầu ra (giữ nguyên)

```
# post/<số>-<loại>-<user>.png   (<nhãn> · @user · <N> like)
<dòng văn bản> || -
<dòng văn bản> || -
```

- **Giữ nguyên dòng tiêu đề `#`** (tên file, nhãn comment, số like, thứ tự số comment gốc). Không đánh số lại khi xóa comment — để số nhảy cóc.
- Mỗi dòng văn bản kết thúc bằng ` || -`.
- Cách nhau một dòng trống giữa các comment.

## Quy trình

Làm lần lượt 5 bước:

### 1. Lọc comment (xóa cả khối: tiêu đề + nội dung)
Xóa hẳn comment nếu:
- **Lạc đề / không liên quan** mạch hài của bài (vd. "liên quan ?").
- **Cãi nhau chính trị trực diện, nhắc đảng/nhà nước/an ninh mạng/dư luận viên/biểu tình**, hoặc chuỗi reply tranh cãi, chửi bới qua lại giữa hai người. Xóa **cả chuỗi** (comment gốc + mọi reply).
- Nội dung có thể gây rủi ro pháp lý/nền tảng nếu đọc thành tiếng.

Nếu không chắc một comment có thuộc nhóm này không → **giữ lại và hỏi người dùng ở cuối**, không tự quyết.

### 2. Comment không có chữ
- Comment chỉ có emoji/cười (`:)))`, `🤣🤣`, `😂`) hoặc **không có văn bản** (ảnh/sticker/GIF, ô trống) → thay bằng một dòng `[sound] || -`.
- Comment **có chữ và có ảnh đính kèm** → giữ chữ như bình thường, **không** thêm dòng `[zoom]`; app tự thêm một nhịp zoom (kèm nhạc) ở cuối mục đó — bài gốc có ảnh cũng vậy — người dùng tắt/bật hoặc xoá nhịp đó trong bảng nhịp.
- Comment có chữ **và** emoji → bỏ emoji, giữ chữ (xem bước 4). Nếu chữ chỉ là phần râu ria của emoji (vd. "🤣" kẹp cuối lời đã đủ nghĩa) thì chỉ bỏ emoji.

### 3. Đọc-hóa viết tắt / teencode (thay theo bảng dưới)
Giữ **hoa/thường** như gốc (`Đcu` → `Đờ mờ`, `M ơi` → `Mày ơi`, `m ơi` → `mày ơi`). Chỉ thay khi đó là **từ nguyên vẹn** (không thay `k` bên trong từ khác).

| Gốc | Chỉnh thành |
|---|---|
| đcu, đcm | đờ mờ |
| vcl, vl | vờ cờ lờ / vờ lờ (xem ghi chú) |
| cmay, cm | chúng mày |
| cmt | còm men |
| ig | i gờ |
| wtf | oát đờ phắc |
| k, ko, hok | không |
| đ (đứng riêng, phủ định) | đếch |
| vs | với |
| r (đứng riêng, sau "rồi") / "đcđ r" | rồi / "được rồi" |
| v (đứng riêng, cảm thán) | vãi (không phải "vậy") |
| t, tao viết tắt (đại từ) | tao |
| m, mày viết tắt (đại từ) | mày |
| tk | thằng |
| nv | nhân vật |
| TQ | Trung Quốc |
| VPN | vi pi ên |
| M3P | em báp pê (Mbappé) |
| Mbappe, Mbappé, Mpabbe (gõ sai) | em báp pê |

Ghi chú:
- `vcl` → **vờ cờ lờ**; `vl` → **vờ lờ**; `vl ra` → `vờ lờ ra`. Giữ nguyên số chữ cái được đọc.
- `t`/`m` chỉ đổi khi rõ là đại từ ("t khốn nạn quá" → "tao khốn nạn quá", "anh t" → "anh tao", "M ơi" → "Mày ơi"). Ngữ cảnh mơ hồ thì để nguyên và hỏi.
- **Không đụng** vào từ vẫn đọc được tự nhiên: `í`, `chả`, `thằng pê`, `cha pê`, `Pe`, `fan trung`, `bọn nó`, `đc` (xem Điểm cần chốt).
- Tên đầy đủ `Mbappe`/`Mbappé` (kể cả gõ sai `Mpabbe`) → **em báp pê**. Cách gọi ngắn `pê`, `Pe`, `thằng pê`, `cha pê` giữ nguyên vì người đọc đã quen.

### 4. Làm sạch ký tự
- Xóa toàn bộ emoji và emoticon (`🤣 😂 🙃 😕 😭 😃 :)))`, `:\u{2060}-\u{2060})`).
- Sửa khoảng trắng: bỏ khoảng trắng thừa trước dấu câu (`pê . Wtf` → `pê. oát đờ phắc`), thêm khoảng trắng sau dấu câu, bỏ dấu `…`/`.` / `,` thừa ở cuối dòng nếu là dấu cuối comment (`đọc k ngậm đc mồm🤣` → không dấu).
- Giữ nguyên dấu phẩy ngắt nhịp giữa câu.
- Giữ nguyên số like, tên user, nội dung ý nghĩa; **không** viết lại câu, không sửa chính tả ngoài bảng trên, không "làm đẹp" văn phong.

### 5. Ngắt dòng lại
Xuống dòng theo **nhịp đọc** (cuối cụm/câu), không theo độ rộng ảnh gốc. Dòng gốc bị cắt giữa cụm (`nhà độc ‖ tài`) → nối lại, rồi ngắt ở chỗ hợp lý:

```
Thì cha pê lỡ mồm chả bảo quả ảnh ghép với nhà độc tài là hài nhất || -
nên chả bị bọn trung quốc nó chửi || -
```

Mỗi dòng ≲ 70–80 ký tự; ưu tiên ngắt trước "nên / xong / nhưng / mà / vì".

## Ví dụ ngắn

Thô:
```
# post/04-cmt-ca-khong-biet-boi-.png   (comment 3 · @ca.khong.biet.boi.199 · 135 like)
mình lên ig đọc họ toàn trêu hài || -
vl ra đọc k ngậm đc mồm🤣 || -
```
Chỉnh:
```
# post/04-cmt-ca-khong-biet-boi-.png   (comment 3 · @ca.khong.biet.boi.199 · 135 like)
mình lên i gờ đọc họ toàn trêu hài vờ lờ ra || -
đọc không ngậm đc mồm || -
```

Thô: `# post/02-cmt-hievelynz.png ... :))) || -` → Chỉnh: `[sound] || -`

## Điểm cần chốt với người dùng (hỏi 1 lần, rồi nhớ)

Bản mẫu có vài chỗ không nhất quán; hỏi hoặc ghi chú ở cuối câu trả lời, không tự quyết:

1. **`đc`**: bản mẫu để nguyên `đc` ở một số chỗ nhưng đổi `đcđ r` → `được rồi`. Mặc định: **để nguyên `đc`**, trừ khi người dùng muốn đổi thành `được`.
2. **`TQ`**: có chỗ thành `Trung Quốc`, có chỗ `trung quốc` (chữ thường). Mặc định: **`Trung Quốc` viết hoa**; còn `trung quốc` chữ thường nếu gốc đã viết thường.
3. **Ảnh đính kèm**: không đánh dấu trong kịch bản — app tự thêm một nhịp zoom ở cuối mục có ảnh. Chỉ ghi chú ở "Cần bạn xác nhận" khi không chắc mục đó có ảnh hay không.

## Đầu ra cuối cùng

1. Bản đã chỉnh (khối code, đúng định dạng đầu vào).
2. Một danh sách ngắn **"Đã xóa"** (file + lý do một cụm) và **"Cần bạn xác nhận"** (các điểm mơ hồ). Không lặp lại toàn bộ bản thô.
