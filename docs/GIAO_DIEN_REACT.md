# Dùng VideoMaker Studio

Đóng app cũ rồi bấm `run.bat`. React và Python API cùng chạy tại
`http://127.0.0.1:7860`. Bản build React đã có sẵn trong `frontend/dist/`.

Giao diện dùng shadcn/ui với nền sáng mặc định, chữ và viền rõ hơn. Nút mặt trời/mặt trăng
trên thanh đầu trang đổi sáng/tối và nhớ lựa chọn trên trình duyệt.

## Video thường

1. Nhập tên nội dung trùng thư mục minh họa trong `assets/illus/`.
2. Dán kịch bản đã chuẩn bị hoặc mở file `.txt`. Mỗi dòng theo format `[thẻ] lời đọc || chữ hiển thị`.
3. Bấm **Phân tích kịch bản**. Trong **Các nhịp**, sửa lời đọc, chữ, thứ tự hoặc chọn media từ thư viện.
4. Bấm **Xem khung nhịp** để kiểm tra hình, hoặc **Dựng bản xem thử** để dựng MP4 chất lượng thấp.
5. Khi đã kiểm tra xong, bấm **Xuất video đẹp**. Thành phẩm xuất hiện trong **Video đã xuất**.

**Thiết lập video** chứa giọng đọc, tốc độ, nghỉ giữa nhịp, nền, nhạc, phụ đề, bố cục và GPU.
Nút **Xem thử bố cục · 1 hình** nằm ngay đầu trang Video thường và Threads. Có thể nhập câu thử,
chọn ảnh/meme rồi tạo một ảnh khung hình mà không cần phân tích kịch bản, tạo giọng hay render video.
Ảnh preview có thể mở lớn và tải về; nhịp reply đã có ngữ cảnh sẽ giữ thông tin cha trong preview.
**Lưu cấu hình** lưu kịch bản video thường và thông số dùng chung vào `config/settings.json`.
Nút tải bên cạnh tab kịch bản tải bản `.txt`; nếu đã sửa bảng nhịp, file dùng nội dung bảng hiện tại.

Flow AI vẫn là: người dùng đưa bản thô → AI biên tập giọng chia sẻ/cập nhật, tìm và lưu ảnh/meme →
bàn giao kịch bản để người dùng kiểm tra và tự làm tiếp. Giao diện không tự viết lại nội dung hay tự render.

## Threads

Dán link bài và bấm **Lấy bài**, hoặc mở bài đã lưu. Có thể đăng nhập Threads, chọn chế độ ảnh,
số comment và giới hạn reply trong phần tùy chọn. Khi lấy bài/chụp ảnh xong, app tự chuyển
kịch bản thô và ánh xạ ảnh sang **Biên tập Threads**. Ô Kịch bản ở Threads chưa nhận bản thô.

Xử lý đủ bốn bước trong Biên tập, kiểm tra rồi bấm **Dùng trong trình dựng Threads**.
Chỉ lúc đó bản hoàn chỉnh mới được điền vào ô Kịch bản ở Threads để dựng/xuất video.
Reply giữ ngữ cảnh cha; `|| -` giữ trạng thái không phụ đề. Mỗi nhịp có chip **Zoom**: bật thì
card phóng to theo **Độ zoom** trong bố cục và ẩn phụ đề; mục có ảnh đính kèm (bài gốc hoặc
comment) tự được thêm một nhịp zoom ở cuối, đi kèm nhạc. Lấy bài mới hoặc đổi danh sách comment
sẽ hủy bản hoàn chỉnh cũ và đưa bản thô mới trở lại Biên tập.

## Biên tập Threads theo 4 bước

Tab này nhận trực tiếp bản thô từ bài đang làm ở **Threads**, không yêu cầu chọn bài nguồn,
mở JSON hoặc nhập lại kịch bản. Mở từ thanh bên cũng tiếp tục đúng bản đang làm.
Nếu chưa lấy bài, UI hướng dẫn quay về Threads. Mọi bản thảo đều là ô text chỉnh sửa trực tiếp.

**Làm tiếp vào lần sau:** danh sách **Tiếp tục bài đã scan** hiển thị cả các bài đã lấy trước đây
và các phiên biên tập đã lưu. Bấm **Mở để tiếp tục** để dùng ảnh/dữ liệu có sẵn, không scan lại.
Nếu đã có phiên lưu, app khôi phục bản thô, nguồn cha–con, curated, TTS, bước đang làm và báo cáo kiểm tra.
Khi mở Biên tập mà chưa có bài đang làm, app tự mở phiên được lưu gần nhất.

Các bước tự lưu sau khi ngừng chỉnh khoảng 0,8 giây. Nút **Lưu phiên** lưu ngay; kiểm tra trạng thái
**Đã tự lưu** trước khi đóng app. Phiên nằm trong `work/threads-script/sessions/`, tồn tại sau khi đóng
trình duyệt hoặc khởi động lại Python. Không xóa thư mục này khi dọn file render tạm.
Bài scan cũ chưa có phiên vẫn mở lại và tạo bản thô từ `threads.json` có sẵn; không cần lấy bài lại.

1. **Prepare (code):** dựng nhóm cha–con, đặt cha trước reply và cũ trước mới trong từng nhóm;
   hiện cây nguồn và **Kịch bản thô nhận từ Threads**. Không tự loại comment hay sửa chữ.
   Có thể chỉnh bản thô ở đây rồi bấm **Prepare & sang Curate** để chuẩn bị lại;
   curated được đối chiếu đúng bản thô vừa chốt, ảnh và quan hệ cha–con giữ từ bài đã lấy.
2. **Curate (bạn + LLM bên ngoài):** lấy prompt kèm nguồn, tự gửi cho LLM rồi dán kết quả vào
   **Bản tuyển chọn nguyên văn**. Chỉ bỏ khối dư sau khi xét cả hội thoại; giữ nguyên chữ của mục được giữ.
   Có nút bắt đầu từ nguyên văn nếu muốn tự tuyển chọn bằng tay.
3. **Normalize (bạn + LLM bên ngoài):** lấy prompt quy tắc TTS, dán kết quả vào
   **Bản đã chuẩn hóa TTS**. Giữ nguyên mục ảnh/thứ tự từ curated; mỗi nhịp là `lời đọc || -`.
4. **Validate (code):** kiểm tra nguyên văn của curated, thứ tự cha–con, header/ảnh,
   hai vế `|| -`, mục bị thêm/bỏ giữa curate và normalize, cùng các dấu hiệu viết tắt/số còn sót.
   Mỗi lỗi có bước và dòng; bấm lỗi để quay về đúng ô. Sửa text sẽ hủy kết quả cũ, cần kiểm tra lại.

Trạng thái có ba mức: **Chưa đạt**, **Đạt cấu trúc — cần rà**, **Đạt kiểm tra bằng code**.
Code không chứng minh được normalize giữ đúng nghĩa, tên riêng hoặc mức giọng; vẫn cần tự đọc đối chiếu.
Không dùng độ dài hay thời lượng ước tính để tự bỏ comment.

Có thể sao chép hoặc tải `source.txt`, `curated.txt` và `tts-cleaned.txt` riêng.
Chỉ khi bấm **Dùng trong trình dựng Threads**, app kiểm tra lại ảnh và nạp bản thảo sang trình dựng;
không render video, không tự gọi LLM, không ghi đè file nguồn. Vẫn có thể tải các bản text riêng nếu cần.
Kết quả kiểm tra lần trước được khôi phục để xem; cần bấm **Kiểm tra lại** trước khi chuyển sang trình dựng
vì ảnh hoặc dữ liệu trên máy có thể đã thay đổi.

## Thư viện và video đã xuất

### Duyệt mẫu thiết kế thẻ Threads

Nút **Xem mẫu thiết kế ảnh Threads** mở trang `/design/threads.html` với ba mẫu đồng bộ:
bài gốc, bình luận và reply có trích ngữ cảnh cha. Có thể thử cỡ chữ, bo góc, màu chữ và nền,
tải từng mẫu SVG hoặc sao chép thông số để trao đổi trước khi áp dụng một thiết kế chung.
Đây là nội dung minh họa để duyệt bố cục, chưa áp lên ảnh đã scan hoặc bộ dựng video.
Trang mẫu cũng có nút riêng **Mẫu thiết kế Threads** trong thanh điều hướng bên trái và đầu trang Threads.

**Thư viện media** hỗ trợ tìm kiếm, lọc, xem file, tải thêm ảnh/video/nhạc/font và xóa từng file.
Minh họa được lưu theo nội dung và thẻ, meme theo thẻ cảm xúc. File mới có tên riêng để không ghi đè file cũ.
**Video đã xuất** cho phép xem/tua video, tải về hoặc chuyển video đã chọn sang màn hình Facebook.

## Facebook Reels

Trong **Kết nối Page**, nhập Page ID và token nếu cần, lưu rồi kiểm tra kết nối.
Token đã lưu không hiển thị lại trong trình duyệt. Cấu hình từ `work/fb.env` vẫn được sử dụng như trước.

Chọn video, nhập caption hoặc lấy gợi ý từ bài Threads đã lưu, chọn giờ hoặc đăng ngay.
Với hàng loạt, chọn video, xếp giờ rồi sửa từng caption và mốc giờ trước khi xác nhận gửi.
Trong **Bài đang chờ**, tải danh sách từ Page để xem và hủy lịch.
App không tự gửi lại một tác vụ đăng bài khi gặp lỗi; kiểm tra Page trước khi chủ động thử lại.

## Khi đang xử lý

Thanh tiến độ hiển thị trạng thái tác vụ. Bản đang sửa được giữ khi chuyển giữa các màn hình trong cùng phiên.
Tải lại trang sẽ nạp lại kịch bản video thường đã lưu; tác vụ nền đang chạy tiếp tục được theo dõi
trong cùng phiên máy chủ. Việc theo dõi không khởi chạy lại render hay đăng bài.

Nếu cần kiểm tra cài đặt, mở **Kiểm tra hệ thống** rồi bấm **Kiểm tra máy**.
Cách cài, build và phát triển nằm trong [CAU_TRUC.md](CAU_TRUC.md).

Nếu từng gặp lỗi `BrowserType.launch: ENOENT ... mkdtemp ... playwright-artifacts`, đóng hẳn app
và mở lại `run.bat`. App tạo và dùng `work/browser_temp/` cho Playwright thay vì đường dẫn Temp
của hồ sơ Windows. Không xóa thư mục này khi trình duyệt lấy bài hoặc đăng nhập đang chạy.
