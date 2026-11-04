# Quy ước làm việc của VideoMaker

## Cấu trúc dự án

- `videomaker/`: mã nguồn Python; dùng import theo package `videomaker`.
- `frontend/`: giao diện React/Vite; `src/` là mã nguồn, `dist/` là bản build Python phục vụ.
- `config/settings.json`: chỉ cấu hình dựng video; kịch bản video thường và tên nội dung nằm trong file kịch bản tại `assets/illus/<nội-dung>/`.
- `docs/`: hướng dẫn sử dụng và sơ đồ thư mục.
- `tests/`: bài kiểm thử; `tools/`: công cụ phát triển.
- `assets/`: thư viện nền, ảnh, meme, font và nhạc; `output/`: video hoàn chỉnh.
- `work/`: dữ liệu tạm và trạng thái đăng nhập/đăng bài. Không xóa toàn bộ thư mục này khi dọn cache.
- Giữ cache voice đã duyệt và checkpoint Threads khi dọn file render cũ.
- `skills/`: các flow cho AI; `ffmpeg/` và `.venv/`: công cụ và môi trường chạy.

Chạy dựng video bằng `python tools/render_script.py <kich-ban.txt> [--content <ten>] [--preview]`.
Giao diện React local vẫn dùng để xem/chỉnh sửa và thao tác trực tiếp; dựng kịch bản/video
cũng có thể thực hiện qua agent/CLI. Media nằm trong `assets/` và `output/`.
Chạy kiểm thử bằng `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
Cấu trúc tối giản: `assets/`, `output/`, `work/`, `config/`, `skills/`, `tools/`, `videomaker/`, `tests/`.

`skills/` chỉ có hai bộ: `lam-video-thuong` (kịch bản + minh hoạ + dựng video thường) và
`lam-video-threads` (chuẩn hóa comment + scraper + card + render Threads).

## Video thường (không phải Threads)

Khi người dùng đưa kịch bản thô để làm video, đọc và áp dụng
[skill làm video thường](skills/lam-video-thuong/SKILL.md) — PHẦN 1, đặc biệt "Ba tầng ưu tiên" và
"Quy trình viết — 6 bước"
(CQ → sổ dữ kiện có nhãn → bản đồ nhịp → viết xuôi giọng chia sẻ kiến thức → thử xương sống → cắt nhịp). Mặc định biên tập theo giọng chia sẻ, cập nhật thông tin; chuẩn hóa format của app;
tự tìm, tải hoặc chụp ảnh minh họa bằng Playwright — **mọi nhịp dùng ảnh thật đúng nội dung đang đọc, không dùng meme**.
Bàn giao kịch bản cùng media đã lưu sẵn để người dùng kiểm tra rồi tự làm tiếp trong app.
Dừng ở bước bàn giao; chỉ render preview, xuất video hoặc đăng bài khi người dùng yêu cầu.
Lệnh "Làm video" (tự chọn sự kiện trong ngày tới mp4) ở PHẦN 2 của cùng skill.

## Threads

Flow video thường ở trên không thay đổi flow Threads. Với bài/comment Threads, giữ quy tắc riêng
của flow đó: bám nguyên văn nguồn, chỉ chuẩn hóa cách đọc TTS, không tự sáng tác thêm.
Khi người dùng dán bản thô comment (`# ...png` + các dòng `|| -`) và muốn đọc thành tiếng,
đọc [skill làm video Threads](skills/lam-video-threads/SKILL.md) PHẦN 1 và làm đúng quy trình ở đó.

Threads lấy bài/chụp ảnh xong: bản thô được đổ thẳng vào ô Kịch bản (nhãn "BẢN CHỈNH") để người dùng
sửa trực tiếp, không bắt chọn nguồn/JSON lại. Bản thô nguyên văn vẫn giữ trong card "Bản thô"
(chỉ đọc, có nút sao chép) để đối chiếu; bấm "Lưu kịch bản" mới ghi bản chỉnh vào session.
Không tích hợp hoặc tự gọi Claude/LLM; không tự render, không ghi đè nguồn Threads.
Quy tắc UI nằm ở `docs/GIAO_DIEN_REACT.md`; chạy scraper, chia nhịp, bố cục card và render bằng
lệnh nằm ở `skills/lam-video-threads/SKILL.md` PHẦN 2.
Bài đã scan và phiên chỉnh sửa có checkpoint trong `work/threads-script/` (`video-drafts/`, `sessions/`):
mở lại được sau khi đóng app, không ép scan lại. Giữ thư mục này khi dọn cache.
