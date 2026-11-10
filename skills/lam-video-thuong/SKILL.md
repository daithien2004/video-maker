---
name: lam-video-thuong
description: Flow "Làm video" cho video ngắn kiến thức (không phải Threads): người dùng ra lệnh một lần → AI tự chọn đề tài, viết kịch bản ngắn, tải ảnh thật từ Wikimedia Commons, dựng preview và tự kiểm. Cũng dùng khi người dùng đưa kịch bản/đề tài thô để làm video.
---

# Làm video thường — một lệnh, tới preview

Người dùng chỉ nói **"Làm video"** (kèm đề tài, hoặc để AI tự chọn). AI làm trọn các bước dưới đây rồi **dừng ở preview**;
chỉ xuất mp4 hoặc đăng bài khi người dùng bảo. Video Threads không dùng skill này (xem `skills/lam-video-threads/SKILL.md`).

## Video mẫu (đích cần đạt)

Video **khoảng 1 phút (55–75 giây), 240–300 từ** (đo thực tế ~4,3 từ/giây), **một chuỗi nhân quả liền mạch người nghe hiểu ngay
lần đầu**, giọng trung tính như người chia sẻ kiến thức, hình thật đổi mỗi 3–4 giây, phụ đề 2–4 từ có chữ nhấn,
kết bằng câu giải thích cuối. Video 30 giây là **quá ngắn**: thiếu bối cảnh nên người xem không hiểu. Mẫu dựng/nhịp: `assets/references/`.

## Phần dựng đã làm sẵn — KHÔNG chỉnh trừ khi người dùng yêu cầu

Mascot trồi lên từ đầu và trượt xuống ở cuối; chỉ ảnh đầu có tiếng pop, các ảnh sau chuyển im lặng; phụ đề ngắn bám lời đọc
(căn mốc theo giọng thật) có chữ nhấn; giọng **mặc định** của VieNeu (`"voice": ""` trong `config/settings.json`, không clone); tốc độ đọc **1,2** (đọc ở 1,0 người dùng chê quá chậm; câu nghỉ theo dấu câu, `CLAUSE_*` ở `videomaker/pipeline.py`).
`config/settings.json` bị git bỏ qua nên **kiểm trước khi dựng**: `"voice": ""` (không clone) và `"speed": 1.2`; lệnh dựng bên dưới đã kèm
`--speed 1.2`. Giọng mặc định không bị ép tốc độ từng câu (co giãn `atempo` làm tiếng vỡ, chỉ dùng cho giọng clone).
Không tự đổi giọng, tốc độ, nghỉ, cỡ chữ.

## Quy trình

### 1. Đề tài và dữ kiện
- Người dùng nêu đề tài thì dùng; không thì chọn sự kiện từ Wikipedia On This Day (`/feed/v1/wikipedia/en/onthisday/events/{MM}/{DD}`),
  ưu tiên **sự kiện có ảnh thật** và có chuỗi nhân quả rõ. **Bỏ qua** chiến tranh/chính trị Việt Nam gây tranh cãi, thảm họa, thương vong.
- Đọc ít nhất một bài đầy đủ (không chỉ dòng tóm tắt). Ghi `assets/illus/<noi-dung>/SOURCES.txt`: dữ kiện → nguồn. **Mọi câu trong
  kịch bản phải có căn cứ trong nguồn**; không bịa số, mốc, nguyên nhân. Nguồn nói không chắc thì nói thận trọng hoặc bỏ.
- `<noi-dung>` là tên thư mục dạng `ten-su-kien-nam` (không dấu).
- **Không ghi đè kịch bản có sẵn.** `assets/illus/` nằm ngoài git nên ghi đè là mất vĩnh viễn. "Kịch bản mới nhất / video vừa làm" =
  thư mục `assets/illus/` hoặc `output/kienthuc/` sửa gần nhất (`ls -t`); không chắc thì hỏi người dùng tên nội dung trước khi sửa.

### 2. Viết kịch bản (`assets/illus/<noi-dung>/kich-ban.txt`)
Mỗi dòng một nhịp: `[the] lời đọc, có *chữ nhấn*`. **Không dùng `||`** (làm lệch phụ đề). `[the]` = tên thư mục ảnh của nhịp.
- **12–20 nhịp, 240–300 từ (~1 phút).** Mỗi nhịp 1–3 câu, mỗi câu một ý, ≤15 từ. Câu ngắn xen câu vừa. Dài phải do **thêm hiểu biết**,
  không do kéo dài: giải thích bối cảnh (ai, ở đâu, lúc nào), thuật ngữ lần đầu xuất hiện (nói một câu nó là gì), và **từng bước** của
  chuỗi nguyên nhân. Mỗi bước nhân quả một nhịp; không nhảy từ A sang C. Người chưa biết gì về đề tài nghe một lần phải hiểu.
- **Ngắt nghỉ = dấu phẩy. Viết theo nhóm hơi (breath group).** Giọng nghỉ ở dấu phẩy/chấm và phụ đề cũng cắt ở đúng đó, nên:
  mỗi đoạn giữa hai dấu câu **4–8 tiếng** (tối đa 10 nếu có số/tên; "từ" trong máy kiểm = tiếng/âm tiết, phụ đề chia 4 tiếng một dòng). Câu 15 tiếng thường có 1–2 dấu phẩy chia theo nghĩa. Câu dài không phẩy
  thì giọng đọc một hơi và phụ đề bị cắt máy móc giữa cụm ("bằng sáng | chế cho cái").
  - Phẩy **sau** trạng ngữ mở đầu ("Năm 1930,", "Ngay từ lúc dựng,"), **trước** từ nối ("…, nhưng …", "…, nên …", "…, vì …"),
    giữa hai vế song song, sau chủ ngữ dài.
  - **Không** phẩy giữa chủ–vị ngắn, trong cụm danh từ/tên riêng/số–đơn vị ("45 bằng sáng chế", "9 giờ 45"), giữa động từ và tân ngữ.
  - Chỗ đảo chiều/quan trọng dùng **câu riêng ngắn** (dấu chấm = nghỉ dài nhất), không dùng dấu hai chấm nối dài.
  - **Không thêm dấu phẩy chỉ để hết LƯU Ý** — dấu phẩy sai chỗ (giữa động từ và tân ngữ) làm giọng nghỉ sai, tệ hơn câu dài. Soát: đọc to; chỗ nào mình không ngừng thở thì không đặt phẩy; chỗ nào hụt hơi thì thiếu phẩy.
- **Hook = câu kể tự nhiên, đủ chủ ngữ vị ngữ, 15–25 từ**, nêu chủ thể bằng danh từ chung, đặt **cái quen cạnh chỗ lệch**
  (số lớn đối với kết quả ngược kỳ vọng, nguyên nhân nhỏ đối với hệ quả lớn). Không lộ lời giải, không tiêu đề báo.
  Câu hỏi "Tại sao…?" chỉ là một cách, không bắt buộc.
- **Mạch:** hook → trả lời ngay ("Thật ra…") → chuỗi nguyên nhân–kết quả có từ nối ("Nhưng", "Vấn đề là", "Chính vì thế") →
  **câu kết khép lại ý chính và nhắc lại hook**. Cần ≥2 chỗ "Nhưng" và một nhịp 1 câu ngắn ở chỗ đảo chiều. Không kết bằng câu hỏi mở,
  không kêu gọi. **Câu cuối phải nghe như dấu chấm hết:** một câu ngắn, chốt đúng cái hook đã hỏi, không thêm mệnh đề phụ
  ("đúng lúc…", "và rồi…") và không nêu ý mới. **Mở câu kết bằng từ nối kết luận ("Vậy là…", "Tóm lại…") và giữ nguyên chủ đề
  của nhịp ngay trước**, không đổi chủ ngữ sang một đối tượng mới — đổi chủ ngữ làm người nghe tưởng sắp sang phần mới.
- **Giọng:** trung tính, rõ, chắc. Không cảm thán, không "thật bất ngờ/kinh ngạc", không văn viết ("tuy nhiên", "nhằm", "tiến hành").
  Sự lệch tự lộ bằng dữ kiện đặt cạnh nhau, không bằng tính từ. Câu nào bỏ đi không ai nhận ra thì xoá.
- **Chữ nhấn `*...*`:** **tối đa 1 cụm mỗi nhịp** (nhịp bình thường có thể không nhấn gì), 1–3 từ, nằm gọn trong một cụm phẩy.
  Nhấn đúng cái **mới hoặc gây lệch** của nhịp: con số bất ngờ, hành động then chốt, chỗ đảo chiều ("*thất bại*", "*45 bằng sáng chế*").
  **Không** nhấn: danh từ chủ đề đã nhắc nhiều lần (tên đề tài, "tủ lạnh" trong bài về tủ lạnh), từ phụ/loại từ ("cái", "của", "và"),
  từ chỉ để cuối câu cho có, hoặc cả hai chủ–vị. Nếu nhịp có 2 chỗ muốn nhấn, bỏ chỗ ít quan trọng hơn. Cụm nhấn không vắt qua dấu phẩy.
- **Số/ngày:** viết số bình thường ("9 tháng 11", "1989"); pipeline tự đọc ngày tháng cho đúng.
- **Tên nước ngoài** TTS đọc sai: giữ tên gốc trong kịch bản và thêm một dòng `Tên = cách đọc` vào `assets/phat-am.txt`
  (mỗi tên một từ ↔ một từ). Tên riêng cần đứng thành một cụm chữ thì thêm vào `assets/illus/<noi-dung>/ten-rieng.txt`.
- Đọc lại cả bài từ đầu tới cuối: chỗ nào phải quay lại nhịp trước mới hiểu thì viết lại.

### 3. Ảnh thật — mỗi nhịp một ảnh, ảnh đầu = ảnh cuối
- Muốn ~1 phút cần 12–20 nhịp nên **cần 11–19 ảnh khác nhau**: tìm đủ ảnh *trước* khi chốt số nhịp (đề tài ít ảnh thì chọn đề tài khác, không nhồi nhịp). Cần **số ảnh khác nhau = số nhịp − 1** (nhịp đầu và nhịp cuối dùng **cùng một thẻ `[the]`**, tức cùng một ảnh). Không meme.
- Tìm: `python tools/tai_anh.py tim "<từ khóa tiếng Anh/Đức>" --n 8` → tải ứng viên vào `work/anh-ung-vien/…` kèm `sheet.png`.
  **PHẢI mở `sheet.png` và nhìn từng ảnh** trước khi chọn: ảnh phải thể hiện đúng cảnh câu đó đang nói (người, vật, địa điểm, thời kỳ).
  Không gán ảnh theo tên file hay mô tả của trang nguồn.
- Chọn: `python tools/tai_anh.py chon <noi-dung> <the> <file-ung-vien>` → chép vào `assets/illus/<noi-dung>/<the>/` và ghi nguồn + giấy phép vào `SOURCES.txt`.
- Không tìm được ảnh đúng cảnh thì **đổi câu hoặc đổi đề tài**, không gán ảnh sai cho đủ. Ảnh CC BY / CC BY-SA cần ghi tác giả khi đăng
  (đã có trong `SOURCES.txt`).
- Thư viện cũ trong `assets/illus/` có thể dùng lại nếu đúng đề tài, nhưng vẫn phải xem ảnh thật (nhiều ảnh đặt tên sai nội dung).

### 4. Dựng preview
```bash
.venv\Scripts\python.exe tools/render_script.py assets/illus/<noi-dung>/kich-ban.txt --content <noi-dung> --preview --speed 1.2
```
Không chạy `lint_rows` và không sửa câu chỉ để hết cảnh báo (`--lint` chỉ để tra cứu).

### 5. Tự kiểm — bắt buộc trước khi báo người dùng
```bash
.venv\Scripts\python.exe tools/kiem_video.py assets/illus/<noi-dung>/kich-ban.txt --content <noi-dung>
```
Kiểm: mọi nhịp có ảnh và ảnh tồn tại, không ảnh lặp ở giữa, ảnh đầu = ảnh cuối, không phụ đề nào gần như không hiện, độ dài 50–80 giây,
235–320 từ, 12–22 nhịp, và soi ngắt nghỉ/nhấn (đoạn >10 tiếng không phẩy, nhấn quá nhiều hoặc vào từ phụ, phụ đề cắt giữa cụm nhấn hoặc kết bằng từ nối).
Các **LƯU Ý** về ngắt nghỉ/nhấn cũng phải sửa trong kịch bản (thêm/bớt phẩy, bỏ nhấn) rồi dựng và kiểm lại, không bỏ qua. Có **LỖI** thì sửa (đổi ảnh, rút kịch bản…) rồi dựng và kiểm lại; chỉ báo người dùng khi **ĐẠT** hoặc nói rõ lỗi còn lại.

### 6. Bàn giao
Báo: đường dẫn preview, kết quả kiểm, đề tài + nguồn, danh sách ảnh (tác giả/giấy phép nếu cần ghi), những gì chưa chắc.
**Không tự xuất mp4 hoặc đăng.** Người dùng nói "xuất"/"đăng" mới làm.

## Khi người dùng đưa kịch bản hoặc đoạn văn thô
Giữ nguyên dữ kiện, viết lại theo mục 2 (đủ dài ~1 phút, nhóm hơi có phẩy, nhấn đúng chỗ), rồi làm tiếp từ bước 3. Hỏi lại chỉ khi thiếu dữ kiện
để hoàn thành chuỗi nhân quả.
