# Quy ước làm việc của VideoMaker

## Cấu trúc dự án

- `videomaker/`: mã nguồn Python; dùng import theo package `videomaker`.
- `frontend/`: giao diện React/Vite; `src/` là mã nguồn, `dist/` là bản build Python phục vụ.
- `config/settings.json`: cấu hình giao diện và kịch bản đang làm.
- `docs/`: hướng dẫn sử dụng và sơ đồ thư mục.
- `tests/`: bài kiểm thử; `tools/`: công cụ phát triển.
- `assets/`: thư viện nền, ảnh, meme, font và nhạc; `output/`: video hoàn chỉnh.
- `work/`: dữ liệu tạm và trạng thái đăng nhập/đăng bài. Không xóa toàn bộ thư mục này khi dọn cache.
- `skills/`: các flow cho AI; `ffmpeg/` và `.venv/`: công cụ và môi trường chạy.

Chạy app bằng `run.bat` hoặc `.venv\Scripts\python.exe -m videomaker` từ thư mục gốc.
App mặc định dùng giao diện React tại `http://127.0.0.1:7860`, backend là FastAPI.
Sau khi sửa React, chạy `npm.cmd run build` trong `frontend/`, hoặc dùng `run_dev.bat` để tự build lại.
Không đưa token Facebook vào frontend, localStorage hoặc phản hồi API. Media được phục vụ qua `/api/media`.
Chạy kiểm thử bằng `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
Xem [sơ đồ và cách dùng](docs/CAU_TRUC.md) khi cần tìm file.

## Video thường (không phải Threads)

Khi người dùng đưa kịch bản thô để làm video, đọc và áp dụng
[skill tạo kịch bản](skills/tao-kich-ban/SKILL.md), đặc biệt mục "Flow video thường đã chốt".
Mặc định biên tập theo giọng chia sẻ, cập nhật thông tin; chuẩn hóa format của app;
tự tìm, tải hoặc chụp ảnh minh họa bằng Playwright và chuẩn bị meme phù hợp.
Bàn giao kịch bản cùng media đã lưu sẵn để người dùng kiểm tra rồi tự làm tiếp trong app.
Dừng ở bước bàn giao; chỉ render preview, xuất video hoặc đăng bài khi người dùng yêu cầu.

## Threads

Flow video thường ở trên không thay đổi flow Threads. Với bài/comment Threads, giữ quy tắc riêng
của flow đó: bám nguyên văn nguồn, chỉ chuẩn hóa cách đọc TTS, không tự sáng tác thêm.
Khi người dùng dán bản thô comment (`# ...png` + các dòng `|| -`) và muốn đọc thành tiếng,
đọc [skill chuẩn hóa comment](skills/vn-comment-tts-normalize/SKILL.md) và làm đúng quy trình ở đó.

Giao diện **Biên tập Threads** có flow riêng: prepare (code, dựng cha–con và thứ tự)
→ curate (người dùng tự dùng LLM, bỏ khối dư nhưng giữ nguyên chữ)
→ normalize (người dùng tự dùng LLM theo quy tắc TTS)
→ validate (code báo lỗi/cảnh báo theo bước và dòng). Các đầu ra là ô text chỉnh sửa trực tiếp.
Threads lấy bài/chụp ảnh xong sẽ đưa kịch bản thô thẳng sang Biên tập, không bắt chọn nguồn/JSON lại.
Kịch bản thô chỉ xử lý ở Biên tập; ô Kịch bản ở Threads chờ bản hoàn chỉnh sau khi validate
và người dùng bấm chuyển về. Giữ bản thô và metadata riêng với bản đã xử lý.
Không tích hợp hoặc tự gọi Claude/LLM. Chỉ chuyển bản đã kiểm tra sang trình dựng khi người dùng bấm;
không tự render, không ghi đè nguồn. Quy tắc UI nằm ở `docs/GIAO_DIEN_REACT.md`.
Mỗi bài/scan có checkpoint các bước trong `work/threads-script/sessions/`: tự lưu và mở lại được
sau khi đóng app. Danh sách Bài đã scan mở lại dữ liệu/ảnh sẵn có, không ép scan lại.
Giữ thư mục checkpoint khi dọn cache. Khôi phục báo cáo cũ để xem, rồi validate lại trước khi dựng.
