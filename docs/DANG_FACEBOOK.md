# Đăng / hẹn giờ video lên Facebook Page

Video đã xuất trong `output/` được đăng bằng Graph API qua `videomaker/fb_post.py` + tab
**Đăng Facebook** trong app (cách bấm xem [GIAO_DIEN_REACT.md](GIAO_DIEN_REACT.md)). Hẹn giờ là hẹn
giờ *của Facebook*: video tải lên ngay, Facebook tự đăng lúc đã hẹn, app tắt vẫn chạy.

## 1. Cấu hình một lần (khuyến nghị: biến môi trường)

**Page ID + token không cần nhập vào app mỗi lần** — lấy theo thứ tự ưu tiên:

1. Biến môi trường của máy: `FB_PAGE_ID`, `FB_PAGE_TOKEN` (+ `FB_GRAPH_VERSION` tuỳ chọn).
2. File `work/fb.env` (cùng dạng `KEY=VALUE`, đọc lại mỗi lần đăng — không cần restart app).
3. `work/fb_config.json` do app lưu khi nhập tay.

Token lấy từ (1) hoặc (2) **không bao giờ bị ghi xuống** `work/fb_config.json`.

Thiết lập nhanh trên Windows (PowerShell):

```powershell
[Environment]::SetEnvironmentVariable('FB_PAGE_ID', '1234567890', 'User')
[Environment]::SetEnvironmentVariable('FB_PAGE_TOKEN', 'EAA…', 'User')
```

hoặc tạo `work/fb.env`:

```env
FB_PAGE_ID=1234567890
FB_PAGE_TOKEN=EAA…
FB_GRAPH_VERSION=v24.0
```

Quyền token cần: `pages_manage_posts`, `pages_read_engagement`. Mở app lại, tab **Đăng Facebook**
hiển thị `✅ Đang dùng Page ID + token từ biến môi trường`. **🔌 Kiểm tra kết nối** trả về tên Page
+ số lượt thích để chắc token đúng.

## 2. Đăng một video

Tab **Một video**:

1. Chọn video đã xuất trong danh sách (mới nhất trước; video đã đăng/hẹn có ghi chú).
2. Caption tự điền **phương án 1** soạn sẵn từ kịch bản/bài Threads đã tạo ra video; sửa lại trực
   tiếp trong ô caption nếu muốn.
3. Giờ đăng mặc định là **11:30 gần nhất** còn ≥ 15 phút; sửa tay nếu muốn giờ khác, hoặc tích
   **Đăng ngay**.
4. Bấm **Kiểm tra & lên lịch** → xem lại caption/giờ trong hộp xác nhận → **Xác nhận gửi**.

App không tự chọn video hay xếp thứ tự file: mỗi lần đăng là một video do bạn chọn. Muốn hẹn nhiều
video, đăng lần lượt từng video với ngày giờ bạn muốn.

Giờ hẹn phải cách hiện tại **≥ 11 phút** và **≤ 30 ngày**; video tối đa 1 GB.

## 3. Quản lý bài đã hẹn

**↻ Tải danh sách** xem các bài đang chờ (`is_published=false`), bấm **Hủy lịch** để huỷ (bài bị huỷ
sẽ về lại danh sách chưa đăng). Chỉ đăng được lên **Page**, không đăng được trang cá nhân.
Reels/Stories không có hẹn giờ native.

## 4. Caption tự động

> Caption sinh tự động chỉ là **bản nháp theo công thức** (không có LLM trong app): chữ lấy từ chính
> bài/comment, không thêm số liệu. Muốn caption sắc hơn thì nhờ agent viết rồi dán vào ô caption.

- Caption mặc định là **phương án 1** của công thức trong `videomaker/caption.py`, soạn từ
  `post.text` của bài Threads đã tạo ra video hoặc từ nhịp hook của `kich-ban.txt`.
- Khối hashtag chung được nối vào cuối caption khi gửi, bỏ trùng, bỏ tag chung chung
  (`#viral`, `#reels`, `#xuhuong`, `#thinhhanh`, `#fyp`…) và tối đa 5 tag.
