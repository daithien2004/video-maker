---
name: tao-kich-ban
description: Biên tập kịch bản thô cho video thường theo giọng chia sẻ, cập nhật thông tin; chuẩn hóa format app và chuẩn bị ảnh minh họa, meme để người dùng duyệt rồi tự dựng. Với bài/comment Threads, dùng giao diện Biên tập Threads trong app.
---

# SKILL: Nội dung liền mạch → kịch bản video + minh hoạ

Mục tiêu: nhận **một đoạn văn liền mạch** (không tag, không `||`), trả về **kịch bản dán thẳng vào app**
và **tải sẵn minh hoạ** vào `assets/illus/<nội-dung>/<tag>/` (minh họa theo nội dung riêng) + `assets/memes/<tag>/` (meme dùng chung cho mọi video)

## Flow video thường đã chốt

- Người dùng cung cấp kịch bản thô. Biên tập thành lời kể tự nhiên theo giọng **chia sẻ, cập nhật thông tin**, giữ ý chính, tên riêng và số liệu; không tự thêm tình tiết hoặc số liệu chưa được kiểm chứng. Nếu người dùng yêu cầu giữ nguyên văn hoặc đưa bản đã duyệt để chỉ định dạng, giữ nguyên lời văn đó.
- Chia bản đã biên tập thành nhịp và chuyển sang format `[tag] lời đọc || CHỮ HIỂN THỊ CÓ *NHẤN MẠNH*`. Chữ hiển thị phải khớp lời đọc sau biên tập theo mục 4.
- Tự tìm và chuẩn bị ảnh minh họa: tải file có sẵn hoặc dùng Playwright chụp vùng ảnh/trang liên quan. Mở file kiểm tra đúng chủ thể, đủ rõ và không dính giao diện thừa; lưu theo chủ đề và ghi nguồn theo mục 6. Kết hợp meme từ thư viện phù hợp với từng nhịp.
- Lưu kịch bản UTF-8 tại `assets/illus/<nội-dung>/kich-ban.txt` và lưu sẵn toàn bộ media trước khi bàn giao. Gửi kịch bản để người dùng kiểm tra cùng bảng ánh xạ nhịp → tag → file, nguồn và đường dẫn thư mục. Phân biệt rõ phần đã hoàn tất và media còn thiếu.
- **Dừng ở bàn giao kịch bản và media để người dùng duyệt rồi tự làm tiếp trong app.** Không tự chạy TTS, render preview, xuất video hoặc đăng bài. Người dùng duyệt kịch bản không tự động đồng nghĩa với yêu cầu render; chỉ thực hiện khi được yêu cầu.
- Flow này dành cho video thường. Bài/comment Threads làm trong giao diện **Biên tập Threads** của app.

---

## 1. Đầu vào

- Một đoạn văn liền mạch (có thể có số liệu, tên người, mốc thời gian).
- Tuỳ chọn: giọng điệu (nghiêm túc / hài), độ dài mong muốn, ghi chú "chỗ này phải có hình X".
- **Mặc định biên tập kịch bản thô theo flow video thường đã chốt ở trên.** Giữ ý chính và thông tin thực tế; không tự rút bỏ ý quan trọng để ép thời lượng. Với yêu cầu giữ nguyên văn hoặc bản đã duyệt chỉ cần định dạng, chỉ chia nhịp, thêm tag và chuẩn hóa số/dấu câu cho TTS. Chữ hiển thị luôn khớp đầy đủ lời đọc cuối cùng.

## 2. Đầu ra (luôn đúng 3 phần)

**Phần A — Kịch bản để dán** (khối text thuần, mỗi dòng một nhịp):

```
[tag] lời đọc || CHỮ HIỂN THỊ CÓ *NHẤN MẠNH*
```

**Phần B — Bảng minh hoạ**: nhịp | danh từ/chủ thể và hành động cần minh hoạ | tag | file trong thư viện | lý do ảnh khớp nội dung | nguồn | giấy phép/tình trạng quyền sử dụng.
Kèm dòng cuối: đã tải về thư mục nào, còn thiếu gì.

**Phần C — Meme nên tải thêm cho lần sau**: dựa trên nội dung vừa làm và thư viện thực tế, trình bày bảng: mức ưu tiên | tên meme hoặc mô tả cảnh cụ thể | dùng cho tình huống/nhịp nào | thư viện hiện thiếu gì | số clip nên bổ sung | tag lưu | từ khoá tìm kiếm.
Ưu tiên các nhóm ít lựa chọn, meme đã dùng đủ 2 lần và cảm xúc đang phải dùng meme gần nghĩa để thay. Đề xuất 3–5 mục hữu ích khi có thiếu hụt; nếu đã đủ thì nói rõ, không cố liệt kê cho đủ. Không đề xuất lại đúng meme đã có; cần bổ sung thì yêu cầu cảnh/nhân vật khác. Không bịa link tải hoặc báo đã tải phần gợi ý. Phần này dùng để cải thiện lần sau, không thay cho việc hoàn tất ảnh/clip của bản hiện tại.

---

## 3. Chia nhịp (quan trọng nhất)

- Mục tiêu **7–14 từ lời đọc / nhịp** (≈3–5 giây nói). Câu dài thì cắt theo mệnh đề, không cắt giữa cụm từ. Có thể ngắn hoặc dài hơn để giữ nguyên văn và trọn cụm nghĩa; không thêm/bớt từ để đạt số từ mục tiêu.
- Cắt ở chỗ có dấu phẩy/chấm là tốt nhất — app cũng ngắt cụm chữ theo dấu câu nên nhịp và chữ khớp nhau.
- **Khoảng nghỉ giữa nhịp do app tự tính theo dấu câu cuối nhịp**: kết thúc bằng chấm/!/? nghỉ
  dài (~0.5s tổng), kết thúc bằng phẩy/chấm phẩy nghỉ ngắn hơn (~0.3s), cắt giữa cụm không dấu
  nghỉ ngắn nhất (~0.18s). Không cần chèn lệnh nghỉ; muốn khoảng lặng kịch tính ở chỗ nào thì
  kết thúc nhịp đó bằng dấu chấm. Luật này áp dụng cho cả flow Threads.
- **Không tách số khỏi danh từ**: "năm 1932", "20.000 con emu", "9.860 viên đạn" luôn nằm trong một nhịp.
- Mỗi nhịp **một ý**. Nếu một câu có 2 ý (người + hành động) thì tách thành 2 nhịp — mỗi nhịp sẽ có hình riêng.
- Đoạn chuyển ý lớn (địa điểm, thời gian, nhân vật mới) luôn bắt đầu nhịp mới.

## 4. Chữ hiển thị (`||`) và nhấn mạnh

- **Chữ hiển thị = đúng từng chữ lời đọc** (người xem nghe gì đọc nấy). Chỉ được phép làm 3 việc:
  viết IN HOA, đổi số viết bằng chữ thành chữ số, bọc `*nhấn mạnh*`. Không lược từ, không thêm từ,
  không đảo trật tự, không thay bằng từ đồng nghĩa, không tóm tắt. Không giới hạn chữ hiển thị ở 9 từ.
  Dài quá thì chia lời đọc và chữ hiển thị cùng một vị trí thành các nhịp tương ứng, không được rút gọn bên nào.
- Số liệu, số lượng, ngày tháng, năm, tỉ lệ: chuyển phần số viết bằng chữ sang chữ số, giữ đúng giá trị và giữ nguyên các từ xung quanh.
  Ví dụ: "năm một nghìn chín trăm ba mươi hai" → "NĂM *1932*";
  "mười nghìn viên đạn" → "*10.000 VIÊN ĐẠN*";
  "năm mươi ki lô mét trên giờ" → "*50 KI LÔ MÉT TRÊN GIỜ*".
  Không tự đổi "ki lô mét trên giờ" thành "KM/H", "phần trăm" thành "%", hoặc viết tắt đơn vị/từ ngữ khác.
  Giữ nguyên số đã ở dạng chữ số. Chỉ chuyển từ thực sự mang nghĩa số: "năm nay", "một lần nữa", "một đàn chim" không tự đổi thành "5 NAY", "1 LẦN NỮA", "1 ĐÀN CHIM".
- **Mỗi nhịp bắt buộc có ít nhất 1 cụm `*NHẤN MẠNH*` trong chữ hiển thị**, thường chọn 1–2 cụm trọng tâm.
  Ưu tiên con số → tên riêng → từ/cụm từ mang ý chính hoặc gây sốc. Nhịp không có số vẫn phải nhấn mạnh từ/cụm từ có sẵn trong lời đọc.
  Chỉ bọc dấu `*` quanh chữ có sẵn, không thêm hoặc sửa chữ để tạo điểm nhấn; không bọc toàn bộ câu dài.
- **Mọi con số quan trọng phải được `*nhấn mạnh*`**: 20.000, 9.860, 284.000, 986… Nếu có nhiều số quan trọng trong cùng nhịp, nhấn mạnh đủ các số đó.
- Ưu tiên dấu câu `, . ! ?`. Nếu bản gốc có `—`, `–`, `:`, `-` làm dấu ngắt câu, có thể thay bằng dấu phẩy/chấm ở cả lời đọc và chữ hiển thị để tránh app tách cụm kỳ lạ; không đổi từ hoặc ý. Giữ ký hiệu thuộc tên riêng, số âm hoặc khoảng số khi thay sẽ làm sai nghĩa.

## 5. Tag và thư viện minh hoạ

**Nguyên tắc: hình phải minh hoạ đúng nội dung đang đọc, không chỉ cùng chủ đề chung.** Tag mô tả chủ thể/hành động cụ thể; một tag chỉ dùng lại khi các nhịp thực sự cần cùng loại hình.

- Trước khi tìm ảnh, rà từng nhịp và liệt kê **danh từ/cụm danh từ có thể minh hoạ**: người, vật, địa điểm, tên riêng, hiện tượng, công cụ, hoạt động và hình ảnh so sánh. Lập danh sách bao phủ để không bỏ sót chủ thể mới, kể cả chỉ xuất hiện một lần.
- Xác định chủ thể chính, chủ thể phụ cần thấy và hành động/mối quan hệ của chúng trong nhịp. Đại từ như "nó", "đó" phải được nối với đúng chủ thể ở nhịp trước. Các từ chung như "điều", "những gì", "thời điểm" không cần ảnh riêng nếu đã được thể hiện trong cảnh.
- **Không dùng ảnh có sẵn chỉ để lấp chỗ trống.** Khi giới thiệu hoặc giải thích trực tiếp về Proxima Centauri phải có ảnh đúng Proxima Centauri, Andromeda phải đúng Andromeda; nhà thiên văn học, mắt thường nhìn trời và cuốn sách lịch sử cũng phải có hình tương ứng. Sau khi chủ thể đã được minh hoạ rõ, các nhịp phản ứng hoặc nhấn vào điều bất ngờ về chủ thể đó có thể dùng meme.
- Với quan hệ/hiện tượng như ánh sáng đi từ Mặt Trời đến Trái Đất, tìm ảnh hoặc sơ đồ có sẵn thể hiện đường truyền và hai chủ thể. Ảnh Mặt Trời đơn lẻ không đủ để chứng minh đã minh hoạ quan hệ này.
- Nếu một nhịp có nhiều chủ thể cần ảnh riêng, chia nhịp tại ranh giới cụm nghĩa và gán tag cụ thể cho từng phần; giữ nguyên toàn bộ lời đọc và chữ hiển thị. Nếu không thể chia hợp lý, tìm một ảnh/sơ đồ có sẵn bao quát các chủ thể đó.

- Tên tag **không dấu, gạch nối**: `pearce`, `meredith`, `sung-lewis`, `dan-emu`, `lua-mi`, `ban-do`, `so-lieu-986`.
- **Mỗi ảnh chỉ được xuất hiện 1 lần trong toàn bộ video**, kể cả các nhịp cách xa nhau. Với chủ thể được nhắc lại, tìm ảnh khác đúng chủ thể; không dùng lại cùng ảnh dưới tên file, kích thước hoặc bản cắt khác.
- **Mỗi meme tối đa 2 lần trong toàn bộ video**, không dùng cùng meme ở hai nhịp liền nhau. Mặc định ưu tiên meme chưa dùng; lần thứ 2 chỉ khi vẫn phù hợp với cảm xúc và cách đủ xa lần đầu. Đếm theo nội dung/cảnh meme, không theo tag hoặc tên file: bản đổi tên, cắt ngắn, đổi độ phân giải hoặc chuyển định dạng vẫn là cùng meme. Quy tắc meme áp dụng cả meme dạng ảnh; ảnh minh hoạ nội dung vẫn chỉ được dùng 1 lần.
- Trước khi giao, thống kê số lần dùng từng meme trong bảng phân cảnh thực tế. Nếu app bốc ngẫu nhiên mà không giới hạn số lần, chia tag theo cảnh hoặc giới hạn số nhịp của từng tag để mọi cách chọn đều không vượt 2 lần; kiểm tra cả meme trùng nội dung nằm ở các tag khác nhau. Thiếu lựa chọn thì dùng meme khác phù hợp hoặc tải thêm, không nới giới hạn, không đổi hàng loạt meme thành ảnh để né giới hạn.
- Chuẩn bị ít nhất số ảnh khác nhau bằng số nhịp cần ảnh của tag. Nếu app chỉ tránh lặp hai nhịp liền nhau, tạo tag cụ thể riêng cho từng cảnh và chỉ đặt ảnh được chọn vào tag đó để tránh app chọn lại ảnh cũ. Độ khớp nội dung quan trọng hơn số lượng; thiếu thì tìm thêm ảnh đúng nội dung.
- **1 hình / 1 nhịp.** Không để "giữ clip dòng trước" (tuỳ chọn trong app nên tắt).
- **Bắt buộc phối hợp minh hoạ nội dung và meme**, trừ khi người dùng yêu cầu phong cách khác. Mục tiêu khoảng 40–50% nhịp dùng meme khi nội dung phù hợp; không biến video thành toàn ảnh minh hoạ. Ảnh/clip/sơ đồ dùng cho giới thiệu chủ thể, hành động và giải thích hiện tượng; meme dùng cho phản ứng bất ngờ, con số gây choáng, suy ngẫm hoặc chuyển ý. Không để quá 4 nhịp liên tiếp cùng một loại khi có thể xen kẽ hợp lý.
- **Bao phủ danh từ theo cả đoạn/video, không bắt mỗi lần nhắc lại đều phải có ảnh thật.** Ví dụ: giới thiệu Proxima bằng ảnh đúng sao đó, nhịp tiếp nói khoảng cách 4,2 năm ánh sáng có thể dùng meme sốc; giới thiệu Andromeda bằng ảnh đúng thiên hà, nhịp nhấn vào 2,5 triệu năm có thể dùng meme. Giữ đủ ảnh cho chủ thể mới và sơ đồ cho lời giải thích chính, đồng thời chủ động chọn meme cho các nhịp phản ứng.
- **Không tự tạo ảnh minh hoạ / card đồ hoạ** — tải ảnh, clip hoặc sơ đồ có sẵn trên mạng và dùng meme có sẵn khi phù hợp.
- Tag = **thư mục theo chủ thể** cho ảnh thật, **thư mục theo cảm xúc** cho meme.
  App ưu tiên chọn video hơn ảnh trong thư mục nên thư mục ảnh thật không nên trộn file meme.

Bảng chọn theo nội dung:

| Nội dung đang nói | Loại | Thư mục |
|---|---|---|
| Chủ thể/sự kiện đang kể (emu, lính, ruộng lúa, súng) | ảnh thật | `emu`, `cuu-binh`, `lua-mi`, `sung-lewis`, `dan-emu-tan`, `ngam-ban`, `rut-quan`, `nong-dan`, `dat-can-coi`, `chien-dich-2`, `bao-chi` |
| Con số/khoảng cách/tốc độ | ảnh hoặc sơ đồ đúng đối tượng và quan hệ đang nói | `toc-do-anh-sang`, `anh-sang-mat-troi-trai-dat`, `khoang-cach-proxima` |
| Tên riêng cụ thể | ảnh đúng người/vật/địa điểm đó | `proxima-centauri`, `andromeda` |
| Danh từ mới hoặc hình ảnh so sánh | ảnh thể hiện trực tiếp danh từ/cảnh đó | `nha-thien-van`, `ngam-sao-mat-thuong`, `sach-lich-su` |
| Câu punchline, thất bại "chẳng ăn thua" | meme | `cuoi`, `ngan` |
| Chạy trốn, hoảng loạn | meme | `hoang` |
| Đau, hư hại, kẹt đạn | meme | `dau` |
| Khen, kết quả tốt, 0 thương vong | meme | `khen` |
| Buồn, rút quân, suy thoái | meme | `buon` |
| Nghi ngờ, "hold up" | meme | `khohieu` |
| Mở đầu / kết thúc | hình đúng nội dung câu; meme nếu phù hợp | tag chủ thể hoặc `modau` / `ketthuc` |

## 6. Quy trình tải minh hoạ

1. Lập bảng bao phủ danh từ/chủ thể và hành động theo từng nhịp ở mục 5, rồi mới gom tag. Không bắt đầu bằng cách chọn tag cảm xúc từ thư viện.
2. Với mỗi chủ thể/cảnh còn thiếu, tìm bằng tên chính xác và hành động/mối quan hệ, dùng cả từ khoá tiếng Việt và tiếng Anh khi hữu ích. Tìm từ **bất kỳ nguồn công khai nào trên mạng**: công cụ tìm ảnh, website chuyên ngành, cơ quan khoa học, báo chí, Wikimedia, kho ảnh, v.v. Không giới hạn nguồn hoặc chỉ tìm ảnh PD/CC0/CC BY.
3. Mở trang nguồn, xem ảnh ứng viên để kiểm tra đúng chủ thể, cảnh và ngữ cảnh. Sau khi tải, mở file để kiểm tra ảnh thực tế, độ nét, khả năng cắt khung và việc file có phải trang HTML/ảnh lỗi hay không. Không coi tên file hoặc kết quả tìm kiếm là bằng chứng ảnh khớp.
4. **Tự tải ảnh phù hợp, không cần hỏi lại về bản quyền cho từng ảnh.** Người dùng đã chọn tự xử lý quyền sử dụng sau. Không loại ảnh chỉ vì giấy phép hạn chế hoặc chưa rõ; không dừng tải để chờ xác minh giấy phép. Ghi đúng thông tin có trên nguồn, không suy đoán ảnh là miễn phí hay đã được cấp quyền. Nếu không thấy thông tin, ghi "chưa rõ — người dùng xử lý sau". Không vượt đăng nhập, paywall hoặc biện pháp chặn truy cập; nguồn không tải được thì tìm nguồn khác.
5. Tải bằng Python + `User-Agent` mô tả khi cần:
   ```python
   req = urllib.request.Request(url, headers={"User-Agent": "VideoMakerLocal/1.0 (personal video project)"})
   ```
   Ưu tiên bản `iiurlwidth=1600` (nhẹ, đủ nét cho khung 960×560).
   Có thể dùng Playwright chụp vùng ảnh, sơ đồ hoặc nội dung trang phù hợp khi cần. Cắt bỏ thanh công cụ, popup và phần không liên quan; kiểm tra ảnh chụp và ghi URL trang nguồn như ảnh tải xuống.
6. Lưu minh hoạ vào `assets/illus/<nội-dung>/<tag>/<tên-ngắn>.<đuôi-file>`; lưu meme dùng chung vào `assets/memes/<tag>/`. Tag phải đủ cụ thể để app không chọn nhầm ảnh khác chủ thể trong cùng thư mục. Thư mục minh hoạ không trộn meme.
7. Ghi nguồn vào `assets/illus/<nội-dung>/SOURCES.txt` hoặc `assets/memes/SOURCES.txt`: file — chủ thể/nhịp sử dụng — tác giả nếu có — giấy phép/tình trạng quyền sử dụng — URL trang nguồn — URL file gốc. Giữ thông tin cũ khi bổ sung ảnh mới.
8. Chốt bảng minh hoạ với file cụ thể cho từng nhịp và rà lại danh sách danh từ/chủ thể trên toàn video. Chủ thể mới chưa được minh hoạ thì tiếp tục tìm, không lấp bằng meme hoặc ảnh chung chung. Với chủ thể đã có ảnh, chọn thêm meme ở các nhịp phản ứng theo mục 5. Nếu vẫn thiếu ảnh phù hợp có thể tải, báo chính xác chủ thể còn thiếu, không đánh dấu hoàn tất.
9. Kiểm tra ảnh không lặp và từng meme không quá 2 lần trên toàn video. Đối chiếu thư viện với nhu cầu vừa dùng rồi viết Phần C: các meme nên bổ sung cho lần sau, ưu tiên nhóm thiếu biến thể.
10. Chạy checklist mục 10 rồi mới giao.

> Ghi chú kỹ thuật: thư mục `assets/` do app tạo nên sandbox của agent có thể chặn ghi → xin quyền
> (danger-full-access) cho đúng một lệnh copy/tải, và chỉ định rõ thư mục đích.

## 7. Đầu vào đặc biệt: post Threads (card + đọc nguyên văn)

Khi người dùng đưa **link post Threads** thay vì một đoạn văn, đây là quy trình riêng — không áp dụng
các quy tắc tải ảnh minh hoạ ở mục 5–6.

1. Chạy scraper có sẵn (Playwright headless, không tốn phí):
   ```powershell
   .\.venv\Scripts\python.exe -m videomaker.threads_shot "<link>" --content <nội-dung> --tag post --top 4
   ```
   Kết quả trong `assets/illus/<nội-dung>/post/`: `01-post-<handle>.png`, `02-cmt-<handle>.png`… (rộng 1080,
   cao theo nội dung — tối đa 640),
   `threads.json` (dữ liệu đã bóc) và `script.txt` (kịch bản sinh sẵn). Trong app: tab **Threads** →
   *1. Lấy bài + comment* → sửa **kịch bản chữ** ngay trong ô → *2. Chuyển thành Các nhịp*.
   Kịch bản chữ có một mục `# <đường-dẫn-ảnh>   (mô tả)` cho mỗi card, bên dưới là từng nhịp đọc;
   app đọc lại đúng các mục đó (`threads_shot.parse_sections`) nên sửa/thêm/bớt dòng đều được, và
   cột clip của mỗi nhịp luôn là ảnh của mục chứa nó. Không muốn comment nào vào video thì tích ở ô
   **Comment muốn xoá** rồi bấm **🗑 Xoá comment đã chọn**: ảnh của comment đó bị xoá, mục tương ứng
   trong kịch bản chữ bị bỏ (bài gốc luôn giữ, các dòng bạn đã sửa vẫn nguyên).
2. **Lời đọc = nguyên văn** `post.text`, rồi `comments[].text` theo like giảm dần. Không viết lại, không
   thêm câu dẫn, không bỏ câu, không sửa chính tả/viết tắt của tác giả (`ko`, `b hít zô`, `ctrinh`).
   Chỉ được: chia nhịp, thêm tag, chuyển số viết bằng chữ sang chữ số.
   Ngày giờ / tuổi bài ("2 giờ", "26 thg 10", "26/10/2026") **đã hiện ở header card** nên không bao giờ
   đưa vào lời đọc — `card_from_raw` đã lọc bằng `is_dateish()`.
3. Chia nhịp theo mục 3 (7–14 từ). Dùng `threads_shot.split_beats()`, `mark_emphasis()`,
   `build_editable_script()` thay vì tự chia tay; chúng giữ nguyên từng chữ và ưu tiên cắt ở dấu câu /
   ranh giới ngoặc kép. `threads_shot.parse_sections()` đọc lại bản đã sửa để dựng bảng nhịp.
   Thứ tự comment luôn tính lại theo like **mỗi lần lấy bài**: Threads dùng danh sách ảo, gỡ card khỏi
   DOM khi cuộn và xếp lại comment, nên scraper gom dần qua từng lượt cuộn (`crawl()`), không đọc một
   lần ở cuối trang (đọc kiểu đó mất đúng các comment nhiều like nhất ở đầu trang).
4. **Mỗi nhịp dùng đúng ảnh của bài/comment chứa nó** — ghi thẳng tên file vào cột clip:
   `post/01-post-uidasoda.png` cho mọi nhịp của bài gốc, `post/02-cmt-truogg36x.png` cho mọi nhịp của
   comment đó… Đây là ngoại lệ của quy tắc "mỗi ảnh chỉ xuất hiện 1 lần": một ảnh card phải theo suốt
   đoạn văn của nó. Không để trống cột clip (app sẽ bốc ảnh khác) và không chỉ ghi tag trần `[post]`.
5. Bố cục: card phủ **đủ bề ngang** khung overlay (`meme_w = 1080 − 2×lề ngang`, mặc định 1060)
   nên card vuông, dọc hay ngang đều cách mép trái/phải như nhau và không bị cắt nội dung.
   Chiều cao khung tự nở theo card cao nhất của cảnh (tab Threads tự tính, không còn dùng
   `threads_max_height`), nên mọi card kết thúc ở cùng một đường đáy chung. Chữ chạy **sát ngay
   dưới** card: neo **mép trên** ngay tại đáy chung, cách card 0px, không đổi dù card cao thấp
   hay chữ 1–2 dòng. Card quá cao (dài hơn vùng an toàn) tự thu chiều cao để không tràn khung/chữ.
   Nhịp không phụ đề (`|| -`) canh **giữa dọc** khung (tâm y=738) chứ không dính đáy.
   Trên card, cỡ chữ cố định ~52px (không phóng to khi bài ngắn), header (avatar + ngày) dính mép
   trên, footer (like/bình luận) dính mép dưới; card không in dòng nguồn/link ở đáy.
   Bài dài quá 640px mới hạ cỡ chữ, cuối cùng mới cắt bớt.
6. Nhấn mạnh `*…*`: chỉ đánh vào **số liệu** và **chữ tác giả cố ý viết HOA** (`KHÔNG`). Văn nói trên
   Threads không có "từ khoá" đúng nghĩa — bọc từ dài nhất sẽ ra nhấn mạnh vô nghĩa (`*Thực* ra`,
   `*Vạn* lý trường thành`), nên **thà không nhấn còn hơn nhấn bừa**. Đây là ngoại lệ của quy tắc
   "mỗi nhịp bắt buộc có ≥1 cụm nhấn mạnh" ở mục 4.
7. Chế độ ảnh: `auto` — post có ảnh/clip thì chụp nguyên card của Threads, post chỉ có chữ thì dựng card
   (cùng rộng 1080, cao theo nội dung). `--mode shot|card` để ép.
   Danh tính trên card (`--ident`): mặc định `avatar` = ảnh đại diện + chữ "Threads" (không lộ tên tài
   khoản); `full` = avatar + tên; `no-avatar` = ẩn avatar giữ tên; `anon` = ẩn cả hai. Với `avatar`,
   ảnh chụp cũng bị ẩn link tên trong DOM trước khi chụp (giữ avatar + giờ đăng) nên không lộ tài
   khoản; `no-avatar`/`anon` thì mọi post tự chuyển sang dựng card.
   Ảnh chụp bị tối (lớp phủ đăng nhập) hoặc lỗi sẽ tự bỏ và dựng card thay thế.
8. Không tải ảnh minh hoạ thêm, không chèn meme: nội dung là phát ngôn của người khác, hình phải là chính
   post/comment đó.
9. `threads.json` giữ `post.image` + `comments[].image` để đối chiếu; `script.txt` là bản đã gắn đúng ảnh
   cho từng nhịp.

## 8. Đăng / hẹn giờ lên Facebook Page

Video đã xuất trong `output/` được đăng bằng Graph API qua `fb_post.py` + tab **Đăng Facebook**.
Hẹn giờ là hẹn giờ *của Facebook*: video tải lên ngay, Facebook tự đăng lúc đã hẹn, app tắt vẫn chạy.

### 8.1 Cấu hình một lần (khuyến nghị: dùng biến môi trường)

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

### 8.2 Đăng hàng loạt (luồng chính — một nút)

Tab **Đăng Facebook** đã điền sẵn mọi thứ; bạn chỉ xem lại rồi bấm:

1. **1. Video cần đăng** — danh sách video trong `output/` (mới nhất trước), video đã hẹn trước đó
   để trống; chọn nhịp đăng **2/ngày** (11:30 + 20:00) hoặc **1/ngày** (20:00).
   App tự xếp giờ trống kế tiếp (bỏ qua mốc giờ đã hẹn) → bảng xem trước hiện `Video | Giờ đăng | Caption`.
2. **2. Caption** — để trống ô **Caption chung** thì mỗi video tự soạn caption từ bài Threads đã tạo ra nó
   (bản nháp đầu theo skill `facebook-reels-caption`). Viết vào ô chung thì cả loạt dùng chung.
   **✨ Gợi ý 3 caption** vẫn có để bạn tự chọn phương án cho caption chung.
3. Bấm **✅ Đăng lên lịch tất cả** — video tải lên, Facebook tự đăng đúng giờ; app tắt vẫn chạy.
   Sau khi xong, video đã hẹn được bỏ khỏi danh sách chưa đăng.

Giờ hẹn phải cách hiện tại **≥ 11 phút** và **≤ 30 ngày**; video tối đa 1 GB.

### 8.3 Tuỳ chọn: hẹn một video với giờ tự chọn

Mở accordion **⚙ Tuỳ chọn: hẹn một video với giờ tự chọn** để chọn video, gõ giờ tay
(`28/10/2026 20:00`) hoặc bấm nhanh **Tối nay 20:00 / Trưa mai 11:30 / Tối mai 20:00**,
tích **Đăng ngay** nếu không hẹn giờ. Ô giờ được xoá sau khi hẹn xong để tránh bấm nhầm hai lần.

### 8.4 Quản lý bài đã hẹn

**↻ Tải danh sách** xem các bài đang chờ (`is_published=false`), chọn một bài rồi **🗑 Huỷ bài đã chọn**
để huỷ (bài bị huỷ sẽ về lại danh sách chưa đăng). Chỉ đăng được lên **Page**, không đăng được trang
cá nhân. Reels/Stories không có hẹn giờ native.

### 8.5 Caption tự động

> Caption sinh tự động chỉ là **bản nháp theo công thức** (không có LLM trong app): chữ lấy từ chính
> bài/comment, không thêm số liệu. Muốn caption sắc hơn thì nhờ agent viết theo skill
> `facebook-reels-caption` rồi dán vào ô caption.

- **↩ Điền nguyên văn bài đã chọn** lấy đúng `post.text` của bài Threads trong dropdown.
- **# Chèn hashtag vào caption** nối khối hashtag, bỏ trùng, **bỏ tag chung chung**
  (`#viral`, `#reels`, `#xuhuong`, `#thinhhanh`, `#fyp`…) và **tối đa 5 tag**; tag bị bỏ
  được liệt kê ngay dưới ô hashtag.

## 9. Không tự tạo card đồ hoạ

## 9. Không tự tạo card đồ hoạ

Không tự tạo card/ảnh minh hoạ. Dùng ảnh/clip/sơ đồ tải về đúng nội dung; meme chỉ dùng theo tiêu chí mục 5.
(`tools/card_gen.py` chỉ giữ lại để tham khảo, không dùng.)

**Ngoại lệ:** card Threads do `threads_shot.py` dựng lại từ dữ liệu đã bóc (mục 7) — đó là ảnh chụp nội
dung thật, không phải đồ hoạ tự bịa.

## 10. Checklist trước khi giao

- [ ] **Mọi ảnh/clip** — minh họa theo nội dung (`assets/illus/<nội-dung>/<tag>/`) và meme (`assets/memes/<tag>/`) — đều đã tải sẵn trước khi giao.
  ở cuối checklist, `bad` phải rỗng; thiếu thì tải bổ sung trước khi giao, không giao kịch bản "nợ" hình.
- [ ] Mỗi nhịp có tag và ≥1 file phù hợp trong `assets/illus/<nội-dung>/<tag>/` hoặc `assets/memes/<tag>/`. Có file chưa đủ: đã mở ảnh và xác nhận khớp đúng chủ thể/hành động của nhịp.
- [ ] Danh sách danh từ/chủ thể quan trọng đã được bao phủ bằng ảnh cụ thể; tên riêng đúng đối tượng, cảnh quan hệ có đủ các thành phần cần thiết. Không bỏ sót chủ thể chỉ vì thiếu ảnh trong thư viện cũ.
- [ ] Có cả minh hoạ nội dung và meme, mục tiêu khoảng 40–50% nhịp meme khi phù hợp. Mỗi chủ thể quan trọng đã có ảnh ở nhịp giới thiệu/giải thích; meme ở nhịp phản ứng không bị đánh dấu là thiếu minh hoạ chỉ vì nhắc lại danh từ hoặc số liệu.
- [ ] **Không ảnh minh hoạ nội dung nào lặp lại trong toàn video; mỗi meme tối đa 2 lần**, kể cả nằm ở tag khác. Đối chiếu file, hash và nội dung để phát hiện bản sao đổi tên/đổi kích thước/cắt lại. Không lặp cùng meme ở hai nhịp liền nhau; phân bổ ưu tiên meme chưa dùng. Giữ phối hợp ảnh và meme theo mục 5 khi thay tài nguyên trùng. (Post Threads: cùng một card dùng cho mọi nhịp của đoạn văn đó — xem mục 7.)
- [ ] Có thống kê meme đã dùng (tên/cảnh, số lần và nhịp xuất hiện) và **Phần C — Meme nên tải thêm cho lần sau**, gắn với những thiếu hụt thực tế của thư viện; các đề xuất có tình huống, số clip cần thêm, tag và từ khoá tìm.
- [ ] Số liệu chính xác nằm trong chữ hiển thị. Nhịp giải thích phép đo/quan hệ có ảnh hoặc sơ đồ tương ứng; nhịp gây bất ngờ bằng con số được dùng meme khi đối tượng đã có minh hoạ trong đoạn. Không bắt buộc ảnh gốc phải in sẵn số và không dùng sơ đồ có số mâu thuẫn lời đọc.
- [ ] Mỗi file tải có nguồn và tình trạng quyền sử dụng được ghi trung thực; giấy phép chưa rõ đã ghi để người dùng xử lý sau, không dùng làm lý do bỏ thiếu minh hoạ.
- [ ] Với kịch bản thô: đối chiếu bản biên tập với đầu vào để giữ đủ ý chính, đúng tên riêng và số liệu. Với bản yêu cầu nguyên văn: ghép lời đọc các nhịp và kiểm tra không thiếu/thừa từ, trừ chuẩn hóa TTS được phép. Sau khi chia nhịp, không tự sửa thêm lời văn đã chốt.
- [ ] Đối chiếu từng cặp hai bên `||`: bỏ dấu `*`, không phân biệt hoa/thường và quy đổi phần số về cùng dạng thì phải khớp toàn bộ từ, đúng thứ tự. Chỉ cho phép chuẩn hoá số và dấu ngắt câu theo mục 4; sai thì sửa trước khi giao.
- [ ] Không rút gọn chữ hiển thị để vừa khung hoặc đạt số từ. Nếu chia nhịp, chia đồng thời cả hai bên `||`; số liệu đã dùng chữ số, giữ nguyên đơn vị và các từ còn lại.
- [ ] **Mỗi nhịp có ít nhất 1 cụm `*NHẤN MẠNH*` ở bên phải `||`**, kể cả nhịp không có số; mọi số quan trọng đều được nhấn mạnh. Dấu `*` phải đủ cặp và chỉ bao quanh từ/cụm từ có sẵn. (Post Threads: bỏ trống cũng được khi không có số/chữ HOA — xem mục 7.)
- [ ] Kiểm tra thư viện khớp kịch bản (minh họa nội dung + meme):
  ```powershell
  .venv\Scripts\python.exe -c "from videomaker import pipeline as pl; from pathlib import Path; lib=pl.scan_memes(); ill=pl.scan_illust('ten-noi-dung'); rows=pl.analyze(Path('duong-dan-kich-ban.txt').read_text(encoding='utf-8'), content='ten-noi-dung'); bad=[r for r in rows if not r[4]]; print(len(rows),'nhịp, thiếu clip:',len(bad))"
  ```
  (Thay `ten-noi-dung` và `duong-dan-kich-ban.txt` bằng nội dung và file kịch bản đang làm. `bad` phải rỗng — nếu không thì bổ sung file cho tag đó.)
- [ ] Đã lưu `kich-ban.txt`, media và nguồn; bàn giao để người dùng kiểm tra. Chỉ khi người dùng yêu cầu render/xuất video mới thử khung hình bằng nút "👁 Xem thử bố cục" trước khi xuất.

## 11. Ví dụ

Đầu vào:
> Năm một nghìn chín trăm ba mươi hai, quân đội Úc được điều đi đối phó với một đàn chim. Đó là chim emu, loài chim không biết bay.

Đầu ra:

```
[linh-uc-1932] Năm một nghìn chín trăm ba mươi hai, || NĂM *1932*,
[linh-uc-emu] quân đội Úc được điều đi đối phó với một đàn chim. || QUÂN ĐỘI ÚC ĐƯỢC ĐIỀU ĐI ĐỐI PHÓ VỚI MỘT *ĐÀN CHIM*.
[emu] Đó là chim emu, loài chim không biết bay. || ĐÓ LÀ CHIM EMU, LOÀI CHIM *KHÔNG BIẾT BAY*.
```

Tag `linh-uc-1932` → ảnh lính Úc đúng bối cảnh năm 1932; `linh-uc-emu` → ảnh/sơ đồ có sẵn thể hiện lính Úc đối phó đàn emu; `emu` → ảnh emu ngoài tự nhiên. Không dùng meme mở đầu hoặc ảnh chim bất kỳ để thay các chủ thể này.
