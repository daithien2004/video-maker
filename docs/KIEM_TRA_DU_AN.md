# Rà cấu hình, dữ liệu tạm và tốc độ dựng — 29/10/2026

## Cấu hình và bản thảo

Trước đây `settings.json` chứa cả `script` và `content`, nên mở file cấu hình thấy nguyên
kịch bản Mbappé. Đây là dữ liệu bản đang làm, không phải mã nguồn thừa.

Đã chuyển nguyên vẹn 1.616 ký tự của kịch bản cùng tên nội dung sang
`work/video-draft.json`. `config/settings.json` chỉ giữ thiết lập. Khi gặp cấu hình cũ,
app tự chuyển bản thảo trước rồi mới bỏ hai khóa khỏi cấu hình. Lưu thiết lập không
ghi đè bản thảo; React nhận bản thảo qua `video_draft` và lưu qua `/api/video-draft`.

Đã bỏ kịch bản minh họa mặc định trong code, một `return` không thể chạy tới và hai
import React không dùng. Không xóa giao diện Gradio cũ vì vẫn được tài liệu hỗ trợ,
và API còn dùng nhiều thao tác trong cùng module.

Đã đóng pipe đọc tiến độ FFmpeg sau khi tiến trình kết thúc; giảm chu kỳ chờ kiểm tra
từ 1 giây xuống 0,1 giây để bớt thời gian chờ thừa của các lần chuyển âm thanh ngắn.

## Mẫu đo tốc độ

Chạy `tools/profile_render.py` bằng Python 3.11 của dự án. Dùng ba ảnh minh họa thật,
các bộ lọc của pipeline hiện tại, âm thanh im lặng thay cho TTS, dựng 2 giây ra thiết bị
bỏ dữ liệu (`null`), không xuất video thành phẩm và không đăng bài.

| Cấu hình | Thời gian thực |
|---|---:|
| NVENC, 60 FPS, nền chuyển động | 7,208 giây |
| NVENC, 60 FPS, nền đứng | 3,812 giây |
| NVENC, 30 FPS, nền chuyển động | 3,690 giây |
| CPU x264 medium, 60 FPS, nền chuyển động | 5,843 giây |

Đây là một lượt đo rất ngắn; khởi động FFmpeg, tải bộ lọc và thứ tự chạy có ảnh hưởng.
Không dùng số này để dự đoán thời gian video dài hoặc kết luận CPU luôn nhanh hơn GPU.
Tuy nhiên, mẫu cho thấy giảm khối lượng xử lý hình đem lại khác biệt rõ: nền chuyển động
đang scale ở 2160×3840 trở lên trước khi thu về 1080×1920, và mặc định xử lý 60 FPS.
NVENC chỉ thay bộ mã hóa cuối, không chuyển các bộ lọc này sang GPU.

Chưa thay FPS, preset NVENC hoặc tắt hiệu ứng của người dùng. Nếu muốn tối ưu tiếp,
nên đo một đoạn dài đại diện, lặp nhiều lượt, rồi so chất lượng hình giữa 30/60 FPS
và nền đứng/chuyển động trước khi chọn mặc định mới.

## Dọn dữ liệu

Đã dọn 11 preview cũ, thư mục ảnh thử `work/demo_next_card`, `work/_t` và Python bytecode
có thể tạo lại: tổng khoảng **117,4 MiB**. Chi tiết trong `work/cleanup-report.json`.
Giữ preview mới nhất, mọi job dựng, cache voice, tất cả media gốc, video thành phẩm,
bản thảo, checkpoint Threads, cấu hình và phiên đăng nhập.

Lệnh dọn job cũ bị duyệt tự động từ chối vì job còn chứa âm thanh/dữ liệu dựng có thể cần
giữ; không xóa các thư mục đó. Không xóa toàn bộ `work/` hoặc `work/cache/`.

## Kiểm chứng

- Build React thành công; kiểm tra khoảng trắng trong diff không báo lỗi.
- Python: 120/121 bài kiểm thử qua, gồm toàn bộ API và năm kiểm thử mới cho lưu/chuyển
  bản thảo. Một kiểm thử Threads hiện yêu cầu từ chối mục ảnh trống, trong khi code
  hiện tại chuyển mục ảnh trống thành nhịp âm thanh; không đổi hành vi này trong đợt dọn.
- JavaScript: 12/14 bài qua. Hai lỗi sẵn có ở `threads-flow.test.js` liên quan bản thô
  được đưa thẳng vào ô kịch bản thay vì chờ biên tập; không sửa flow Threads trong đợt này.

Khởi động lại backend bằng `run.bat` sau khi cập nhật để dùng hợp đồng bootstrap mới.

## Tối ưu đã áp dụng sau khi đo

Thay chuỗi scale nền thay đổi kích thước liên tục bằng `zoompan` đầu ra cố định, vẫn
lấy mẫu ở lưới 2× để giữ chuyển động mịn. Cố định thời điểm đầu nền ở 0 để không lệch
một khung sau khi seek video nền. Tham số tham khảo: [FFmpeg zoompan](https://www.ffmpeg.org/ffmpeg-filters.html#zoompan).
Ảnh card, mascot và dây nối được giải mã/fit ở 1 FPS, rồi lặp khung tại FPS xuất trước
các bước hoạt hình. Video/GIF vẫn xử lý theo nhịp hình của video. Preview giới hạn 30 FPS;
bản xuất vẫn dùng FPS người dùng chọn. Giữ NVENC p5, CQ 19 và 1080×1920.

Đã xuất mẫu MP4 thật 8 giây, gồm ba card Threads, chữ Việt, mascot và chuyển card;
voice được thay bằng im lặng, giữ tiếng hiệu ứng. Hai lượt đo chạy theo thứ tự đảo nhau:

| Cách dựng | Trung bình hai lượt |
|---|---:|
| Cách cũ, 60 FPS | 21,262 giây |
| Chỉ tái sử dụng ảnh | 13,456 giây |
| Tái sử dụng ảnh + zoom mới, 60 FPS | 9,578 giây |

Mẫu này nhanh khoảng **2,22 lần**, giảm khoảng 55% thời gian. Không suy rộng thành tốc độ
cam kết cho mọi video: số card, kích thước ảnh, độ dài và phần cứng đều ảnh hưởng.
Trên mẫu đã xem, độ rõ card/phụ đề được giữ; SSIM so với bản cũ tại đoạn card ổn định
3,2–4,5 giây là 0,999662 ở vùng card, 0,999568 ở vùng phụ đề. SSIM toàn video là 0,974941:
nền có khác biệt do cách nội suy và làm tròn vùng zoom, không phải video giống từng pixel.
Âm thanh giải mã trước/sau có cùng SHA-256. FFprobe xác nhận cả hai file 8 giây,
1080×1920, H.264 60 FPS, AAC, yuv420p.

Số đo được giữ trong `work/render-profile.json`; các MP4 mẫu, ảnh so sánh và log tạm
đã được dọn theo yêu cầu chuẩn bị phiên làm việc mới. Công cụ tái kiểm tra:
`tools/compare_render.py`. Chỉ số crop áp dụng cho bố cục mẫu đã đo, không đại diện toàn
bộ mọi bố cục. Kiểm thử FFmpeg thật cũng xác nhận đoạn card ngắn, khung cuối, thời lượng
audio, 24/60 FPS xuất và 30 FPS preview; nền video tiếp tục chuyển động, không bị đóng băng.
Toàn bộ 137 kiểm thử backend: 136 qua, còn lỗi biên tập mục ảnh trống đã ghi ở trên.
