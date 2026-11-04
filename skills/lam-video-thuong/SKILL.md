---
name: lam-video-thuong
description: Flow video thường: biên tập kịch bản thô thành kịch bản 16-18 nhịp (mạch kể + format app + ảnh thật bám sát kịch bản, không dùng meme) rồi dừng ở bàn giao; và khi người dùng ra lệnh "Làm video" thì tự chọn sự kiện trong ngày (Wikipedia On This Day), tự tìm ảnh và dựng tới mp4. Dùng cho mọi video không thuộc flow Threads.
---

# SKILL: Làm video thường

Hai chế độ, dùng chung một bộ luật viết ở PHẦN 1:
- **Người dùng đưa kịch bản thô** → biên tập theo PHẦN 1, bàn giao kịch bản + media, **dừng ở bàn giao**.
- **Lệnh "Làm video"** → chạy thêm PHẦN 2 (tự tìm sự kiện, tự dựng tới mp4).

Video Threads không dùng skill này; xem `skills/lam-video-threads/SKILL.md`.

## PHẦN 1 — VIẾT KỊCH BẢN, ĐỊNH DẠNG VÀ MINH HOẠ

Mục tiêu: nhận **một đoạn văn liền mạch** (không tag, không `||`), trả về **kịch bản dán thẳng vào app**
và **tải sẵn ảnh thật** vào `assets/illus/<nội-dung>/<tag>/` (mỗi tag một chủ thể/hành động trong kịch bản). **Không dùng meme** — mọi nhịp có ảnh riêng, ảnh phải minh họa đúng nội dung đang đọc.

## Ba tầng ưu tiên

1. **Mạch kể** — bài phải là một câu chuyện liền, không phải chuỗi dữ kiện đặt cạnh nhau. Tầng này gãy thì bản viết chưa xong.
2. **Format** — số từ, âm tiết, cụm 2–4 từ, nhấn mạnh, parity lời đọc/chữ hiển thị.
3. **Media** — ảnh thật đúng chủ thể + hành động, hash, nguồn.

Khi một luật ở tầng 2 hoặc 3 bẻ gãy mạch ở tầng 1, áp đúng ngoại lệ đã ghi cho luật đó; **không viết lại mạch để tuân luật**.

## Nguyên lý nền — vì sao quy trình này tồn tại

Tò mò là **khoảng trống kiến thức mà người xem tin mình lấp được** (Loewenstein 1994). Ba hệ quả chi phối mọi luật dưới đây:

- Người xem phải **đã biết một thứ** thì mới **thấy thiếu một thứ**. Hook chỉ có tên riêng lạ thì không tạo tò mò: phải neo vào cái quen (NEO) rồi phá kỳ vọng (LỆCH).
- Khoảng trống không được quá to (không hiểu gì) hay quá nhỏ (đã đoán ra). Tò mò mạnh nhất khi người xem đoán được vài phần nhưng chưa chắc.
- **Spoiler đóng khoảng trống.** Hook nêu mâu thuẫn, không nêu lời giải.

Giữ chân là việc của phần thân, không phải của hook: thân phải liên tục mở câu hỏi nhỏ mới trước khi trả lời xong câu cũ. Thông tin mới chỉ giữ người xem khi nó **giải thích hoặc đảo ngược** điều trước đó; thêm dữ kiện chỉ cho "đủ thông tin" là đổ nước vào bài.

**Giọng TTS phẳng, không có cảm xúc.** Cảm xúc và độ nhấn không đến từ giọng đọc mà từ ba kênh còn lại: **nội dung** (đối lập, số có thang so sánh, trớ trêu nói thẳng bằng dữ kiện), **ảnh** (cắt đúng lúc, đúng nội dung đang đọc), và **chữ nhấn + khoảng nghỉ** (dấu chấm cuối nhịp = nghỉ dài). Vì vậy kịch bản dùng giọng **chia sẻ kiến thức / thuyết minh**: rõ, chắc, trung tính; và mọi sức hút phải nằm sẵn trong chữ, không được trông vào cách đọc. **Không dùng meme**: meme là kênh cảm xúc thay thế cho chữ, mà kênh hình giờ phải chở nội dung kiến thức — mỗi nhịp một ảnh thật đúng điều đang đọc.

**Nguyên tắc tổ chức: viết cho người xem trước, định dạng sau — hai việc này không được làm cùng lúc.** Luật ở mục 3–5 là gate hậu kiểm; nghĩ sẵn theo mảnh ≤24 âm tiết thì mạch không còn chỗ hình thành.

## Quy trình viết — 6 bước, bắt buộc theo thứ tự

### BƯỚC 0 — Chọn câu hỏi trung tâm (CQ)

Cả video là câu trả lời cho **một** câu hỏi, viết ra thành chữ: "Vì sao / Làm sao [điều quen thuộc] lại [điều ngược kỳ vọng]?".

Phép thử CQ — trượt một câu là đổi góc hoặc đổi sự kiện, **không viết tiếp**:

1. Người xem Việt Nam chưa biết gì về sự kiện này có hiểu CQ không? (khoảng trống không quá to)
2. Họ có đoán được vài phần nhưng không chắc không? (không quá nhỏ)
3. Câu trả lời có nằm trong nguồn không? (không bịa lời giải)

### BƯỚC A — Sổ dữ kiện có nhãn

Liệt kê 10–15 dữ kiện từ nguồn. Mỗi dòng giữ **cột quan hệ** với dữ kiện khác (`A dẫn đến B`, `A đối lập B`, `A xảy ra trước B`, `A là một phần của B`, `chưa rõ`) và gắn **0–2 nhãn sức hút**:

| Nhãn | Nghĩa |
| --- | --- |
| `NEO` | Thứ người xem Việt đã biết hoặc hình dung ngay (quân đội, súng máy, nông dân, chim) |
| `LỆCH` | Điều đi ngược kỳ vọng so với NEO |
| `SỐ` | Con số quy ra thang đời thường được (mười viên đạn mới trúng một con) |
| `NGƯỜI` | Chi tiết nhân vật, lời nói, hành động cụ thể |
| `TRỚ TRÊU` | Kết quả ngược với mục đích |
| `LEO` | Mức cược/độ lạ tăng so với dòng trước |

**Cổng bước A:** ≥1 `NEO`, ≥1 `LỆCH`, ≥1 `TRỚ TRÊU` hoặc `SỐ`, ≥2 `LEO`. Thiếu `LỆCH` nghĩa là sự kiện chưa đủ hấp dẫn hoặc nguồn quá mỏng: đọc bài đầy đủ + ít nhất một nguồn thứ hai (không chỉ dòng tóm tắt On This Day) rồi mới tính chuyện đổi sự kiện.

Chỉ ghi quan hệ mà nguồn nêu hoặc chứng minh được; suy đoán thì ghi `chưa rõ`. **Câu viết ở bước C chỉ được diễn đạt đúng các quan hệ có trong sổ này** — đây là cách giữ liền mạch mà không bịa.

### BƯỚC B — Bản đồ nhịp truyện (chưa viết lời)

Xếp dữ kiện đã chọn vào khung; mỗi mũi tên là "nhưng" hoặc "vì vậy", không phải "và rồi":

```
HOOK (NEO + LỆCH, không lộ lời giải)
 → BỐI CẢNH ngắn (1–3 nhịp, chỉ đủ để hiểu LỆCH)
 → THỬ LẦN 1 —nhưng→ LỆCH nhỏ
 → vì vậy THỬ LẦN 2 (cược cao hơn) —nhưng→ LỆCH lớn hơn    ← leo thang
 → ĐẢO CHIỀU / chi tiết khó tin (TRỚ TRÊU hoặc SỐ)
 → PAYOFF trả lời CQ
 → CALLBACK: quay lại câu hook, nay mang nghĩa khác. Dừng.
```

**Mạch hở (open loop) mỗi 3–4 nhịp:** trước khi đóng câu hỏi hiện tại phải gợi một điều cụ thể sắp tới ("nhưng con số thật còn tệ hơn nhiều"). Cấm kiểu rỗng: "chuyện chưa dừng ở đó", "điều bất ngờ đang chờ".

Ghi bản đồ ra, đánh dấu vị trí hook, từng mạch hở, điểm đảo chiều. Thiếu một trong ba thì quay lại bước A.

### BƯỚC C — Viết xuôi bằng giọng chia sẻ kiến thức

Viết **150–200 từ (ngân sách tham khảo)** theo giọng **người dẫn chương trình kiến thức**: rõ, chắc, trung tính, như thuyết minh phim tài liệu. Chưa nghĩ đến nhịp, tag, ảnh, âm tiết hay chữ hiển thị.

Ngân sách này chặn viết lan man, **không phải để bỏ dữ kiện**. Sổ ở bước A có nhiều dữ kiện đạt thì bản văn dài hơn và chỉ cần khai số từ thật; cấm cắt dữ kiện cho khớp chữ. Muốn ngắn thì bỏ dữ kiện ở **bước A**, lúc chưa viết.

- Câu ngắn, chủ ngữ rõ, **chủ động**, mỗi câu một ý. Văn nói chuẩn mực, không tiếng lóng, không cảm thán.
- **Không có câu thái độ.** Thay bằng **câu đối chiếu**: đặt hai dữ kiện cạnh nhau để sự lệch tự lộ ("Hai khẩu súng máy, 10.000 viên đạn. Đối thủ: một đàn chim."). Mức sốc của con số do **phép quy đổi tính từ số trong nguồn** tạo ra ("mười viên đạn mới trúng một con"), không do tính từ ("kinh ngạc", "thật bất ngờ").
- **Trớ trêu nói thẳng bằng quan hệ, không bằng bình luận**: "Người từng từ chối cấp tiền, về sau tặng cả mảnh đất." — đúng rồi, không cần thêm "thật trớ trêu".
- **Cặp số đối chiếu là thiết bị bắt buộc**: mỗi video phải có ít nhất một chỗ đặt hai đại lượng cùng loại cạnh nhau theo tỷ lệ tính được từ nguồn (10.000 viên : 986 con; 66 tranh : 50 bức vẽ). Nguồn không cho cặp số nào thì đổi góc hoặc đổi sự kiện — đó là tín hiệu nguồn mỏng, không phải chỗ để lấp bằng tính từ.
- Với chỗ cần mở câu hỏi, ưu tiên **câu khẳng định nêu chỗ lệch** ("Nhưng có một điều không khớp: …") hơn câu hỏi tu từ — giọng TTS đọc ngữ dấu "?" kém, và câu hỏi bỏ lửng không ai trả lời bằng giọng đọc.
- **Từ/cấu trúc cấm trong lời đọc**: cảm thán và bình luận cảm xúc ở dạng cụm — "thật bất ngờ", "thật kinh ngạc", "thật khó tin", "thật trớ trêu", "thật vô lý", "quả là", "không thể tin", "đáng ngạc nhiên", "nghe vô lý"; và chữ văn viết — "được điều đi", "tiến hành", "nhằm", "tuy nhiên", "do đó", "đáng chú ý là", "cụ thể là", câu bị động dài, mở đầu bằng "Vào năm X". "Thật" trần trong "sự thật", "chân thật", "thật thà" không bị cấm — máy chỉ chặn cả cụm.
- **Chốt hook theo sức tò mò trước, ảnh sau.** Viết 3 hook theo 3 công thức dưới đây, chọn cái khiến người xem hỏi ra một câu cụ thể nhất:
  1. **Phá kỳ vọng:** [chủ thể quen] + [hành động không hợp] + [mẩu kết quả]. "Quân đội Úc mang súng máy ra đánh một đàn chim. Và không thắng nổi."
  2. **Số lệch:** con số quy ra đời thường. "Mười viên đạn mới hạ được một con."
  3. **Nghịch lý nhân vật:** người giỏi nhất làm việc ngược lẽ.
  4. **Cảnh giữa chừng:** mở ngay giữa hành động, giải thích sau.
  5. **Kết quả trước, nguyên nhân sau:** chỉ khi kết quả đủ lạ.
- **Hard gate hook:** bỏ tên riêng ra, câu vẫn phải còn một quan hệ/đối lập/chi tiết cụ thể; câu còn đúng với hàng nghìn sự kiện tương tự thì loại. Hook không được giải thích hết kết quả; payoff phải trả lời đúng câu hỏi hook mở ra.
- **Hook phải tự nêu chủ thể bằng danh từ chung** ("một bảo tàng", "quân đội Úc", "chiếc cầu"), không được dồn việc gọi tên chủ thể sang nhịp 2. NEO nằm ở **loại sự vật**, không nằm ở tên riêng: người xem chưa biết "Mô-ma" nhưng biết "bảo tàng" là gì, nên mất danh từ chung là mất NEO. Phép thử khi chốt: **che nhịp 2, chỉ đọc nhịp 1 — có biết đang nói về cái gì không?** Không biết thì khoảng trống quá to, viết lại.
- **Ba phép thử trước khi chốt:** (1) đọc thành tiếng — câu có tự nhiên như lời mở video không; (2) hỏi "người xem đang muốn biết điều gì tiếp theo?" — phải trả lời được bằng một câu hỏi cụ thể; (3) che hook và nhìn ảnh bookend — ảnh phải chứng minh được chủ thể/hành động hoặc quan hệ cốt lõi, không chỉ cùng chủ đề. Trượt một phép thử thì viết lại.
- **Đa dạng hook giữa các video:** không mặc định mở bằng ngày/năm; mốc thời gian chỉ lên hook khi nó chính là chi tiết lệch. Trước khi chốt, đối chiếu các video gần đây để không lặp cùng kiểu mở đầu.
- **Bốn cổng rõ nghĩa** — viết xong câu nào, đọc câu ấy qua đủ bốn câu hỏi rồi mới sang câu sau. Đây là bốn chỗ người xem từng phải bắt hộ:
  1. **Tên riêng phải có neo.** Tên lần đầu xuất hiện phải đứng ngay sau một danh từ chỉ loại ("thành phố Ba-cô", "giàn khoan Oil Rocks") hoặc đã có nhịp giới thiệu trước nó. Mất ô này là câu "từ bờ Ba-cô nhìn ra" — người xem không biết Ba-cô là gì thì mốc đường không còn nghĩa.
  2. **Mốc ngày không đè mức mỗi ngày.** "Ngày 7 tháng 11, giếng cho dầu, 100 tấn một ngày" nghe thành "riêng ngày đó được 100 tấn". Mở mốc bằng "Từ/Sau" hoặc dời mốc sang nhịp khác; `lint_rows` báo khi cả hai nằm cùng một nhịp.
  3. **Không nén cụm.** "Giếng dầu đầu tiên" ép thành "giếng đầu", "cầu thép nối các giàn thành đường đi" ép thành "cầu thành đường" — gọn hơn nhưng mất nghĩa. Câu nào phải bỏ chữ mới vừa ngân sách từ/âm tiết là câu chưa xong: viết câu ngắn hơn ở bước C, không giao câu cụt cho bước cắt.
  4. **Mỗi nhịp chỉ lấy số liệu của một câu nguồn.** "5.000 người ở lại theo ca 7 ngày" là ghép sai: nguồn nói 5.000 người lúc cao điểm, còn ca 7 ngày thuộc thời 2.000 người. Nối hai con số chỉ hợp khi câu nguồn của ô 9 đã nối sẵn.


### BƯỚC D — Thử xương sống và thử người xem khó tính

**D1 — Xương sống:** tóm đoạn văn thành 5–6 câu theo mẫu `vì A nên B, nhưng C, vì vậy D, nhưng E, cuối cùng F`, mỗi câu nêu rõ quan hệ nào nối nó với câu trước. **Không có ít nhất 2 chữ "nhưng" là truyện phẳng** — quay lại bước B. Không tóm được thành chuỗi như vậy nghĩa là mạch chưa tồn tại, chưa sang bước E.

**D2 — Người xem khó tính:** đọc bản văn xuôi như người đang lướt Facebook và đánh dấu:

- 🟥 **chỗ vuốt** — cắt câu này có ai nhận ra không? Có thì giữ, không thì xoá.
- 🟨 **chỗ phải đoán** — "tôi chưa hiểu vì sao điều này xảy ra" → thêm cầu nối từ sổ dữ kiện.
- 🟦 **chỗ hỏi "liên quan gì tới tôi"** → thay bằng chi tiết cụ thể hoặc so sánh quy mô.

Sau mỗi nhịp tự hỏi "người xem đang muốn biết gì tiếp theo?"; hai nhịp liền không có câu hỏi thì thêm mạch hở hoặc gộp nhịp. Sửa xong mới sang cắt nhịp — từ đây **không sửa lời**.

### BƯỚC E — Cắt nhịp

Cắt đoạn văn đã duyệt theo mục 3: chỉ chia nhịp, gắn tag, chuẩn hóa số/dấu câu cho TTS và chọn cụm `*nhấn mạnh*`; **chữ hiển thị do bộ dựng tự sinh từ chính lời đọc** (dòng không có `||` là mặc định), không chép tay và không sửa câu cho vừa cột hiển thị. Chỗ nào phải sửa lời là chỗ bước C còn hỏng — quay lại C, không sửa tại đây. **Bảng bàn giao khai báo vai trò từng nhịp** (`tiếp nối`/`hệ quả`/`đối lập`/`ví dụ`/`chuyển ý`); nhịp không gán được vai trò là nhịp rời: viết lại ở bước C hoặc gộp vào nhịp kề, không dựng.

- **Cắt nhịp chỉ được TÁCH, không được RÚT GỌN — mọi nhịp, không riêng hook.** Buộc phải bỏ chữ để một nhịp vào ngân sách từ/âm tiết, vào cỡ cụm 2–4 từ hoặc khớp ảnh là dấu hiệu bước C chưa xong: quay lại C viết câu ngắn hơn, không cắt câu cũ thành câu cụt. Bằng chứng đạt: đọc lời đọc từng nhịp đối chiếu nguyên văn câu văn xuôi ở bước C — lệch một chữ là chưa đạt.
- **Sau mọi sửa đổi ở bất kỳ nhịp nào, chạy lại TOÀN BỘ bảng tự kiểm dưới đây**, không kiểm tra riêng nhịp vừa sửa. Một nhịp đổi có thể làm hỏng hook, callback, mạch hở và ảnh của nhịp khác.
- Nhịp ngắn 3–6 từ ở điểm đảo chiều **không có meme để dựa vào**. Sức nặng của nó đến từ ba thứ: dấu chấm cuối nhịp (nghỉ dài), chữ nhấn cỡ lớn, và cú cắt ảnh sang ảnh thật đúng nội dung đang đọc. Mỗi nhịp ngắn vì vậy bắt buộc kết bằng dấu chấm và có `*nhấn mạnh*`.
- Cảm xúc ở nhịp phản ứng do **ảnh + dữ kiện** chở, không viết thành câu bình luận. Chủ đề thương vong/tang tóc càng bắt buộc điều này: để dữ kiện tự nói.
- Không để cả bài toàn nhịp cùng cỡ: nhịp dài (≤24 âm tiết) để giải thích, nhịp ngắn để nhấn.

## Bảng tự kiểm bàn giao — 10 ô, cấm giao khi còn ô trống

Không có ô tick. Mỗi ô phải **điền chữ thật**, in kèm kịch bản khi bàn giao; ô nào không điền được thì việc ở bước tương ứng chưa xong. Đây là cách duy nhất để luật tầng 1 không bị "đã tuân" trên giấy.

| Ô | Phải viết ra | Bắt luật nào thành bằng chứng |
|---|---|---|
| 1 | CQ nguyên văn + **dòng nguồn nào trả lời nó** + nó là "vì sao" hay "trước–sau" | BƯỚC 0; nếu nguồn không có nguyên nhân thì CQ phải là trước–sau, không được viết "vì sao" |
| 2 | **3 hook ứng viên** + hook chọn + một dòng vì sao hai hook kia thua | BƯỚC C "viết 3 hook" |
| 3 | Chép riêng nhịp 1 → "chủ thể là ___, nằm ở chữ thứ ___"; trắng = vi phạm luật NEO | Hook phải tự nêu chủ thể |
| 4 | Chép nguyên văn nhịp có **hai con số** + phép quy đổi từ số của nguồn | cặp số đối chiếu |
| 5 | Xương sống 6 câu, **chữ "nhưng" viết hoa để đếm được ≥2** | D1 |
| 6 | Bảng nhịp → vai trò, kèm tổng số nhịp `đối lập` | BƯỚC E |
| 7 | Liệt kê từng **mạch hở**: nhịp nào mở câu hỏi gì, câu hỏi được trả lời ở nhịp nào | BƯỚC B |
| 8 | **Số ảnh đạt = ___, số nhịp = ___** (số nhịp không được vượt số ảnh đạt) | mục 5 + mục 6 |
| 9 | Mỗi con số **và mỗi tên riêng** trong kịch bản → **dòng nguồn cụ thể** trong `SOURCES.txt`; mỗi tên riêng kèm một dòng "là gì" (thành phố, giàn khoan, người…), không viết được dòng ấy thì bỏ tên hoặc thêm nhịp giới thiệu | chống bịa, chống nhớ đại, chống tên riêng không neo, chống nối sai hai con số |
| 10 | Ba chốt kết bài + chép nguyên văn nhịp callback | Kết bài |

Ô 1, 2, 3, 5, 7 là những ô mà kịch bản hỏng vì **không ai từng viết ra chúng**, không phải vì thiếu luật.

## Máy kiểm gì, người kiểm gì

`script_draft.lint_rows(rows)` tự báo — **mọi mục chỉ là cảnh báo, không chặn bàn giao**: đại từ/cụm chỉ định đứng đầu nhịp mà không có tên riêng nào trong 2 nhịp gần nhất; chữ văn viết và cụm cảm thán bị cấm ở bước C; nhịp 1 mở bằng "Năm/Vào năm/Ngày + số"; cả bài không có nhịp nào ≤6 từ; ≥4 nhịp liên tiếp cùng độ dài ±2 từ; cả bài không có nhịp nào chứa từ hai con số trở lên (thiếu cặp số đối chiếu); **một nhịp có quá 2 cặp `*nhấn mạnh*`** (3 cặp chỉ hợp lệ ở nhịp ≥18 âm tiết); nhịp > 24 âm tiết; **hai hàng chữ trong cùng cụm lệch nhau quá 1 từ** (đo bằng đúng `split_items` của bộ dựng); **mốc ngày kiểu "Ngày 7 tháng 11" đứng cùng nhịp với mức "100 tấn một ngày"**; viết tắt còn sót trong glossary. `pipeline.analyze(...)` báo nhịp thiếu ảnh.

**Không có gate máy** cho: parity số từ hai bên `||`, hook và câu chốt có ≥1 `*nhấn mạnh*` (nhịp chuyển tiếp được 0), độ dài cụm do bộ tách pipeline sinh ra, hash bookend, mỗi nhịp có ảnh thật chứng minh đúng lời đọc, CQ, nhãn sổ dữ kiện, mạch hở mỗi 3–4 nhịp, ≥2 chữ "nhưng" trong xương sống, ≥2 nhịp `đối lập`, ba chốt kết bài. Người viết phải tự đối chiếu — không được mặc định "máy đã bắt hộ". **Phần tự đối chiếu đó là Bảng tự kiểm bàn giao ở trên, không phải trí nhớ.**

Máy không còn báo "chuỗi nhịp không mở bằng từ nối": luật đó khuyến khích chèn "Vậy nên / Sau đó" cho đủ, nghe máy móc. Mạch do xương sống (D1) và vai trò nhịp (bước E) quyết, không do từ nối.

## Kết bài — ba chốt bắt buộc

1–2 nhịp. Không còn luật "kết bài luôn đủ 2 nhịp: một bài học + một hình ảnh hồi sinh".

- **Bắt buộc callback:** nhắc lại đúng chi tiết hook, nhưng nay mang nghĩa đã đổi; ảnh nhịp kết là ảnh bookend cùng file với ảnh hook.
- **Bài học chỉ thêm khi nguồn tự nêu.** Không lên lớp, không thêm vế đánh giá khi dữ kiện đã tự nói.
- **Không kết bằng con số thiệt hại. Không chào kết** ("cảm ơn đã xem"); video kết ngay sau nhịp khép.

Chủ đề thương vong/tang tóc: kết trang trọng, vẫn callback, không dùng giọng mỉa. Hình tưởng niệm hoặc dựng lại chỉ là **một cách** làm callback, không phải luật.

## Quy tắc biên tập và bàn giao

- Người dùng cung cấp kịch bản thô. Biên tập thành lời kể tự nhiên theo giọng **chia sẻ, cập nhật thông tin**, giữ ý chính, tên riêng và số liệu; không tự thêm tình tiết, số liệu, nguyên nhân, động cơ, kết quả hoặc quan hệ nhân–quả nếu đầu vào/nguồn không nêu hoặc không chứng minh được. Câu nối chỉ được làm rõ trật tự và quan hệ đã có trong dữ kiện, không được dùng để lấp chỗ thiếu bằng suy đoán. Nếu dữ kiện chưa đủ, nói rõ chỗ chưa xác định hoặc giữ cách diễn đạt thận trọng. Nếu người dùng yêu cầu giữ nguyên văn hoặc đưa bản đã duyệt để chỉ định dạng, giữ nguyên lời văn đó.
- Tự tìm và chuẩn bị ảnh minh họa theo mục 5–6: **mọi nhịp dùng ảnh thật** đúng chủ thể + hành động đang đọc, không dùng meme.
- Lưu kịch bản UTF-8 tại `assets/illus/<nội-dung>/kich-ban.txt` và lưu sẵn toàn bộ media trước khi bàn giao. Gửi kịch bản để người dùng kiểm tra cùng bảng ánh xạ nhịp → vai trò nhịp → tag → file, nguồn và đường dẫn thư mục. Phân biệt rõ phần đã hoàn tất và media còn thiếu.
- **Dừng ở bàn giao kịch bản và media để người dùng duyệt rồi tự làm tiếp trong app.** Không tự chạy TTS, render preview, xuất video hoặc đăng bài. Người dùng duyệt kịch bản không tự động đồng nghĩa với yêu cầu render; chỉ thực hiện khi được yêu cầu.
- Flow này dành cho video thường. Bài/comment Threads làm theo `skills/lam-video-threads/SKILL.md` (hoặc giao diện **Biên tập Threads** của app); đăng Facebook xem [docs/DANG_FACEBOOK.md](../../docs/DANG_FACEBOOK.md).

---

## 1. Đầu vào

- Một đoạn văn liền mạch (có thể có số liệu, tên người, mốc thời gian).
- Tuỳ chọn: giọng điệu (nghiêm túc / hài), độ dài mong muốn, ghi chú "chỗ này phải có hình X".
- **Mặc định biên tập kịch bản thô theo quy trình 6 bước ở trên.** Giữ ý chính và thông tin thực tế; không tự rút bỏ ý quan trọng để ép thời lượng. Với yêu cầu giữ nguyên văn hoặc bản đã duyệt chỉ cần định dạng, bỏ BƯỚC 0–D, chỉ chia nhịp, thêm tag và chuẩn hóa số/dấu câu cho TTS. Chữ hiển thị luôn khớp đầy đủ lời đọc cuối cùng.
- **Tên riêng phải đọc được bằng TTS**: nếu tên nước ngoài, thuật ngữ hoặc từ viết tắt
  khiến giọng đọc phát âm sai hoặc đánh vần máy móc, chỉ phiên âm trong phần lời đọc
  bên trái `||`; phần chữ hiển thị bên phải giữ nguyên tên gốc để người xem nhận diện.
  Vẫn giữ tên gốc trong nguồn, bảng minh họa và ghi chú nội bộ khi cần. Ví dụ:
  lời đọc `MÉT-SEN-GIƠ` nhưng chữ hiển thị `MESSENGER`.

## 2. Đầu ra (luôn đúng 3 phần)

**Phần A — Kịch bản để dán** (khối text thuần, mỗi dòng một nhịp):

```
[tag] lời đọc || CHỮ HIỂN THỊ CÓ *NHẤN MẠNH*
```

**Phần B — Bảng minh hoạ**: nhịp | **vai trò với nhịp trước** (tiếp nối / hệ quả / đối lập / ví dụ / chuyển ý) | danh từ/chủ thể và hành động cần minh hoạ | tag | file trong thư viện | lý do ảnh khớp nội dung | nguồn | giấy phép/tình trạng quyền sử dụng.
Kèm dòng cuối: đã tải về thư mục nào, còn thiếu gì.

**Phần phụ — CQ, sổ dữ kiện và xương sống** (bắt buộc kèm theo, để người dùng duyệt được mạch trước khi duyệt chữ): câu hỏi trung tâm ở bước 0, danh sách dữ kiện ở bước A kèm nhãn sức hút và quan hệ, bản đồ nhịp ở bước B (đã đánh dấu hook / mạch hở / điểm đảo chiều), **3 hook ứng viên ở bước C kèm hook được chọn và một dòng vì sao hai hook kia thua**, đoạn văn xuôi ở bước C, bản tóm xương sống 5–6 câu ở bước D, và **Bảng tự kiểm bàn giao đã điền đủ 10 ô**.

**Phần C — Ảnh cần bổ sung cho lần sau**: dựa trên nội dung vừa làm và thư viện thực tế, trình bày bảng: mức ưu tiên | chủ thể/cảnh còn thiếu | nhịp nào cần nó | thư viện hiện thiếu gì | từ khoá tiếng Việt + tiếng Anh đã thử | nguồn gợi ý (Wikimedia/LoC/Smithsonian/báo chuyên ngành) | tag lưu.
Ưu tiên các chủ thể phải dùng ảnh chung chung hoặc phải gộp nhịp vì thiếu ảnh. Đề xuất 3–5 mục hữu ích khi có thiếu hụt; nếu đã đủ thì nói rõ, không cố liệt kê cho đủ. Không đề xuất lại đúng ảnh đã có; cần bổ sung thì yêu cầu cảnh/giai đoạn khác. Không bịa link tải hoặc báo đã tải phần gợi ý. Phần này dùng để cải thiện lần sau, không thay cho việc hoàn tất ảnh/clip của bản hiện tại.

---

## 3. Chia nhịp (tầng 2 — chỉ chạy sau khi mạch đã chốt ở bước D)

Toàn bộ mục này là luật **cắt**, không phải luật **viết**. Lời văn lấy nguyên từ đoạn văn đã duyệt ở bước C–D; cắt chỗ nào phải giữ nguyên quan hệ nối giữa hai nhịp, và nhịp nào bị cắt làm mất quan hệ thì ghép lại.

- Mục tiêu **7–14 từ lời đọc / nhịp** (≈3–5 giây nói). Câu dài thì cắt theo mệnh đề, không cắt giữa cụm từ. Có thể ngắn hoặc dài hơn để giữ nguyên văn và trọn cụm nghĩa; không thêm/bớt từ để đạt số từ mục tiêu.
- **Cho phép và khuyến khích 1–3 nhịp rất ngắn (3–6 từ)** đặt ngay tại điểm đảo chiều hoặc cú sốc ("Quân đội rút." / "Mười viên một con."). Đây là ngoại lệ có chủ đích của mục tiêu 7–14 từ. Không để cả bài toàn nhịp cùng cỡ: nhịp dài (≤24 âm tiết) dùng để giải thích, nhịp ngắn dùng để nhấn.
- Cắt ở chỗ có dấu phẩy/chấm là tốt nhất — app cũng ngắt cụm chữ theo dấu câu nên nhịp và chữ khớp nhau.
- **Không tách số khỏi danh từ**: "năm 1932", "20.000 con emu", "9.860 viên đạn" luôn nằm trong một nhịp.
- Mỗi nhịp **một ý**. Nếu một câu có 2 ý (người + hành động) thì tách thành 2 nhịp — mỗi nhịp sẽ có hình riêng. **Ngoại lệ mạch kể:** hai ý là nguyên nhân → kết quả trực tiếp, hoặc hai chủ thể đứng trong cùng một quan hệ ("A mua lại tranh của B", "A là vợ của B") thì giữ chung một nhịp; tách ra là mất quan hệ.
- **Ngân sách mỗi nhịp ≤ 24 âm tiết** (~3,5 s đọc), đếm theo **âm tiết** chứ không theo từ: `Rốc-ke-phe-lơ` = 4 âm tiết/1 từ, `1929` = ~6 âm tiết/1 từ. **Mặc định một nhịp chỉ mang một cụm tên riêng hoặc một mốc năm**; **hai tên riêng được đứng chung khi chúng nằm trong cùng một quan hệ** ("A mua lại tranh của B", "A cưới B", "A chỉ đạo B") — tách hai tên ra hai nhịp là cắt mất quan hệ, người xem phải tự nối. Số liệu liệt kê cùng loại (66 tranh + 50 bức vẽ) tính là một cụm. Vượt ngân sách thì tách ở dấu phẩy/chấm có sẵn — tốc độ giọng đọc là cố định, nên nhịp dài chính là chỗ duy nhất tạo cảm giác "chậm lại".
- **Độ dài video thường: 16–18 nhịp** (mỗi nhịp một ảnh riêng), tương đương video mẫu. **Nguồn mỏng thì 12–15 nhịp là bản đạt, không phải bản thiếu**: đừng tách một câu thành hai nhịp chỉ cho đủ số — mỗi nhịp đắp thêm đều là nhịp rời. Không rút xuống dưới 12 khi nguồn còn ý; ngược lại thiếu ý thì tách theo mệnh đề thật, không gộp hai ý xa nhau vào một nhịp. Cặp nguyên nhân → kết quả/nhãn trực tiếp luôn giữ chung một nhịp.
- Đoạn chuyển ý lớn (địa điểm, thời gian, nhân vật mới) luôn bắt đầu nhịp mới.
- **Không chia nhịp làm gãy một ý trọn vẹn**: một cụm nguyên nhân–cơ chế–kết quả có thể gồm nhiều nhịp, nhưng phải đọc liền vẫn hiểu được quan hệ giữa chúng. Nếu cần đổi chủ đề, thêm một nhịp cầu nêu kết quả hoặc lý do chuyển sang chủ đề mới.
- **Mốc thời gian phải có khung**: kể trong một khoảng ("trong mười năm đầu…") rồi mới đưa năm cụ thể; "X năm sau" chỉ neo vào **mốc năm gần nhất**, không neo vào một khoảng; không đặt một năm cụ thể ngay sau câu nói tới mốc xa hơn nếu không nói rõ đang quay lại.
- **Nhân vật mới phải có gốc:** câu đầu tiên xuất hiện một người phải nêu vai trò, lý do có mặt và quan hệ với nhân vật trước (nếu có). Không mở bằng danh từ nghề trần trụi kiểu "một biên tập viên", "một nhiếp ảnh gia"; viết "biên tập viên báo địa phương đang lái xe qua cầu", "đồng nghiệp của người biên tập viên ấy".
- **Nhãn sinh ra từ sự việc phải đứng cùng sự việc:** biệt danh, tên gọi hoặc kết luận phát sinh từ một chi tiết phải nằm chung câu với chi tiết đó ("mặt cầu nhún lên nhún xuống… nên công nhân gọi nó là…"), không để thành nhịp riêng sau khi đã kể xong.
- **Không nâng mức so với nguồn:** nguồn nêu con số thì giữ đúng con số và mức độ. Không đổi "gió 40 dặm/giờ" thành "không hề có bão" hay "gió nhẹ"; không đổi "dầm" thành "mặt cầu" khiến người nghe hiểu sai bộ phận kết cấu.
- **Mỗi ý phải có điểm đến**: nêu nguyên nhân, cơ chế, ví dụ, phép so sánh hay con số thì phải nối tiếp bằng tác dụng, hệ quả hoặc bước kế tiếp; ví von chỉ giúp hình dung, không thay lời giải thích nghĩa đen. Sau mỗi cụm ý tự hỏi "vậy thì sao?" — câu trả lời chưa nằm trong kịch bản thì bổ sung cầu nối hoặc viết lại. Khi chuyển từ ý này sang ý khác phải giữ nguyên quan hệ trước–sau, nguyên nhân–kết quả, vấn đề–cách giải quyết; không xếp các câu đúng riêng lẻ khiến người nghe phải tự đoán bước nối.
- **Không tham chiếu treo:** "này", "đó", "nó", "lần nữa", "như vậy", "sau đó" và cụm xác định ("đường bay này", "kết quả đó") chỉ được dùng khi đối tượng đã được giới thiệu rõ và không nhầm với chủ thể khác. Chưa có tiền đề thì gọi tên hoặc thêm nhịp giới thiệu; không dùng đại từ để tạo cảm giác liên kết giả.
- **Câu nối phải cụ thể**: cấm câu nối mơ hồ kiểu "rồi nó lớn nhanh", "sau đó mọi thứ thay đổi" — câu nối phải nêu chủ thể và hành động cụ thể của nhịp sau.
- **Bỏ vế đánh giá thừa khi dữ kiện đã tự nói**: không viết "thành công lớn" sau khi đã nêu "66 tranh sơn dầu và 50 bức vẽ"; con số tự nói, vế đánh giá chỉ đẻ thêm một nhịp rời.
- **Đọc liền mạch toàn bài:** đọc lời đọc từ nhịp đầu đến nhịp cuối liền một hơi. Chỗ nào phải quay lại nhịp trước mới hiểu là chỗ hỏng, phải viết lại.
- **Viết như nói, không viết tắt kiểu ghi chú.** Mỗi nhịp là một câu nói đủ chủ ngữ + vị ngữ, đọc lên hiểu ngay khi chưa xem ảnh. Cấm lối tỉnh lược "thành phố đó không có đất", "gần nhất, ngoài đó 39 ki lô mét", "cầu thành đường": người nghe phải tự điền chữ mình chưa nói. Trần 24 âm tiết là trần cho **cả câu**, không phải lý do bỏ chủ ngữ, tân ngữ hay từ nối — chật chỗ thì giảm số ý trong nhịp hoặc bỏ nhịp, không nén câu. Bố cục chữ do bộ dựng lo, nên câu không bao giờ được viết để vừa hàng phụ đề.
- **Khoảng nghỉ giữa nhịp do app tự tính theo dấu câu cuối nhịp**: kết thúc bằng chấm/!/? nghỉ dài (~0.5s tổng), kết thúc bằng phẩy/chấm phẩy nghỉ ngắn hơn (~0.3s), cắt giữa cụm không dấu nghỉ ngắn nhất (~0.15s). Không cần chèn lệnh nghỉ; muốn khoảng lặng kịch tính ở chỗ nào thì kết thúc nhịp đó bằng dấu chấm. Luật này áp dụng cho cả flow Threads.

## 4. Chữ hiển thị (`||` tuỳ chọn), nhấn mạnh và cụm phụ đề

- **Không tách cột là mặc định.** Viết mỗi nhịp đúng một câu nói, không có `||`: bộ dựng tự sinh chữ hiển thị bằng IN HOA chính câu đó, giữ nguyên dấu `*nhấn mạnh*`. Chỉ mở `||` khi buộc phải khác lời đọc đúng theo ngoại lệ dưới đây (tên phiên âm gạch nối `Ca-xpi` / `CASPI`, viết tắt `KM/H`). Dòng đã có `||` thì hai bên phải khớp từng chữ; dòng không có `||` thì khớp theo thiết kế.
- **Chữ hiển thị = đúng từng chữ lời đọc** (người xem nghe gì đọc nấy) và **cùng số từ với lời đọc**. Chỉ được phép 3 việc: viết IN HOA, đổi số viết bằng chữ thành chữ số, bọc `*nhấn mạnh*`. Không lược từ, không thêm từ, không đảo trật tự, không thay bằng từ đồng nghĩa, không tóm tắt. Lệch số từ là bộ dựng canh phụ đề lệch giọng đọc. Không giới hạn chữ hiển thị ở 9 từ: dài quá thì chia lời đọc **và** chữ hiển thị cùng một vị trí thành các nhịp tương ứng, không rút gọn bên nào.
- **Ngoại lệ được phép** (vẫn phải đúng số từ): số viết bằng chữ → chữ số, giữ đúng giá trị và các từ xung quanh ("năm một nghìn chín trăm ba mươi hai" → "NĂM *1932*", "mười nghìn viên đạn" → "*10.000 VIÊN ĐẠN*"); dạng viết tắt thông dụng ở chữ hiển thị trong khi lời đọc giữ dạng đầy đủ để TTS đọc đúng ("năm mươi ki lô mét trên giờ" → lời đọc `50 KI LÔ MÉT TRÊN GIỜ`, chữ hiển thị `*50 KM/H*`; "40 dặm một giờ" → `*40 DẶM/GIỜ*`); tên phiên âm gạch nối bên lời đọc so với tên gốc bên hiển thị (`MÉT-SEN-GIƠ` / `MESSENGER`), tính theo âm tiết. Giữ nguyên số đã ở dạng chữ số. Chỉ chuyển từ thực sự mang nghĩa số: "năm nay", "một lần nữa", "một đàn chim" không đổi thành "5 NAY", "1 LẦN NỮA", "1 ĐÀN CHIM".
- **Chia cụm**: dấu phẩy đặt theo nhịp hơi của câu nói, không đặt để ép cụm chữ đẹp — bộ dựng tự gom cụm ≤4 từ (dấu phẩy cũng là điểm ngắt) rồi đẩy cụm `*nhấn mạnh*` xuống hàng dưới. Cụm phải **đủ nghĩa độc lập**, không mượn/chép từ của cụm khác để đủ số từ. Không tách cụm nghĩa cố định ("quốc gia", "nhà nghiên cứu", "trí thông minh", "thức ăn"); tên riêng một từ phải ghép với cụm kế cận. Câu đọc tự nhiên mà dấu phẩy tạo nhịp đúng ngữ pháp: đúng "MÔ TẢ, MỘT CỖ MÁY, NHƯ VẬY", sai "MÔ TẢ MỘT, CỖ MÁY NHƯ VẬY" (tách động từ khỏi tân ngữ). Không coi dấu chấm trong chữ viết tắt tên riêng là điểm ngắt — `GEORGE B. SELDEN` phải nằm trong cùng một cụm. Rà từng dấu phẩy trước khi bàn giao.
- **Kiểm cụm bằng đúng bộ tách của pipeline** (`pipeline.split_items(pipeline.parse_emph(disp), 4)`): mọi cụm thực sự lên hình phải dài 2–4 từ. Nếu bộ dựng ra cụm 1 từ hoặc chẻ đôi cụm nghĩa, sửa chỗ ngắt hơi/chữ hiển thị trước khi giao.
- **Hai hàng trong một cụm nhấn không được lệch nhau quá 1 từ.** Bộ dựng cắt cụm tại từ `*nhấn mạnh*` đầu tiên: chữ thường thành hàng trên, cụm nhấn thành hàng dưới. "CHO / *100 TẤN DẦU*" để một chữ treo trên ba chữ, bố cục vỡ. Sửa bằng cách chọn lại từ nhấn trong cùng câu (chọn chữ rơi vào giữa cụm 4 từ), dời dấu phẩy tới chỗ ngắt hơi tự nhiên khác, hoặc bọc trọn cụm (`*100 TẤN DẦU*`) để nổ một hàng — **không thêm chữ đệm vào hàng côi**, vì đó là bẻ lời đọc cho vừa bố cục. `lint_rows` đếm và báo từng nhịp lệch.
- **Nhấn mạnh — mỗi nhịp 1–2 cụm, nhịp dài (≥18 âm tiết) được 3.** Bậc chữ to là tài nguyên hiếm nhưng một câu thật sự có thể có hai chỗ lệch; quá trần thì người xem không biết chỗ nào là chính. Chọn theo thứ tự: con số/dữ kiện → từ khoá chủ đề → cặp tương phản ("không phải… mà là") → chỗ gây bất ngờ → động từ trong CTA. Không bọc từ nối, trợ từ, đại từ hay từ đệm ("rất", "khá", "thực sự") trừ khi chính nó là trọng tâm của ý; không nhấn lại từ vừa nhấn ở nhịp liền trước; hai cụm đứng sát nhau chỉ khi chúng là một cụm nghĩa. Nhịp chỉ để chuyển tiếp không cần cụm nào, nhưng **hook và câu chốt luôn phải có ít nhất một cụm**. Phép thử cho từng câu: "nếu người xem chỉ nghe đúng một từ, đó là từ nào?"; đọc riêng dãy từ đã bọc phải gợi lại được thông điệp chính của kịch bản. Chỉ bọc `*` quanh chữ có sẵn, không thêm/sửa chữ để tạo điểm nhấn, không bọc cả câu dài. `lint_rows` đếm số cặp mỗi nhịp và báo khi vượt trần (2, hoặc 3 với nhịp ≥18 âm tiết).
- **Tên riêng là điểm nhấn nên đứng riêng một cụm 2–4 từ** (người khởi xướng, nhân vật đảo chiều, nghệ sĩ gắn số liệu); không cần ở mọi lần nhắc. Khi tách tên, chỉnh lời đọc (dấu hai chấm thay "là", bỏ "và") để hai vế khớp số từ.
- **Chủ thể có tên riêng thì phải được đọc tên ít nhất một lần.** Video nói về một nơi/sự vật mà cả bài không đọc tên thì người xem không tra tiếp được. Lời đọc phiên âm (`Ôi Rốc`), chữ hiển thị giữ tên gốc (`OIL ROCKS`), và phiên âm phải **cùng số từ** với tên gốc để bộ căn mốc giọng còn ghép được; tên đứng sau một danh từ chỉ loại ("có tên …", "giàn khoan …").
- App hiện chữ **2 bậc**: video thường hiện cả hai bậc cùng lúc với cụm (karaoke mới chạy chữ theo giọng; Threads hiện từng bậc lần lượt đúng lúc từ đầu bậc được đọc), bậc lớn xếp dưới dòng nhỏ và giữ tới hết cụm. App không cắt giữa một cụm `*nhấn mạnh*` nên phải bọc trọn cụm nghĩa (`MIỀN NAM`, `DỰNG LẠI`, `3 THÁNG 11`), và tự bỏ dấu câu cuối cụm khi hiển thị (dấu vẫn giữ trong lời đọc). Số đo bố cục, neo ảnh/chữ: mục "Kiểm trước khi render" ở PHẦN 2 dưới đây.
- Ưu tiên dấu câu `, . ! ?`. Nếu bản gốc có `—`, `–`, `:`, `-` làm dấu ngắt câu, có thể thay bằng dấu phẩy/chấm ở cả lời đọc và chữ hiển thị để tránh app tách cụm kỳ lạ; không đổi từ hoặc ý. Giữ ký hiệu thuộc tên riêng, số âm hoặc khoảng số khi thay sẽ làm sai nghĩa.
- **Cách gọi con vật**: dùng tên riêng, "nó" hoặc "chú chó/chú mèo…". Không dùng đại từ chỉ người ("cô", "anh", "chị", "ông") cho con vật vì nghe như đang nói về người. Câu đã nêu tên thì các câu sau dùng "nó", tránh lặp tên quá nhiều.

## 5. Ảnh minh hoạ (khối chuẩn duy nhất)

**Nguyên tắc gốc: hình phải minh hoạ đúng nội dung đang đọc — chủ thể + động từ + giai đoạn — không chỉ cùng chủ đề chung.** Tag mô tả chủ thể/hành động cụ thể; một tag chỉ dùng lại khi các nhịp thực sự cần cùng loại hình. **Toàn bộ nhịp dùng ảnh thật hoặc sơ đồ; không dùng meme ở bất kỳ video thường nào** — kể cả nhịp phản ứng, nhịp con số gây choáng, nhịp chuyển ý.

**Khớp nội dung**

- Trước khi tìm ảnh, rà từng nhịp và liệt kê **danh từ/cụm danh từ có thể minh hoạ**: người, vật, địa điểm, tên riêng, hiện tượng, công cụ, hoạt động và hình ảnh so sánh — kể cả chủ thể chỉ xuất hiện một lần. Với từng nhịp lập ma trận `lời đọc → chủ thể → động từ/hành động → bằng chứng nhìn thấy trong ảnh → nguồn`; ảnh cùng chủ thể nhưng không thể hiện động từ hay quan hệ đang đọc là **không đạt**, không được ghi "đúng chủ đề" thay cho bằng chứng.
- Phân biệt ba loại: (1) ảnh cảnh/hành động thật, (2) sơ đồ/biểu đồ thể hiện đúng quan hệ hoặc quy trình, (3) ảnh chân dung/thiết bị chỉ xác định danh tính. Loại (3) không được dùng cho câu nói về phóng, bay, truyền dữ liệu, phát hiện, thay đổi hay kết quả nếu ảnh không thể hiện chính hành động đó.
- Ảnh phải **đúng giai đoạn**: nhịp kể lúc thi công/trước sập không dùng khung hình từ phim ngày sập (dù khung đó thể hiện đúng hiện tượng); nhịp về lúc sập không dùng ảnh khánh thành hay cầu mới. Mở từng ảnh kiểm tra trực quan; không chấp nhận ảnh tài liệu của sự kiện khác hoặc ảnh chỉ có chủ thể chung khi mệnh đề yêu cầu địa điểm, hành động hay sự kiện cụ thể.
- **Ảnh panorama/siêu ngang phải cắt về ~3:2 trước khi dùng.** Khung ảnh là 1000×640: ảnh 1920×648 thu vào chỉ còn 1000×338, thành dải mỏng không đọc được. Cắt đúng vùng có chủ thể (giữ nguyên tỉ lệ gốc của file nguồn đã cắt trong `SOURCES.txt`), lưu thành tên mới; **ảnh bookend phải là cùng một file chép sang hai thư mục** để hash khớp.
- **Không dùng ảnh có sẵn chỉ để lấp chỗ trống.** Giới thiệu trực tiếp về Proxima Centauri phải có ảnh đúng Proxima Centauri, Andromeda phải đúng Andromeda; nhà thiên văn học, mắt thường nhìn trời và cuốn sách lịch sử cũng phải có hình tương ứng. Quan hệ/hiện tượng như ánh sáng đi từ Mặt Trời đến Trái Đất cần ảnh hoặc sơ đồ có đủ hai chủ thể và đường truyền — ảnh Mặt Trời đơn lẻ không chứng minh được.
- Nếu một nhịp có nhiều chủ thể cần ảnh riêng, chia nhịp tại ranh giới cụm nghĩa và gán tag cụ thể cho từng phần, giữ nguyên toàn bộ lời đọc và chữ hiển thị; không chia hợp lý thì tìm một ảnh/sơ đồ bao quát các chủ thể đó.
- **Nhịp phản ứng và nhịp con số cũng phải có ảnh thật**: chủ thể đã được minh hoạ ở nhịp giới thiệu thì nhịp sau vẫn cần ảnh riêng — ảnh khác cùng chủ thể, ảnh ở giai đoạn/hành động khác, hoặc sơ đồ chứng minh đúng quan hệ (khoảng cách, tỷ lệ, trước–sau). Không có ảnh đạt thì tìm thêm tư liệu, tách nhịp, hoặc bỏ nhịp; **không lấp bằng meme**.

**Số lượng, lặp và phong cách**

- **1 hình / 1 nhịp**, mỗi nhịp phải có file ảnh riêng. Không để trống cột clip và không bật `carry` để giữ ảnh của dòng trước nhằm tiết kiệm.
- **Mỗi ảnh minh hoạ chỉ xuất hiện 1 lần trong toàn bộ video**, kể cả các nhịp cách xa nhau. Bản đổi tên, cắt ngắn, đổi độ phân giải hay chuyển định dạng vẫn là cùng ảnh — tính hash nội dung để phát hiện file bị copy/đổi tên. Chủ thể được nhắc lại thì tìm ảnh khác đúng chủ thể.
- **Bookend**: ảnh nhịp mở và nhịp cuối là cùng một file (cùng hash) — **ngoại lệ duy nhất** của quy tắc trên. Chọn ảnh đủ khái quát dùng được cho cả mở lẫn kết (tượng đài, chân dung, toàn cảnh sự kiện) và câu kết phải nhắc đúng thứ ảnh thể hiện. Hook và nhịp kết kiểm riêng: ảnh bookend phải chứng minh được **cả** câu hook **và** câu kết; hook có nhiều hành động thì rút câu về hành động mà ảnh chứng minh được, không giữ câu rộng rồi dùng ảnh gần nghĩa.
- **Số ảnh đạt quyết định số nhịp**: đếm ảnh đã kiểm chứng được cho từng nhịp **trước khi** chốt độ dài. Nguồn ảnh chỉ đủ 13 ảnh thì bản 13 nhịp là bản đạt; không xuống dưới 12 khi nguồn còn ý, và **không nới nhịp bằng meme hay ảnh lặp**.
- **Ảnh là kênh chở nội dung, không phải kênh chở cảm xúc.** Cảm xúc nằm trong chữ (đối chiếu dữ kiện, cặp số quy đổi) và trong cú cắt ảnh. Vì vậy không tồn tại "mục tiêu % meme", không có "tag cảm xúc", và không có ngoại lệ nào cho nhịp phản ứng.
- **Chủ đề thương vong/tang tóc/tai nạn chết người (bão lụt, thiên tai, chiến tranh, hỏa hoạn…): tắt mascot khi dựng**, dùng ảnh tư liệu cho toàn bộ nhịp và giữ giọng trang trọng. Luật này không còn là ngoại lệ về ảnh — ảnh thật đã là luật chung — điểm khác biệt còn lại là **tắt mascot** và không dùng giọng mỉa.
- **Không tự tạo ảnh minh hoạ / card đồ hoạ** — tải ảnh, clip hoặc sơ đồ có sẵn trên mạng (`tools/card_gen.py` chỉ giữ lại để tham khảo, không dùng). Ngoại lệ: card Threads do `threads_shot.py` dựng từ dữ liệu đã bóc là ảnh chụp nội dung thật, không phải đồ hoạ tự bịa.
- Tag = **thư mục theo chủ thể/hành động**; một thư mục chỉ chứa ảnh đúng chủ thể đó (app bốc ngẫu nhiên trong thư mục, nên trộn ảnh là chọn nhầm ảnh). Chuẩn bị ít nhất số ảnh khác nhau bằng số nhịp cần ảnh. Khi cần ánh xạ tất định (không muốn app bốc ngẫu nhiên), để đúng 1 ảnh trong thư mục tag; ảnh dự phòng chuyển sang `remains/` và ghi lại vị trí mới trong `SOURCES.txt`.

Bảng chọn theo nội dung:

| Nội dung đang nói | Loại | Thư mục |
|---|---|---|
| Chủ thể/sự kiện đang kể (emu, lính, ruộng lúa, súng) | ảnh thật | `emu`, `cuu-binh`, `lua-mi`, `sung-lewis`, `dan-emu-tan`, `ngam-ban`, `rut-quan`, `nong-dan`, `dat-can-coi`, `chien-dich-2`, `bao-chi` |
| Con số/khoảng cách/tốc độ | ảnh hoặc sơ đồ đúng đối tượng và quan hệ đang nói | `toc-do-anh-sang`, `anh-sang-mat-troi-trai-dat`, `khoang-cach-proxima` |
| Tên riêng cụ thể | ảnh đúng người/vật/địa điểm đó | `proxima-centauri`, `andromeda` |
| Danh từ mới hoặc hình ảnh so sánh | ảnh thể hiện trực tiếp danh từ/cảnh đó | `nha-thien-van`, `ngam-sao-mat-thuong`, `sach-lich-su` |
| Câu punchline, thất bại "chẳng ăn thua" | ảnh thật của chính kết quả đó (xác, đống đổ nát, hiện trường) | tag theo sự việc |
| Chạy trốn, rượt đuổi, hỗn loạn | ảnh thật ghi hành động đó | tag theo hành động (`emu-tan-đàn`, `xe-tai-duoi`) |
| Hư hại, thiệt hại, mất mát | ảnh thật ghi hậu quả, đúng giai đoạn | tag theo hậu quả |
| Kết quả tốt, thắng lợi, con số ấn tượng | ảnh thật của kết quả (báo cáo, hiện trường thành công) | tag theo kết quả |
| Buồn, rút quân, suy thoái | ảnh tư liệu đúng thời điểm | tag theo sự kiện |
| Nghi ngờ, điều khó tin | sơ đồ/ảnh chứng minh chính chỗ lệch | tag theo quan hệ |
| Mở đầu / kết thúc | ảnh bookend chứng minh được **cả** hook lẫn câu kết | tag chủ thể |

## 6. Quy trình tải minh hoạ

Tiêu chí ảnh nằm ở mục 5 — mục này chỉ giữ trình tự việc.

1. Lập bảng bao phủ danh từ/chủ thể và hành động theo từng nhịp, rồi mới gom tag. Không bắt đầu bằng cách chọn tag cảm xúc từ thư viện.
2. Với mỗi chủ thể/cảnh còn thiếu, tìm bằng tên chính xác và hành động/mối quan hệ, dùng cả từ khoá tiếng Việt và tiếng Anh khi hữu ích, từ **bất kỳ nguồn công khai nào trên mạng**: công cụ tìm ảnh, website chuyên ngành, cơ quan khoa học, báo chí, Wikimedia, kho ảnh. Không giới hạn nguồn hoặc chỉ tìm ảnh PD/CC0/CC BY.
3. Mở trang nguồn xem ảnh ứng viên để kiểm tra đúng chủ thể, cảnh và ngữ cảnh; sau khi tải, mở file kiểm tra chủ thể thật, độ nét, khả năng cắt khung và việc file có phải trang HTML/ảnh lỗi hay không. Không coi tên file hoặc kết quả tìm kiếm là bằng chứng ảnh khớp. Với mỗi ảnh trả lời bằng văn bản: "Tôi nhìn thấy gì?", "Động từ nào trong lời đọc được ảnh chứng minh?", "Chi tiết nào không được chứng minh?" — không trả lời được câu thứ hai thì loại ảnh hoặc sửa lời đọc. Loại ngay ảnh trắng/trống, mờ, dính thanh công cụ/menu/logo, ảnh có chữ hoặc năm khác làm người xem hiểu sai; không đợi tới preview mới phát hiện.
4. **Tự tải ảnh phù hợp, không cần hỏi lại về bản quyền cho từng ảnh.** Người dùng đã chọn tự xử lý quyền sử dụng sau. Không loại ảnh chỉ vì giấy phép hạn chế hoặc chưa rõ; không dừng tải để chờ xác minh giấy phép. Ghi đúng thông tin có trên nguồn, không suy đoán ảnh là miễn phí hay đã được cấp quyền; không thấy thông tin thì ghi "chưa rõ — người dùng xử lý sau". Không vượt đăng nhập, paywall hoặc biện pháp chặn truy cập; nguồn không tải được thì tìm nguồn khác.
5. Tải bằng Python + `User-Agent` mô tả khi cần:
   ```python
   req = urllib.request.Request(url, headers={"User-Agent": "VideoMakerLocal/1.0 (personal video project)"})
   ```
   Ưu tiên bản `iiurlwidth=1600` (nhẹ, đủ nét cho khung 960×560). Có thể dùng Playwright chụp vùng ảnh, sơ đồ hoặc nội dung trang; cắt bỏ thanh công cụ, popup và phần không liên quan, kiểm tra ảnh chụp và ghi URL trang nguồn như ảnh tải xuống.
6. Lưu ảnh vào `assets/illus/<nội-dung>/<tag>/<tên-ngắn>.<đuôi-file>`. Tag phải đủ cụ thể để app không chọn nhầm ảnh khác chủ thể trong cùng thư mục.
7. Ghi nguồn vào `assets/illus/<nội-dung>/SOURCES.txt`: file — chủ thể/nhịp sử dụng — tác giả nếu có — giấy phép/tình trạng quyền sử dụng — URL trang nguồn — URL file gốc. **Không đưa credit lên video.** Lưu luôn bảng đối chiếu `nhịp → ảnh → bằng chứng nhìn thấy → nguồn` cùng `SOURCES.txt` hoặc ghi chú nội bộ của chủ đề, để lần kiểm tra sau không phải duyệt lại theo tên file. Giữ thông tin cũ khi bổ sung ảnh mới.
8. Chạy hard gate ảnh theo ma trận: mọi nhịp có bằng chứng ảnh cho chủ thể + hành động/ngữ cảnh; `hook` và `closing` cùng file, cùng hash, cùng khớp nội dung; mọi hash khác chỉ xuất hiện một lần; không còn ảnh giao diện, ảnh trắng hay ảnh chỉ đúng chủ đề chung. Nhịp nào không đạt phải đổi ảnh hoặc sửa câu ở bước C, không được đánh dấu đạt để tiếp tục render. **Riêng nhịp 1 và nhịp kết: co câu hook cho khớp ảnh là hỏng** — việc phải làm là đổi ảnh/đổi tag, hoặc quay lại BƯỚC C viết câu mới **vẫn giữ danh từ chỉ chủ thể** (ô 3 Bảng tự kiểm), chứ không được cắt câu đang có thành câu cụt.
9. Chốt bảng minh hoạ với file cụ thể cho từng nhịp, rà lại danh sách chủ thể trên toàn video (mỗi chủ thể mới phải có ảnh của riêng nó), rồi viết Phần C (ảnh cần bổ sung cho lần sau) gắn với thiếu hụt thực tế của thư viện. Chủ thể mới chưa được minh hoạ thì tiếp tục tìm, không lấp bằng ảnh chung chung; vẫn thiếu ảnh thì báo chính xác chủ thể còn thiếu, không đánh dấu hoàn tất.
10. Chạy checklist mục 8 rồi mới giao.

> Ghi chú kỹ thuật: thư mục `assets/` do app tạo nên sandbox của agent có thể chặn ghi → xin quyền
> (danger-full-access) cho đúng một lệnh copy/tải, và chỉ định rõ thư mục đích.

## 7. Ngoài phạm vi flow này

- **Threads** (bài/comment, card, `|| -`, scraper, chế độ ảnh, `--ident`): `skills/lam-video-threads/SKILL.md`. Bài Threads giữ nguyên văn, **không** áp dụng quy trình 6 bước 0–E, không tải ảnh minh hoạ theo kịch bản, và được phép không có `*nhấn mạnh*`. (Meme vốn đã bị cấm ở cả video thường, nên flow Threads cũng không có hình động cảm xúc.)
- **Đăng / hẹn giờ Facebook Page**: [docs/DANG_FACEBOOK.md](../../docs/DANG_FACEBOOK.md). Flow kịch bản dừng ở bàn giao; chỉ đăng khi người dùng yêu cầu.
- **Bố cục khung hình khi dựng** (`meme_y`, `meme_h`, `text_y`, zoom, mascot): PHẦN 2 của file này và `docs/GIAO_DIEN_REACT.md`.

## 8. Checklist trước khi giao

Rà theo đúng thứ tự tầng: **mạch kể gãy thì chưa giao**, dù mọi mục tầng 2–3 đều đạt.

### Tầng 1 — mạch kể

Nguồn kiểm tra tầng 1 là **Bảng tự kiểm bàn giao** (10 ô, ở PHẦN 1): CQ + dòng nguồn trả lời, 3 hook ứng viên, chủ thể trong nhịp 1, cặp số đối chiếu, xương sống ≥2 "nhưng", vai trò từng nhịp, từng mạch hở, số ảnh đạt, nguồn của từng con số, ba chốt kết bài. **Không lặp lại các mục đó ở đây** — bảng còn ô trống thì tầng 1 gãy, chưa giao.

- [ ] Đi đủ BƯỚC 0→E theo đúng thứ tự: CQ, sổ dữ kiện có nhãn đã qua cổng nhãn, bản đồ nhịp đánh dấu hook + từng mạch hở + điểm đảo chiều, văn xuôi (ngân sách tham khảo 150–200 từ; vượt thì khai số từ thật, không cắt dữ kiện), xương sống + thử người xem khó tính, rồi mới cắt nhịp. Không có bản "viết thẳng thành nhịp", và không có bản "sửa ở bước cắt".
- [ ] Không còn câu thái độ: mọi chỗ gây cảm xúc là **câu đối chiếu** (hai dữ kiện đặt cạnh nhau) hoặc **phép quy đổi từ số của nguồn**, không phải tính từ/bình luận.
- [ ] `script_draft.lint_rows(rows)` trên bản cuối đã được đọc hết; cảnh báo chữ văn viết, cụm cảm thán và nhịp đều phải sửa ở bước C, cảnh báo "mở màn bằng mốc thời gian" chỉ giữ khi ghi được lý do.
- [ ] Không chế nội dung khi nối mạch: mọi chi tiết, nguyên nhân, động cơ, kết quả và quan hệ nhân–quả truy được về đầu vào hoặc nguồn đã kiểm — **số liệu phải kiểm từng số, không nhớ đại**; nguồn chưa đủ thì viết theo mức chắc chắn phù hợp hoặc báo rõ phần chưa xác định.
- [ ] Mỗi cụm ý có điểm đến ("vậy thì sao?" đã có trong kịch bản); nhân vật mới có gốc; nhãn đứng cùng sự việc sinh ra nó; không còn 🟥 nào mà cắt đi không ai nhận ra; mức độ và thuật ngữ đúng nguồn.
- [ ] Đã đọc liền mạch toàn bộ lời đọc; không chỗ nào phải quay lại nhịp trước mới hiểu; không tham chiếu treo.

### Tầng 2 — format

- [ ] Mỗi nhịp là câu nói đủ chủ ngữ + vị ngữ, đọc lên hiểu ngay khi chưa xem ảnh; không còn câu tỉnh lược kiểu "không có đất", "gần nhất, ngoài đó…"; ≤ 24 âm tiết (`lint_rows`).
- [ ] Mặc định không có cột `||`; nhịp nào mở `||` thì hai bên khớp toàn bộ từ, đúng thứ tự và **cùng số từ** (bỏ `*`, không phân biệt hoa/thường, quy phần số về cùng dạng). Chỉ chuẩn hoá số/dấu ngắt câu theo mục 4.
- [ ] Kịch bản thô: bản biên tập giữ đủ ý chính, đúng tên riêng và số liệu. Bản yêu cầu nguyên văn: ghép lời đọc các nhịp kiểm không thiếu/thừa từ; sau khi chia nhịp không sửa thêm lời đã chốt.
- [ ] Mọi cụm do `pipeline.split_items(pipeline.parse_emph(disp), 4)` tách ra dài 2–4 từ; mỗi nhịp **1–2** cặp `*nhấn mạnh*` (3 nếu nhịp ≥18 âm tiết; `lint_rows` báo khi vượt trần), hook và câu chốt có ít nhất một cặp, dấu `*` đủ cặp và chỉ bọc chữ có sẵn — các số và tên còn lại của nhịp vẫn hiện ở bậc nhỏ. Hai hàng của cùng một cụm nhấn **chênh nhau ≤1 từ** (`lint_rows` báo).
- [ ] Tên riêng/thuật ngữ/viết tắt khó đọc đã phiên âm ở lời đọc, chữ hiển thị giữ tên gốc; tên gốc cũng nằm ở nguồn hoặc bảng minh hoạ.

### Tầng 3 — media và bàn giao

- [ ] 16–18 nhịp cho video thường; nguồn mỏng thì 12–15 và đã báo lý do. Không nhịp nào trống clip.
- [ ] Ảnh/clip minh hoạ (`assets/illus/<nội-dung>/<tag>/`) đã tải sẵn **trước khi giao**; thiếu thì tải bổ sung, không giao kịch bản "nợ" hình.
- [ ] Bookend cùng file/cùng hash và câu kết nhắc đúng thứ ảnh; không ảnh nào lặp ngoài cặp bookend; **không có file meme nào trong kịch bản**.
- [ ] Ảnh đúng giai đoạn + hành động, không chỉ đúng chủ thể; đã mở từng ảnh và trả lời được "động từ nào trong lời đọc được ảnh chứng minh?".
- [ ] **Toàn bộ nhịp dùng ảnh thật hoặc sơ đồ** — không meme, kể cả nhịp phản ứng và nhịp con số; chủ đề thương vong/tang tóc còn tắt mascot.
- [ ] Mỗi file tải có nguồn + tình trạng quyền sử dụng ghi trung thực trong `SOURCES.txt`, khớp vị trí file thực tế.
- [ ] Có Phần C — ảnh cần bổ sung cho lần sau, gắn với chủ thể thực sự thiếu trong bản này.
- [ ] Kiểm tra thư viện khớp kịch bản (`bad` phải rỗng):
  ```powershell
  .venv\Scripts\python.exe -c "from videomaker import pipeline as pl; from pathlib import Path; rows=pl.analyze(Path('duong-dan-kich-ban.txt').read_text(encoding='utf-8'), content='ten-noi-dung'); bad=[r for r in rows if not r[4]]; print(len(rows),'nhip, thieu clip:',len(bad))"
  ```
  (Thay `ten-noi-dung` và đường dẫn kịch bản đang làm.)
- [ ] Đã lưu `kich-ban.txt`, media và nguồn; bàn giao để người dùng kiểm tra. Chỉ khi người dùng yêu cầu mới chạy preview (`python tools/render_script.py <kich-ban.txt> --content <ten> --preview [--speed 1.25]`) và cho duyệt trước khi xuất bản cuối. `--speed` chỉnh tốc độ đọc cho riêng lần dựng, không sửa `settings.json`.

## 9. Ví dụ

Chủ đề: "Đại chiến Emu", Tây Úc 1932. **Mọi số dưới đây đã đối chiếu nguồn** (Wikipedia — Emu War; hồ sơ tiền thưởng emu 1934). Số nhớ đại là chưa đạt, phải kiểm trước khi viết.

**BƯỚC 0 — CQ:** "Vì sao quân đội cầm súng máy lại không hạ nổi một đàn chim?" — người xem đã biết quân đội + súng máy thì thắng nổi gần mọi thứ (NEO), đàn chim thì ngược lại (LỆCH), và câu hỏi chưa có lời giải trong hook.

**BƯỚC A — Sổ dữ kiện (rút gọn):**

| # | Dữ kiện | Nhãn | Quan hệ |
| --- | --- | --- | --- |
| 1 | Miền Tây Úc, nhiều cựu binh Thế chiến I được cấp đất làm nông, giá lúa mì giảm | `NEO` | là bối cảnh của 2 |
| 2 | Khoảng 20.000 emu kéo về, giẫm hàng rào và ruộng lúa | `LEO` | dẫn đến 3 |
| 3 | Cựu binh xin súng máy vì họ biết thứ gì trị được kẻ địch đông | `NGƯỜI` | dẫn đến 4 |
| 4 | Chính phủ gửi một thiếu tá, hai khẩu súng máy, 10.000 viên đạn | `NEO`, `LEO` | — |
| 5 | Emu chạy nhanh, tách thành nhóm nhỏ; súng đặt trên xe tải không đuổi kịp | `LỆCH` | đối lập 4 |
| 6 | Thiếu tá báo hạ 986 con sau chừng một tuần — tức mười viên đạn mới trúng một con | `SỐ`, `TRỚ TRÊU` | hệ quả của 5 |
| 7 | Chiến dịch chấm dứt ngày 10 tháng 12; về sau tiền thưởng cho thợ săn hiệu quả hơn (57.034 con được tính thưởng năm 1934) | `TRỚ TRÊU` | hệ quả của 6 |

Qua cổng bước A: có `NEO` (quân đội, súng máy), `LỆCH` (emu không trúng đạn), `SỐ` + `TRỚ TRÊU` (mười viên một con, rồi tiền thưởng thắng súng máy) và hai mức `LEO` (20.000 con kéo về → chính phủ gửi súng máy).

**BƯỚC C — Bản văn xuôi (giọng chia sẻ kiến thức):**

> Quân đội Úc từng mang súng máy ra đánh một đàn chim, và không thắng nổi. Chuyện bắt đầu ở miền Tây nước Úc. Nhiều cựu binh Thế chiến thứ nhất được cấp đất làm nông, rồi giá lúa mì giảm. Đúng lúc đó, khoảng 20.000 con emu kéo về, giẫm nát hàng rào và ruộng lúa. Các cựu binh biết một thứ trị được kẻ địch đông: súng máy. Họ xin chính phủ. Chính phủ gửi một thiếu tá, hai khẩu súng máy, 10.000 viên đạn. Đối thủ của họ: một đàn chim. Nhưng emu chạy rất nhanh, lại tách thành từng nhóm nhỏ. Súng gắn lên xe tải thì xe không đuổi kịp. Sau chừng một tuần, thiếu tá báo hạ được 986 con. Tức là mười viên đạn mới trúng một con. Ngày 10 tháng 12, chiến dịch chấm dứt. Quân đội rút hẳn. Rốt cuộc, chính quyền trả tiền thưởng cho người nộp xác emu, riêng năm 1934 là 57.034 con. Vậy nên cuộc chiến này vẫn mang tên Đại chiến Emu, dù bên cầm súng máy là quân đội.

Không có câu nào bình luận cảm xúc. Chỗ đáng chú ý do **câu đối chiếu** ("hai khẩu súng máy, 10.000 viên đạn. Đối thủ của họ: một đàn chim.") và **phép quy đổi từ số của nguồn** ("mười viên đạn mới trúng một con") — người viết không bảo người xem phải thấy gì.

**BƯỚC D1 — Xương sống:** Vì cựu binh bị emu phá ruộng nên xin súng máy, **nhưng** emu chạy nhanh và tách nhóm nên đạn trượt, vì vậy mười viên mới hạ một con, **nhưng** quân đội đành rút, và cuối cùng tiền thưởng thợ săn làm tốt hơn, nên cuộc chiến mang tên con chim. → hai chữ "nhưng", hết phẳng.

**Điểm kiểm:** mạch hở ở "Đối thủ của họ: một đàn chim. Nhưng…" và "Tức là mười viên đạn mới trúng một con"; điểm đảo chiều "Quân đội rút hẳn." (cú đấm 4 từ, đứng ngay sau mốc 10 tháng 12); callback quay lại đúng "quân đội cầm súng máy".
Cú đấm đó **không có meme**: ba thứ làm nó nặng là dấu chấm cuối nhịp (nghỉ dài), chữ nhấn `*RÚT HẲN*` cỡ lớn, và cú cắt ảnh sang ảnh hiện trường/xe tải rút khỏi ruộng.

**Ba chỗ bản nháp từng sai và bước đối chiếu nguồn bắt lại:** 10.000 là số đạn **được cấp**, 9.860 là số **đã bắn** — hai số khác nhau, không dùng lẫn; 986 con là **báo cáo của thiếu tá**, giới sử học còn tranh cãi, nên phải nói "theo báo cáo" (đã nói: "thiếu tá báo hạ được"); "quân đội rút" không xảy ra một lần — họ rút ngày 8 tháng 11, quay lại ngày 13 tháng 11, rồi chấm dứt hẳn ngày 10 tháng 12, nên cú đấm phải là "Quân đội rút **hẳn**." đứng sau mốc 10 tháng 12, không phải "Quân đội rút." trần. Chi tiết nào không qua đối chiếu thì **bỏ chi tiết đó và lấy nhịp khác làm điểm đảo chiều**, không sửa nguồn cho khớp truyện.

**So với cách viết cũ:** bản từng nằm trong skill này mở bằng "Năm 1932, quân đội Úc được điều đi đối phó với một đàn chim." — mốc thời gian + bị động + chưa có mâu thuẫn, người xem không mang theo câu hỏi nào. `lint_rows` bây giờ báo cả hai lỗi đó (nhịp 1 mở bằng mốc thời gian, chữ "được điều đi").

---

## PHẦN 2 — LỆNH "LÀM VIDEO" (TỰ ĐỘNG TỚI MP4)

Nhận lệnh "Làm video" → chọn sự kiện trong ngày → tự tìm ảnh → viết kịch bản **16–18 nhịp**, mỗi
nhịp một ảnh riêng, theo toàn bộ PHẦN 1 → dựng mp4, không cần người dùng đưa văn bản hay chọn ảnh.

## Nguồn dữ liệu
- **Sự kiện**: Wikipedia On This Day (`/feed/v1/wikipedia/en/onthisday/events/{MM}/{DD}`), miễn phí, không cần key. Bản tiếng Việt trả 404 → lấy bản tiếng Anh rồi Việt hóa tên riêng trong lời đọc; chữ hiển thị giữ tên gốc.
- **Ảnh**: Wikimedia Commons / Smithsonian / LoC / Europeana (public domain / CC0). Pexels không phù hợp cho ảnh lịch sử; chỉ dùng để lấy không khí (trời, đám đông, đường phố).

## Chọn sự kiện
- Ưu tiên sự kiện **có ảnh khả dụng** + **liên quan Việt Nam**.
- Không lấy sự kiện đầu danh sách nếu thiếu ảnh. **Không còn meme để lấp**: 16 nhịp cần ~16 ảnh thật khác nhau, nên chủ đề chỉ có 5–6 ảnh tư liệu thì chọn sự kiện khác hoặc chấp nhận bản 12 nhịp.
- Mỗi cảnh bám đúng 1 câu có trong bài gốc, không tự suy diễn số/mốc/động cơ, nguyên
  nhân, kết quả hoặc quan hệ nhân–quả. Không thêm chi tiết để lấp khoảng trống giữa
  các câu; câu nối chỉ được sắp xếp và diễn đạt lại dữ kiện đã có. Nếu bài gốc không
  đủ căn cứ, bỏ chi tiết đó hoặc dùng cách nói thận trọng, không biến suy đoán thành
  sự thật.
- **Bỏ qua chủ đề nhạy cảm**: không chọn sự kiện chiến tranh Việt Nam, lịch sử chính trị Việt Nam gây tranh cãi, thảm hoạ/thương vong/tang tóc. Chọn sự kiện khác trong danh sách thay vì cố xử lý.

## Khớp phụ đề với giọng đọc

- Từ bản dựng này, mốc đổi cụm lấy từ **chính file tiếng của nhịp** (forced alignment),
  không còn suy ra từ trọng số từ hay số chữ số. Tắt bằng ô "Phụ đề bám đúng lúc giọng
  đọc" (`align_subs`) hoặc `--no-align` khi chạy CLI; thiếu torch/transformers thì pipeline
  tự quay về cách ước lượng cũ, không lỗi.
- Model căn mốc là `nguyenvulebinh/wav2vec2-base-vietnamese-250h` chạy CPU, ~0,3 s/nhịp,
  cache ở `.cache/huggingface`. **Không dùng model mặc định của WhisperX cho tiếng Việt**
  (`...-vi-vlsp2020`): nó nhận dạng sai toàn bộ, mốc bị dồn vào nửa đầu nhịp và mất 40% từ.
  Đường căn cũng không đi qua `whisperx.align()` mà là Viterbi CTC tự viết trong
  `pipeline._align_words()` — cách gom từ của WhisperX cắt sai mốc.
- Căn bằng **dạng đọc, không phải dạng viết**: chữ số không có ký tự trong bảng ký hiệu
  nên `_say_number()` viết "1929" → "một nghìn chín trăm hai mươi chín" chỉ để căn, còn
  lời đọc gửi TTS vẫn giữ nguyên. Từ không căn được thì nội suy giữa hai neighbour;
  nhịp nào căn dưới 75% số từ (`ALIGN_MIN_COVERAGE`) hoặc suy ra nhịp đọc phi lý thì bỏ, dùng ước lượng.
- **Vì mốc tra theo chỉ số từ, chữ hiển thị bắt buộc cùng số từ với lời đọc** (luật và ngoại lệ
  ở mục 4 của file này): lệch số từ là mất căn. Đếm từ từng nhịp ở cả hai vế sau khi viết;
  lệch thì sửa chữ hiển thị, không sửa bằng cách nới `max_words`.

## Nhịp đọc

- Giọng đọc đang chặn cứng: khoảng lặng bên trong nhịp ≤ 0,14 s, nghỉ cuối câu 0,16 s,
  sau dấu phẩy 0,05 s, ranh giới nhịp ~0,26 s. Không chỉnh tay file phụ đề; sub tự tính
  lại từ audio đã nén.
- Tốc độ articulation của giọng gần như không đổi (đo 16 nhịp: 6,1–7,8 âm tiết/giây,
  median 6,8). **Cảm giác "vào nội dung bị chậm" không đến từ tốc độ đọc mà từ nhịp dài**:
  một nhịp 30+ âm tiết tên riêng/số chạy liền 4,3–4,6 s trong khi các nhịp khác 1,5–3 s.
  Vì vậy giới hạn độ dài, đừng đi chỉnh prosody.
- Ngân sách ≤ 24 âm tiết/nhịp và cách đếm theo âm tiết: mục 3 của file này (`speech_syllables()`,
  `lint_rows()` đã cảnh báo sẵn). Cùng luật đó áp dụng khi đo: nhịp nào > 24 âm tiết phải tách,
  không được trông vào tốc độ đọc hay rút khoảng nghỉ để "cho gọn".
- Khi người xem than đọc chậm: đo `voice.wav` của job (số khoảng ≥ 0,2 s, khoảng dài nhất)
  và đo âm tiết từng nhịp trước khi kết luận. Chỉ đổi tốc độ đọc khi cả hai đã đúng chuẩn.

## Kiểm trước khi render

- `script_draft.lint_rows(rows)` trên bản cuối — **toàn bộ là cảnh báo mềm, không chặn render**: đại từ treo, chữ văn viết và cụm cảm thán bị cấm, nhịp 1 mở bằng mốc thời gian, không nhịp nào ≤6 từ, ≥4 nhịp liên tiếp cùng độ dài ±2 từ, cả bài không có nhịp nào chứa hai con số, **nhịp có quá 2 cặp `*nhấn mạnh*`** (3 cặp chỉ hợp lệ ở nhịp ≥18 âm tiết), nhịp > 24 âm tiết, viết tắt còn sót trong glossary. Cảnh báo nào cố tình giữ thì ghi lý do vào bảng bàn giao.
- **Không có gate máy** cho các mục sau, phải rà tay: parity số từ hai bên `||`, hook và câu chốt có ≥1 `*nhấn mạnh*` (nhịp chuyển tiếp được 0), hash cặp bookend. Mạch kể thì **không rà tay theo trí nhớ**: đọc lại **Bảng tự kiểm bàn giao 10 ô** ở PHẦN 1 (xương sống ≥2 "nhưng", ≥2 nhịp `đối lập`, ba chốt kết bài, chủ thể trong nhịp 1... đều là ô của bảng) — bảng đủ ô thì mục này đủ, bảng còn ô trống thì chưa render.
- `pipeline.analyze(script, content=...)` không còn nhịp thiếu ảnh; tag nào thiếu thì bổ sung
  ảnh trước, không render preview để "kiểm tra tạm".
- **Bố cục khung hình video thường**: ảnh neo đáy tại `meme_y=150`, `meme_h=640` (đáy y≈750);
  chữ **một hàng** lấy `text_y=880` làm tâm; chữ **hai hàng** thì hàng đáy nằm đúng `text_y=880`
  và hàng nhỏ mọc lên trên, nên hàng chữ to không nhảy lên/xuống khi cụm chuyển từ 1 sang 2 hàng.
  Hệ quả: đỉnh khối chữ hai hàng ~705, hàng nhỏ đè nhẹ đáy ảnh (~50px ở khung 1080) — chấp nhận
  được vì hàng nhỏ hiện trước và tan khi hết cụm. Ảnh cách mỗi mép ngang tối thiểu 60px
  (`meme_w ≤ 960`). Hai bậc chữ trong một cụm cách nhau ~32px ở khung 1080
  (`tier_gap_scale=0.8`, chỉnh bằng slider "Khe giữa 2 bậc chữ"); `1.0` là khe mặc định 60px.
- `carry` chỉ dùng khi cần hiển thị nhiều cụm chữ của **cùng một nhịp**; không dùng để lặp ảnh
  qua nhiều nhịp.

## Render
- `pl.analyze(script, content=...)` → rows có cột clip → `pl.render(rows, opt, preview=True)` ra preview trong `work/`.
- **Luôn dựng preview trước, chỉ xuất bản cuối khi người dùng duyệt.** Không tự xuất video hoàn chỉnh.
- **Đặt tên/đường dẫn** (pipeline tự sinh theo `opt.content`): giữ timestamp tạo file
  ở cuối để phân biệt các lần render.
  - Preview: `work/preview_<topic>_<YYYYMMDD_HHMMSS>.mp4`
  - Video thường hoàn chỉnh: `output/kienthuc/video_<topic>_<YYYYMMDD_HHMMSS>.mp4`
- Dọn preview và `work/job_*` cũ sau khi người dùng duyệt bản mới, kèm file tạm của phiên làm
  việc (`work/_*`: script khảo sát, ảnh cắt kiểm tra, contact sheet, bản thô đã nạp vào
  `assets/illus/`). Không dọn: `work/cache` (voice đã duyệt), `work/threads-script/`,
  `work/thumbs`, `work/browser_temp` và các trạng thái đăng bài (`fb_*.json`, `threads_state.json`).
- Mascot đứng yên đến cuối video rồi mới tụt xuống.
- Âm thanh chuyển mục dùng **pop** (không dùng whoosh) cho video thường.

## Quy tắc của lệnh "Làm video"
- "Làm video" = đi tới mp4 luôn (không dừng ở bàn giao); không có lệnh này thì vẫn dừng ở bàn giao như PHẦN 1.
- "Xử lý kịch bản" = chỉ chuẩn hóa, không render.
- Chủ đề thương vong/tang tóc/tai nạn chết người: tắt mascot, dùng ảnh tư liệu và giọng trang trọng. Ảnh thật là luật chung cho **mọi** chủ đề, không riêng nhóm này.
- Video thường xuất vào `output/kienthuc/`; preview luôn để trong `work/`.
