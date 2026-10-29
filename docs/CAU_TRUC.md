# Cấu trúc VideoMaker

Các lệnh dưới đây chạy từ thư mục gốc `D:\media\VideoMaker`.

```text
VideoMaker/
├── run.bat                Mở app
├── run_dev.bat            Mở app, tự tải lại khi sửa code
├── install.bat            Cài môi trường và công cụ
├── requirements.txt       Thư viện Python
├── AGENTS.md              Quy ước và flow cho AI
├── videomaker/            Mã nguồn ứng dụng
│   ├── __main__.py        Điểm khởi động
│   ├── api.py             API FastAPI, tác vụ nền và phục vụ React
│   ├── editorial_store.py Lưu/khôi phục tất cả bước biên tập theo từng scan
│   ├── paths.py           Đường dẫn gốc và cấu hình
│   ├── app.py             Các thao tác dùng chung và giao diện Gradio cũ
│   ├── pipeline.py        TTS, ghép media và dựng video
│   ├── caption.py         Caption và hashtag
│   ├── fb_post.py         Đăng và hẹn giờ Facebook Reels
│   ├── comment_manager.py Quản lý comment
│   ├── script_draft.py    Chuẩn bị lời đọc Threads
│   └── threads_*.py       Lấy bài, sắp reply và biên tập Threads
├── frontend/              Giao diện React/Vite
│   ├── src/               Các màn hình, kết nối API và CSS
│   │   ├── components/ui/ Component shadcn/ui
│   │   ├── Editorial.jsx  UI prepare → curate → normalize → validate
│   │   └── theme.css      Token màu sáng/tối dùng chung
│   ├── dist/              Bản build được Python phục vụ
│   ├── package.json       Thư viện và lệnh build
│   └── package-lock.json  Khóa phiên bản thư viện
├── config/
│   └── settings.json      Cấu hình giao diện và kịch bản đang làm
├── docs/                  Hướng dẫn sử dụng và cấu trúc dự án
├── tests/                 Các bài kiểm thử test_*.py
├── tools/
│   ├── dev.py             Theo dõi code, build React và khởi động lại app
│   └── check_react_ui.py  Kiểm tra giao diện bằng Playwright
├── skills/                Hướng dẫn làm việc cho AI
├── assets/
│   ├── backgrounds/       Video nền
│   ├── illus/             Minh họa và kịch bản, chia theo chủ đề
│   ├── memes/             Meme dùng chung và catalog
│   ├── fonts/             Font tùy chọn
│   └── music/             Nhạc nền
├── output/                Video xuất xong và metadata đi kèm
├── work/                  File tạm và trạng thái vận hành
├── ffmpeg/                FFmpeg, FFprobe, FFplay và tài liệu đi kèm
└── .venv/                 Môi trường Python
```

## Cách chạy

Bấm `run.bat` để dùng bình thường, hoặc chạy:

```powershell
.\.venv\Scripts\python.exe -m videomaker
```

Giao diện React và API cùng chạy tại `http://127.0.0.1:7860`. Khi đổi sang bản mới,
đóng app cũ rồi mở lại bằng `run.bat`.

Cài từ đầu bằng `install.bat` (cần Python và Node.js 22.12+). Bản build đã có thì
chạy app hằng ngày chỉ cần Python. Khi sửa React, build lại:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run build
Set-Location ..
```

Các màn hình: Video thường, Threads, Biên tập Threads, Thư viện media, Video đã xuất, Facebook Reels,
Kiểm tra hệ thống. Nút Lưu cấu hình lưu bản kịch bản video thường và thông số dùng chung;
bản sửa trong phiên được giữ khi chuyển tab. Tải file kịch bản để lưu bản riêng của Threads.

Để phát triển giao diện với Vite: giữ Python API chạy ở cổng 7860, chạy `npm.cmd run dev`
trong `frontend/`, rồi mở URL Vite in ra (mặc định cổng 5173). Vite chuyển `/api` về Python.

Kiểm tra UI trên một server đang chạy, không đăng bài Facebook:

```powershell
.\.venv\Scripts\python.exe tools/check_react_ui.py --url http://127.0.0.1:7860
```

Script kiểm tra sẽ tạo một khung hình thử và screenshot trong `work/`; thao tác lưu
cấu hình và dựng preview được giả lập để giữ nguyên kịch bản đang lưu và video đã xuất.
Giao diện Gradio cũ vẫn có thể mở riêng bằng `.venv\Scripts\python.exe -m videomaker.app`.

Lấy bài Threads từ dòng lệnh:

```powershell
.\.venv\Scripts\python.exe -m videomaker.threads_shot --help
```

Chạy kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Khi sửa code, dùng `run_dev.bat`. Với script Python khác chạy từ thư mục gốc, dùng
`from videomaker import pipeline as pl` thay cho `import pipeline`.

## Nơi lưu dữ liệu

Video thường: AI lưu `kich-ban.txt`, `SOURCES.txt` và ảnh theo tag bên trong
`assets/illus/<noi-dung>/`. Người dùng kiểm tra kịch bản rồi tự làm tiếp trong app.
Meme dùng chung nằm trong `assets/memes/`.

`work/cache/`, `work/job_*/`, `work/preview_*.mp4` và `work/frame_*` là dữ liệu tạm,
chỉ dọn khi không còn cần và không có tác vụ sử dụng. Các file `work/fb.env`,
`work/fb_config.json`, `work/fb_posted.json`, `work/threads_state.json` và glossary
nếu có là cấu hình, lịch sử hoặc phiên đăng nhập cần giữ lại.
`work/threads-script/sessions/` lưu bản thô, nguồn, curated, TTS, kết quả kiểm tra và bước đang làm
của từng bài đã scan; đây là dữ liệu dự án cần giữ, không phải cache render.

Để đưa giao diện về mặc định, đóng app rồi xóa `config/settings.json`.
Hướng dẫn sử dụng chi tiết nằm trong [HUONG_DAN.txt](HUONG_DAN.txt).
