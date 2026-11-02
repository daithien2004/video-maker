# Dùng VideoMaker Studio

Đóng app cũ rồi bấm `run.bat`. React và Python API cùng chạy tại
`http://127.0.0.1:7860`. Bản build React đã có sẵn trong `frontend/dist/`.

Giao diện dùng shadcn/ui với nền sáng mặc định, chữ và viền rõ hơn. Nút mặt trời/mặt trăng
trên thanh đầu trang đổi sáng/tối và nhớ lựa chọn trên trình duyệt.

## Video thường

1. Nhập tên nội dung trùng thư mục minh họa trong `assets/illus/`.
2. Dán kịch bản đã chuẩn bị hoặc mở file `.txt`. Mỗi dòng theo format `[thẻ] lời đọc || chữ hiển thị`.
3. Bấm **Tạo nhịp và voice** để chia nhịp và tạo giọng từ cùng một bản kịch bản. Lời không đổi dùng lại voice đã có. Khi sửa kịch bản, bấm nút này lại để đồng bộ cả hai trước khi xuất.
4. **Các nhịp** dùng để sửa chữ hiển thị, media và zoom. Tab **Voice** có nghe từng đoạn, **Nghe liên tục** và **Dừng nghe**. Khi thấy đoạn sai, bấm **Sửa lời đọc**, sửa ngay tại đó rồi **Lưu và tạo lại voice**. Thao tác này cập nhật đúng dòng trong kịch bản tổng và lời đọc của nhịp, chỉ tạo lại âm thanh đoạn vừa sửa, giữ nguyên hình và chữ hiển thị. Có thể **Lưu lời đọc** rồi tạo voice sau. Thêm/xóa hoặc đổi thứ tự dòng thực hiện ở **Kịch bản** rồi bấm **Tạo nhịp và voice** lại. Đổi giọng hoặc tốc độ rồi bấm **Cập nhật voice theo giọng đã chọn**.
5. Khi đã kiểm tra xong, bấm **Xuất video đẹp**. Video dùng lại voice đã tạo; không cần dựng bản xem thử trước. Thành phẩm xuất hiện trong **Video đã xuất**. Có thể dùng **Xem khung nhịp** để kiểm tra hình riêng.

Xuất hoàn chỉnh giữ độ phân giải 1080×1920 và FPS bạn chọn. Ảnh tĩnh được tái sử dụng;
nền zoom dùng bộ lọc đầu ra kích thước cố định để giảm tính lại. Preview dùng tối đa
30 FPS ở 540×960 cho nhẹ hơn; việc này không hạ FPS hoặc chất lượng bản xuất hoàn chỉnh.

**Thiết lập video** chứa giọng đọc, tốc độ, nghỉ giữa nhịp, nền, nhạc, phụ đề, bố cục và GPU.
Nút **Xem thử bố cục · 1 hình** nằm ngay đầu trang Video thường và Threads. Có thể nhập câu thử,
chọn ảnh/meme rồi tạo một ảnh khung hình mà không cần phân tích kịch bản, tạo giọng hay render video.
Ảnh preview có thể mở lớn và tải về; nhịp reply đã có ngữ cảnh sẽ giữ thông tin cha trong preview.
**Lưu thiết lập** ghi thông số dùng chung vào `config/settings.json`. **Lưu kịch bản** ghi
kịch bản video thường và tên nội dung vào `work/video-draft.json`; hai thao tác không ghi đè nhau.
App tự chuyển kịch bản trong cấu hình cũ sang file bản thảo khi mở lại.
Nút tải bên cạnh tab kịch bản tải bản `.txt` của kịch bản nguồn hiện tại.

Flow AI vẫn là: người dùng đưa bản thô → AI biên tập giọng chia sẻ/cập nhật, tìm và lưu ảnh/meme →
bàn giao kịch bản để người dùng kiểm tra và tự làm tiếp. Giao diện không tự viết lại nội dung hay tự render.

## Threads

Dán link bài và bấm **Lấy bài**, hoặc mở bài đã lưu. Có thể đăng nhập Threads, chọn chế độ ảnh,
số comment và giới hạn reply trong phần tùy chọn. Lấy bài/chụp ảnh xong, bản thô được đổ thẳng
vào ô **Kịch bản** (nhãn **BẢN CHỈNH**) để sửa trực tiếp; bản thô nguyên văn vẫn giữ trong card
**Bản thô** (chỉ đọc, có nút **Sao chép**) để đối chiếu. Lấy bài mới sẽ thay kịch bản bằng bản thô
mới và xóa nhịp, preview cũ.

**Số comment chính** là số mục cha được lấy theo đúng thứ tự hiển thị trên trang, không
tính reply vào chỉ tiêu này. **Reply mỗi comment** giới hạn số reply của từng cha; không có
ngưỡng like tối thiểu, reply 0 like vẫn được lấy. Không xếp lại theo like hay thời gian:
comment chính theo thứ tự lướt, reply đầu tiên của mỗi cha đứng ngay sau cha. Reply lồng
sâu hơn theo **Độ sâu reply**. Reply hiện ngay trên trang bài gốc được nhận cha theo thụt lề
(card lùi vào ~40px là con của card phía trên), nên bản thô ghi đúng `reply ↳ @cha` chứ không
tính thành comment chính.
Nếu Threads không tải đủ hoặc chạm giới hạn số trang, app báo kết quả có thể thiếu reply.

Sửa kịch bản tại ô **Kịch bản** rồi bấm **Lưu kịch bản** để ghi bản chỉnh vào phiên bài đang làm,
sau đó bấm **Tạo nhịp và voice** để chia nhịp và tạo giọng. Reply giữ ngữ cảnh cha; `|| -` giữ
trạng thái không phụ đề. Mỗi nhịp có chip **Zoom**: bật thì card phóng to theo **Độ zoom** trong
bố cục và ẩn phụ đề; mục có ảnh đính kèm (bài gốc hoặc comment) tự được thêm một nhịp zoom ở cuối,
đi kèm nhạc. Chỉ tính ảnh card dán được (host `fbcdn`/`cdninstagram`/`fbsbx`/`threads`); GIF Giphy
và ảnh ngoài whitelist bị bỏ nên không sinh nhịp zoom. Mục chỉ có ảnh (nhịp `[sound]`) thì chính
nhịp đó được bật zoom luôn, không thêm nhịp thứ hai — tiếng không bị phát lặp hai lần.
Nhịp zoom tự sinh có nút thùng rác (chỉ hiện trên nhịp `[zoom]` không có trong kịch bản): bấm là
xoá nhịp đó và app gắn `[nozoom]` vào dòng `#` của mục, nên **Tạo nhịp và voice** lần sau không
thêm lại. Muốn bỏ phóng to mà vẫn giữ tiếng thì tắt chip **Zoom** thay vì xoá nhịp.

Bài đã scan và bản kịch bản đã lưu của phiên nằm trong `work/threads-script/`: mở lại từ danh sách
**Mở bài** dùng ảnh và dữ liệu có sẵn, không cần lấy bài lại. Không xóa thư mục này khi dọn file
render tạm.

## Thư viện và video đã xuất

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
