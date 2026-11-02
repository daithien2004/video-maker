---
name: lam-video
description: Flow "Làm video": từ sự kiện trong ngày (Wikipedia On This Day) tự tìm ảnh, viết kịch bản 16–18 nhịp và dựng video thường tự động. Dùng khi người dùng ra lệnh "Làm video".
---

# SKILL: Làm video (tự động)

## Mục tiêu
Nhận lệnh "Làm video" → chọn sự kiện trong ngày → tự tìm ảnh → viết kịch bản **16–18 nhịp** (mỗi nhịp một ảnh riêng) → dựng mp4, không cần người dùng đưa văn bản hay chọn ảnh.

## Nguồn dữ liệu
- **Sự kiện**: Wikipedia On This Day (`/feed/v1/wikipedia/en/onthisday/events/{MM}/{DD}`), miễn phí, không cần key. Bản tiếng Việt trả 404 → lấy bản tiếng Anh rồi Việt hóa tên riêng.
- **Ảnh**: Wikimedia Commons / Smithsonian / LoC / Europeana (public domain / CC0). Pexels không phù hợp cho ảnh lịch sử; chỉ dùng để lấy không khí (trời, đám đông, đường phố).

## Chọn sự kiện
- Ưu tiên sự kiện **có ảnh khả dụng** + **liên quan Việt Nam**.
- Không lấy sự kiện đầu danh sách nếu thiếu ảnh.
- Mỗi cảnh bám đúng 1 câu có trong bài gốc, không tự suy diễn số/mốc/động cơ, nguyên
  nhân, kết quả hoặc quan hệ nhân–quả. Không thêm chi tiết để lấp khoảng trống giữa
  các câu; câu nối chỉ được sắp xếp và diễn đạt lại dữ kiện đã có. Nếu bài gốc không
  đủ căn cứ, bỏ chi tiết đó hoặc dùng cách nói thận trọng, không biến suy đoán thành
  sự thật.
- **Bỏ qua chủ đề nhạy cảm**: không chọn sự kiện chiến tranh Việt Nam, lịch sử chính trị Việt Nam gây tranh cãi, thảm hoạ/thương vong/tang tóc. Chọn sự kiện khác trong danh sách thay vì cố xử lý.

## Viết kịch bản (video thường)
- Format: `[tag] lời đọc || CHỮ HIỂN THỊ`.
- Mỗi nhịp chia thành **cụm ngắn 2–4 từ**, cách nhau bằng dấu phẩy; mỗi cụm = một lần hiển thị trên một dòng.
- Mỗi cụm phải **đủ nghĩa độc lập**, không mượn từ giữa các cụm.
- Từ/cụm nhấn mạnh bọc `*...*`; emphasis tô kiểu riêng tại chỗ.
- Lời đọc giữ dạng đầy đủ để TTS đọc đúng; chữ hiển thị có thể dùng dạng viết tắt (KM/H, %, …) theo ý người dùng.
- **Mỗi nhịp bắt buộc có ảnh riêng** (1 hình / 1 nhịp). Không để trống clip hay dùng `carry` để lặp ảnh qua nhiều nhịp chỉ nhằm tiết kiệm. `carry` chỉ dùng khi cần hiển thị nhiều cụm chữ của **cùng một nhịp**.
- **Cách gọi con vật**: dùng tên riêng, "nó" hoặc "chú chó/chú mèo…". Không dùng đại từ chỉ người ("cô", "anh", "chị", "ông") cho con vật.
- **Kết bài không được cụt**: nhịp cuối phải khép lại ý đã mở ở hook hoặc nêu bài học/ý nghĩa, không chỉ tả một vật thể rồi dừng. Trước đó có thể có một nhịp ý nghĩa; không thêm câu chào kết kiểu "cảm ơn đã xem".
- **Tên riêng phải đọc được bằng TTS**: nếu tên nước ngoài, thuật ngữ hoặc từ viết tắt
  khiến giọng đọc phát âm sai hoặc đánh vần máy móc, chỉ phiên âm trong lời đọc; chữ
  hiển thị giữ nguyên tên gốc để người xem nhận diện. Ví dụ: lời đọc `MÉT-SEN-GIƠ`,
  chữ hiển thị `MESSENGER`.
- **Mạch triển khai phải trọn ý**: với mỗi cụm thông tin, làm rõ chuyện gì xảy ra,
  vì sao hoặc bằng cách nào, rồi dẫn đến kết quả/ý nghĩa gì. Giữ rõ quan hệ trước–sau,
  nguyên nhân–kết quả và vấn đề–cách giải quyết; không ghép các câu đúng riêng lẻ
  nhưng bắt người xem tự đoán bước nối.
- **Kiểm tra "vậy thì sao?"** sau mỗi cụm ý. Nếu câu chỉ nêu nguyên nhân, cơ chế,
  ví dụ, phép so sánh, con số hoặc sự kiện mà chưa nói tác dụng, hệ quả hay bước tiếp
  theo, phải thêm cầu nối hoặc viết lại. Ví von chỉ hỗ trợ hình dung, không thay thế
  lời giải thích nghĩa đen. Không chia nhịp làm gãy một quan hệ nguyên nhân–kết quả.
- **Kiểm tra tham chiếu trước khi dựng**: các từ như “này”, “đó”, “nó”, “lần nữa”,
  “như vậy”, “sau đó” và các cụm như “đường bay này”, “kết quả đó” chỉ được dùng khi
  đối tượng hoặc sự kiện đã được giới thiệu rõ ở trước. Nếu chưa có tiền đề, gọi tên
  đối tượng hoặc thêm câu giới thiệu; không dùng đại từ để tạo cảm giác liên kết giả.
- **Kiểm tra nguồn của từng mệnh đề**: trước khi dựng, đối chiếu mỗi mệnh đề thực tế
  với câu tương ứng trong bài gốc hoặc nguồn đã kiểm tra. Đặc biệt rà các câu nối
  nguyên nhân–kết quả, động cơ và kết luận; nếu không có căn cứ trực tiếp thì phải
  bỏ hoặc hạ mức khẳng định, không tự chế cho mạch kể trơn tru.
- **Bố cục khung hình video thường**: ảnh neo đáy tại `meme_y=150`, `meme_h=640` (đáy y≈750); chữ căn giữa tại `text_y=880`; khoảng cách đáy ảnh → đỉnh chữ ~20px, không đè lên nhau. Ảnh cách mỗi mép ngang tối thiểu 60px (`meme_w ≤ 960`).

## Tìm và kiểm ảnh
- Lập bảng danh từ/chủ thể theo từng nhịp trước khi gom tag.
- Kiểm tra ảnh minh họa đúng chủ thể/hành động đang đọc; loại ảnh lạc đề.
- Ảnh thật chỉ dùng 1 lần toàn video; meme tối đa 2 lần, không liền kề. Đối chiếu cả file/hash/nội dung để phát hiện bản sao đổi tên, đổi kích thước hoặc cắt lại.
- **Ảnh mở và ảnh kết phải là cùng một ảnh (bookend)** — đây là ngoại lệ duy nhất của quy tắc trên. Chọn ảnh khái quát dùng được cho cả hai đầu và viết câu kết nhắc đúng thứ ảnh thể hiện.
- Ghi nguồn vào `assets/illus/<nội-dung>/SOURCES.txt` (không đưa credit lên video).

## Render
- `pl.analyze(script, content=...)` → rows có cột clip → `pl.render(rows, opt, preview=True)` ra preview trong `work/`.
- **Luôn dựng preview trước, chỉ xuất bản cuối khi người dùng duyệt.** Không tự xuất video hoàn chỉnh.
- **Đặt tên/đường dẫn** (pipeline tự sinh theo `opt.content`): giữ timestamp tạo file
  ở cuối để phân biệt các lần render.
  - Preview: `work/preview_<topic>_<YYYYMMDD_HHMMSS>.mp4`
  - Video thường hoàn chỉnh: `output/kienthuc/video_<topic>_<YYYYMMDD_HHMMSS>.mp4`
  - Threads hoàn chỉnh: `output/<topic>/video_<topic>_<YYYYMMDD_HHMMSS>.mp4`
- Dọn preview và `work/job_*` cũ sau khi người dùng duyệt bản mới. Giữ cache voice và `work/threads-script/`.
- Mascot đứng yên đến cuối video rồi mới tụt xuống.
- Âm thanh chuyển mục dùng **pop** (không dùng whoosh) cho video thường.

## Quy tắc
- "Làm video" = đi tới mp4 luôn (không dừng ở bàn giao).
- "Xử lý kịch bản" = chỉ chuẩn hóa, không render.
- Chủ đề thương vong/tang tóc/tai nạn chết người: không dùng meme, tắt mascot, dùng ảnh thật/tư liệu cho toàn bộ.
- Video thường xuất vào `output/kienthuc/`; preview luôn để trong `work/`.