---
name: lam-video-threads
description: Flow video Threads: chuyển bản thô (raw) các comment/bài đăng tiếng Việt (định dạng "# post/xx.png ..." + các dòng lời đọc "|| -") sang bản đã chỉnh để đọc thành tiếng / làm voice-over / dựng video, rồi dựng video từ card Threads. Converts raw Vietnamese social-media comment transcripts into a speakable script (expand teencode and English/app names phonetically, rewrite money/unit shorthand, strip emoji, normalize punctuation, replace laughter-only comments with [sound], re-wrap lines, keep every comment) and covers scraper, card layout and render. Use whenever the user pastes a raw comment dump in this format or says "bản thô", "bản đã chỉnh", "chỉnh sửa comment", "viết lại để đọc", "làm script đọc comment", "làm video Threads", even if they don't mention TTS.
---

# SKILL: Làm video Threads

Video Threads là **bài của người khác đăng trên Threads**: không sáng tác, không tìm ảnh minh
hoạ, không chèn meme. Skill này gồm hai phần: PHẦN 1 chuẩn hóa lời đọc nguyên văn, PHẦN 2 lấy
bài - dựng card - dựng video. Kịch bản Threads luôn dùng `|| -` (không phụ đề, chữ nằm trên card).

Flow video thường (`skills/lam-video-thuong/SKILL.md`) là flow riêng, tự viết kịch bản; mọi luật sáng
tác nội dung của nó không áp dụng ở đây.

## PHẦN 1 — CHUẨN HÓA LỜI ĐỌC COMMENT

Biến **bản thô** (copy từ ảnh chụp/OCR comment) thành **bản đã chỉnh**: người đọc/giọng TTS đọc trơn tru, không vấp teencode, không đọc emoji, không đọc nội dung nhạy cảm.

## Định dạng đầu vào / đầu ra (giữ nguyên)

```
# post/<số>-<loại>-<user>.png   (<nhãn> · @user · <N> like)
<dòng văn bản> || -
<dòng văn bản> || -
```

- **Giữ nguyên dòng tiêu đề `#`** (tên file, nhãn comment, số like, thứ tự số comment gốc). Số thứ tự nhảy cóc do người dùng tự xóa cũng giữ nguyên, không đánh số lại.
- Mỗi dòng văn bản kết thúc bằng ` || -`.
- Cách nhau một dòng trống giữa các comment.

## Quy trình

Làm lần lượt 5 bước:

### 1. Không xóa comment
Bản đã chỉnh giữ **toàn bộ** comment của bản thô, kể cả lạc đề, tranh cãi hay nhạy cảm —
đọc-hóa đúng nguyên văn như mọi comment khác. Việc bỏ comment nào là người dùng tự quyết
trong app; skill không xóa, không gợi ý xóa, không hỏi lại về việc xóa.

### 2. Comment không có chữ
- Comment chỉ có emoji/cười (`:)))`, `🤣🤣`, `😂`) hoặc **không có văn bản** (ảnh/sticker/GIF, ô trống) → thay bằng một dòng `[sound] || -`. Mục chỉ có dòng này mà có ảnh thì app tự bật zoom cho chính nhịp đó (tiếng chỉ phát một lần), không thêm dòng `[zoom]`.
- Comment **có chữ và có ảnh đính kèm** → giữ chữ như bình thường, **không** thêm dòng `[zoom]`; app tự thêm một nhịp zoom (kèm nhạc) ở cuối mục đó — bài gốc có ảnh cũng vậy — người dùng tắt/bật hoặc xoá nhịp đó trong bảng nhịp.
- Comment có chữ **và** emoji → bỏ emoji, giữ chữ (xem bước 4). Nếu chữ chỉ là phần râu ria của emoji (vd. "🤣" kẹp cuối lời đã đủ nghĩa) thì chỉ bỏ emoji.

### 3. Đọc-hóa viết tắt / teencode (thay theo bảng dưới)
Giữ **hoa/thường** như gốc (`Đcu` → `Đờ mờ`, `M ơi` → `Mày ơi`, `m ơi` → `mày ơi`). Chỉ thay khi đó là **từ nguyên vẹn** (không thay `k` bên trong từ khác).

| Gốc | Chỉnh thành |
|---|---|
| đcu, đcm | đờ mờ |
| vcl, vl | vờ cờ lờ / vờ lờ (xem ghi chú) |
| cmay, cm | chúng mày |
| cmt | còm men |
| ig | i gờ |
| wtf | oát đờ phắc |
| k, ko, hok | không |
| đc không | được không |
| đc | được |
| đ (đứng riêng, phủ định) | đếch |
| đ* | đéo |
| vs | với |
| r (đứng riêng, sau "rồi") / "đcđ r" | rồi / "được rồi" |
| v (đứng riêng, cảm thán) | vãi (không phải "vậy") |
| t, tao viết tắt (đại từ) | tao |
| m, mày viết tắt (đại từ) | mày / mình (theo ngữ cảnh) |
| tk | **tài khoản** khi nói tài khoản/ngân hàng/thẻ; **thằng** khi là tiếng chửi |
| nv | **nhân viên** khi nói quán/cửa hàng; **nhân vật** khi nói về người trong chuyện |
| sđt | số điện thoại |
| đt | điện thoại |
| ngta | người ta |
| bvs | băng vệ sinh |
| clm, cl | vãi |
| tr ơi, tr oii, tr oiii | Trời ơi |
| cgi, cgi đó | cái gì, cái gì đó |
| shockk, áa, lun, thui, r | sốc, á, luôn, thôi, rồi |
| md | mất dạy |
| tuk | tức |
| mọe, moẹ | mẹ |
| kh | không |
| j | gì |
| tr (đứng riêng) | trời |
| nãy h | nãy giờ |
| th (đứng cuối cụm: "ảnh th", "có v th") | thôi |
| z | vậy (không phải vãi) |
| kbit | không biết |
| bcuoi | buồn cười |
| dcd | đéo chịu được |
| dell, del (viết giảm của "đéo") | méo (không phải "đéo") |
| cdm | cái đờ mờ |
| 3/ | 3 que |
| cmnl | cờ mờ nờ lờ |
| pbvm | phân biệt vùng miền |
| vcd | vãi cả đái |
| TQ | Trung Quốc |
| VPN | vi pi ên |
| M3P | em báp pê (Mbappé) |
| Mbappe, Mbappé, Mpabbe (gõ sai) | em báp pê |

Ghi chú:
- `vcl` → **vờ cờ lờ**; `vl` → **vờ lờ**; `vl ra` → `vờ lờ ra`. Giữ nguyên số chữ cái được đọc.
- `t`/`m` chỉ đổi khi rõ là đại từ ("t khốn nạn quá" → "tao khốn nạn quá", "anh t" → "anh tao", "M ơi" → "Mày ơi"). `m` khi người viết tự nói về mình → **mình**; khi đang nói với người khác → **mày**. Ngữ cảnh mơ hồ thì để nguyên và hỏi.
- Chữ bị lặp ký tự để nhấn (`Dĩmm`, `shockk`) → gõ lại bình thường (**Dĩm**, **sốc**); không đổi từ ngữ.
- Từ bị lặp cả chữ (`kính kính phóng đại`, `chồng vô vô`) → bỏ chữ lặp, và nếu ngữ cảnh rõ nghĩa thì thay bằng từ đúng: `kính kính phóng đại` → **chiếc kính phóng đại**, `vô vô` → **vô**.
- Chữ cái đứng riêng làm đại từ phải đọc theo ngữ cảnh, không mặc định: `c` → **chị** (chị gái/xưng chị) hoặc **cậu** (bạn của cậu/mẹ), `b` → **bạn**, `m` → **mình**/**mày**, `t` → **tao**. Ngữ cảnh mơ hồ thì chọn cách đọc hợp lý nhất và ghi vào "Cần bạn xác nhận".
- **Không đụng** vào từ vẫn đọc được tự nhiên: `í`, `chả`, `thằng pê`, `cha pê`, `Pe`, `fan trung`, `bọn nó`.
- `đc không` → **được không**; `đc` → **được**. Đây là quy tắc đã chốt, áp dụng luôn, không hỏi lại. Chỉ thay `đc` khi là từ nguyên vẹn; giữ dấu câu và hoa/thường như gốc (`Đc không?` → `Được không?`).
- **Giữ nguyên từ địa phương / khẩu ngữ**, không "chuẩn hóa" thành tiếng phổ thông: `mẻ`, `dô`, `quài`, `bả`, `tui`, `cằn nhằn`, `lèm bèm`. Chỉ thêm dấu câu cho dễ đọc.
- Tên đầy đủ `Mbappe`/`Mbappé` (kể cả gõ sai `Mpabbe`) → **em báp pê**. Cách gọi ngắn `pê`, `Pe`, `thằng pê`, `cha pê` giữ nguyên vì người đọc đã quen.
- `3/` → **3 que** (kẻ ba que/xạo), giữ số `3` như gốc — TTS đọc "ba que".
- **Từ nói giảm nói tránh giữ nguyên**: `hấp diêm` (không sửa thành "hiếp dâm"), tương tự các từ né tránh khác. Người viết cố ý dùng cách nói nhẹ hơn.
- `dell` / `del` là cách người viết **cố ý viết giảm** của "đéo" → đọc **méo**, giữ đúng mức nhẹ đó (không nâng thành "đéo"). Áp dụng luôn, không hỏi lại.
- **Chết/giết ở giọng kể đời thường → `hẹo`** (chốt cách đọc): `ch*t`, `chết`, `💀` → **hẹo**; `chết cóng` → **hẹo**. Người viết đã dùng `hẹo`, `bỏ mạng`, `ra đi` thì giữ nguyên.
- Chỉ đổi khi **nghĩa là chết thật**. `chết` dùng làm mức độ (`cười chết`, `mệt chết`, `sợ chết`, `ghét chết đi được`) giữ nguyên, không thành "hẹo".
- **Không nói giảm trong tường thuật tội ác/thảm sát có thật** (Mỹ Lai, các vụ án mạng, tin tai nạn): giữ **giết**, **chết**, **sát hại** — viết `hẹo` cho 504 dân thường bị giết là bóp méo sự thật. Chỉ khôi phục `gi*t` → **giết**, không hạ nhẹ thêm.
- **Tên riêng giữ nguyên**: kể cả tên viết bằng romanization (`Hongxiuquan`) — không đổi sang Hán Việt hay dạng khác. Tên nhân vật nước ngoài khác vẫn phiên âm theo mục 3b nếu có cách đọc quen thuộc.

### 3b. Từ tiếng Anh / tên app / số + đơn vị → phiên âm đọc được
TTS đọc tiếng Anh rất tệ, phải viết theo cách người Việt đọc:

| Gốc | Chỉnh thành |
|---|---|
| viral | vai rồ |
| topic | tốp bít |
| joke | giốc |
| Raumania | rau má ni a |
| take away | mang đi |
| momo | mô mô |
| circle k | xơ cồ cây |
| cellphone | xeo phôn |
| iphone, ip16, ip 16 | ai phôn, ai phôn 16 |
| pro max, prm | Prô Mắc |
| seal, nguyên seal | siu, nguyên siu |
| low tech | lâu tết |
| bro, bros | bờ rồ |
| literally (literal) | thật sự (dịch nghĩa, không phiên âm) |
| please | pờ lia (chốt cách đọc; không viết "pli") |
| shopee, grab… (tên app khác) | phiên âm theo cách đọc thường ngày |

- Từ tiếng Anh có **nghĩa tiếng Việt thông dụng, nghe tự nhiên khi nói** (`literally` → thật sự, `take away` → mang đi, `so true` → đúng thật) thì **dịch nghĩa**, không phiên âm từng âm tiết. Chỉ phiên âm khi đó là tên riêng/tên app hoặc không có cách dịch gọn (`viral`, `joke`, `bro`, `momo`).

Số và đơn vị viết tắt — viết sao cho đọc ra lời:

| Gốc | Chỉnh thành |
|---|---|
| 10k, 10 ka | 10 ka |
| 5.00O, 5O00 (gõ sai) | 5000 |
| 7-8k/c, 10k/c | 7 8 ka một cái, 10 ka một cái |
| 3c/ng, 2c/ng | 3 cái một người |
| 20nghìn, 20 nghìn | 20 nghìn |
| km, 30km | ki lô mét, 30 ki lô mét |
| 2 3 chục cái | 2 3 chục cái (giữ) |
| 19/5/2005 (ngày/tháng/năm) | 19 tháng 5 năm 2 nghìn lẻ 5 |

- `k` **đứng sau một con số** luôn là "ka" (tiền), **không** phải "không". `k` đứng riêng giữa câu mới là "không".
- `/c`, `/ng`, `/1c` tách thành "một cái", "một người", "một cái"; bỏ dấu `/`.
- Số đếm bình thường (16, 18, 30, 20 nghìn) giữ chữ số — TTS đọc đúng.
- **Ngày tháng năm kiểu `d/m/yyyy` luôn viết dài** thành `<ngày> tháng <tháng> năm <năm>` (`19/5/2005` → `19 tháng 5 năm 2 nghìn lẻ 5`, `26/10/2026` → `26 tháng 10 năm 2 nghìn 26`) — TTS đọc `19/5/2005` bị vấp. Năm đọc theo cách nói thường ngày: 2005 → `2 nghìn lẻ 5`, 1999 → `1 nghìn chín trăm chín mươi chín`. Năm hiện tại (2 ngàn mấy) có thể đọc `2 nghìn 26`. Chỉ áp dụng cho ngày sinh/ngày cụ thể; mốc năm trần trụi trong câu ("năm 1932") giữ nguyên vì TTS đọc đúng.

### 4. Làm sạch ký tự
- Xóa toàn bộ emoji và emoticon (`🤣 😂 🙃 😕 😭 😃 :)))`, `:\u{2060}-\u{2060})`), kể cả emoji đứng một mình giữa câu (`🤡`, `🥲`, `👁️👄👁️`, `🫣`).
- Xóa ký tự thay thế vật thể `￼` (U+FFFC) — nó là ảnh/emoji dán từ Threads, TTS sẽ đọc thành tiếng lạ. Xóa luôn khoảng trắng dính quanh nó.
- Sửa khoảng trắng: bỏ khoảng trắng thừa trước dấu câu (`pê . Wtf` → `pê. oát đờ phắc`), thêm khoảng trắng sau dấu câu, bỏ dấu `…`/`.` / `,` thừa ở cuối dòng nếu là dấu cuối comment (`đọc k ngậm được mồm🤣` → không dấu).
- Giữ nguyên dấu phẩy ngắt nhịp giữa câu.
- **Chuẩn hóa dấu câu cho người đọc**: thêm dấu phẩy/chấm vào chỗ ngắt hơi tự nhiên của câu dài, viết hoa khi dòng bắt đầu một câu mới (dòng nối tiếp của cùng câu giữ chữ thường như gốc) (`xong dô mua mẻ nói` → `Xong dô mua, mẻ nói`). Câu hỏi giữ `?` sau khi đã Việt hóa (`cho nó v?` → `cho nó vậy?`).
- **Giữ nguyên số like, tên user, nội dung ý nghĩa**; **không** viết lại câu, không đổi từ ngữ, không sửa chính tả ngoài các bảng trên, không "làm đẹp" văn phong. Dấu câu/viết hoa là mức chỉnh tối đa.

### 5. Ngắt dòng lại
Xuống dòng theo **nhịp đọc** (cuối cụm/câu), không theo độ rộng ảnh gốc. Dòng gốc bị cắt giữa cụm (`nhà độc ‖ tài`) → nối lại, rồi ngắt ở chỗ hợp lý:

```
Thì cha pê lỡ mồm chả bảo quả ảnh ghép với nhà độc tài là hài nhất || -
nên chả bị bọn trung quốc nó chửi || -
```

**Tiêu chí:** mỗi dòng phải **đọc riêng vẫn hiểu** — là một cụm/câu trọn nghĩa, không cần dòng trước dòng sau bổ nghĩa. Độ dài chỉ là mục tiêu mềm, ranh giới nghĩa mới là ràng buộc cứng.

**Chọn điểm ngắt theo thứ tự ưu tiên** (dừng ở mức đầu tiên tách được mà vẫn đủ nghĩa):

1. Sau dấu `.` `?` `!` `;` `:` `,` có sẵn trong câu.
2. Trước liên từ/trạng từ nối giữa hai mệnh đề: "nên / nhưng / mà / vì / xong / rồi / thì / hoặc / còn".
3. Giữa chủ ngữ và vị ngữ của một mệnh đề (trước cụm động từ).
4. Giữa động từ và tân ngữ **dài** (≥4 chữ), khi 1–3 không dùng được.

Mỗi dòng mục tiêu ≲ 70–80 ký tự; nếu cắt đúng ranh giới nghĩa mà dòng dài hơn (tới ~100 ký tự) thì **để dài**, không cắt chữ cho đủ ngắn.

**Không bao giờ ngắt ở giữa:**

- Cặp từ cố định / cụm động từ + bổ ngữ ngắn: `hoàn toàn`, `chữa trị kiểu này`, `liên quan đến`, `phụ thuộc vào`, `độc lập với`, `đi kèm với`, `bị động kinh`…
- Danh từ ghép và tên riêng nhiều chữ: `bán cầu não`, `Cà Mau`, `Bà Rịa Vũng Tàu`, `Kiên Giang`, `Tây Bắc`.
- Số + danh từ + đơn vị: `2019`, `1 bé gái`, `81 xăng ti mét`, `19 tháng 5 năm 2 nghìn lẻ 5`.
- Sau hư từ/trợ từ khi thành phần đi kèm vẫn ở dòng sau: `của, với, và, là, thì, mà, để, bị, được, có, cho, từ, đến, ở, khi, một, những, các, cái, con, chiếc`.
- Trước đại từ/định ngữ nối vào cụm phía trên: `này, đó, ấy, kia, toàn, còn lại, nữa`.

Sai: `mang hai bộ DNA hoàn ⏎ toàn khác nhau` · `chữa trị ⏎ kiểu này` · `có ca của 1 bé ⏎ gái cắt hết…` · `giáp Lào thực chất lại khá ⏎ nóng`.
Đúng: `mang hai bộ DNA ⏎ hoàn toàn khác nhau…` · `chữa trị kiểu này ⏎ cho trẻ em bị động kinh nhiều` · `có ca của 1 bé gái ⏎ cắt hết một nửa bán cầu não` · `giáp Lào thực chất lại khá nóng ⏎ do ảnh hưởng…`.

**Tự kiểm trước khi giao:** đọc lần lượt từng dòng một mình. Dòng nào thấy cụt (kết thúc bằng hư từ, số, tên riêng dở dang, hoặc phải đọc dòng dưới mới hiểu) → nối với dòng kia rồi tách lại ở điểm an toàn khác.

## Ví dụ ngắn

Thô:
```
# post/04-cmt-ca-khong-biet-boi-.png   (comment 3 · @ca.khong.biet.boi.199 · 135 like)
mình lên ig đọc họ toàn trêu hài || -
vl ra đọc k ngậm đc mồm🤣 || -
```
Chỉnh:
```
# post/04-cmt-ca-khong-biet-boi-.png   (comment 3 · @ca.khong.biet.boi.199 · 135 like)
mình lên i gờ đọc họ toàn trêu hài vờ lờ ra || -
đọc không ngậm được mồm || -
```

Thô: `# post/02-cmt-hievelynz.png ... :))) || -` → Chỉnh: `[sound] || -`

Ví dụ thật (mẫu đã chốt 2026-10-29) — chú ý số + đơn vị, tiếng Anh, dấu câu, bỏ emoji:

Thô:
```
# post/02-cmt-her-diaryy.png   (comment 1 · @her.diaryy____ · 92 like)
Mình trước: Mới chiều nay luôn chứ đâu xa! || -
Ghé xe trà sữa bán take away mua ly Trà || -
bí đao 10k theo ĐÚNG GIÁ MENU NIÊM YẾT. || -
đưa cái bịch kêu mình TỰ ĐẬY NẮP, || -
TỰ BỎ BỊCH :)) Thấy dị quá, || -
"Mua có 10k bạc mất công hơi đâu mà làm, || -
đưa cho để vô là may rồi" 🤡 Alo??? || -
```
Chỉnh:
```
# post/02-cmt-her-diaryy.png   (comment 1 · @her.diaryy____ · 92 like)
Mình trước: Mới chiều nay luôn chứ đâu xa || -
Ghé xe trà sữa bán mang đi, mua ly Trà bí đao 10k || -
theo ĐÚNG GIÁ me nu NIÊM YẾT || -
Mình có mang theo ly cá nhân cho tiện || -
Bà chủ đổ nước vô ly mình xong || -
đưa cái bịch kêu mình TỰ ĐẬY NẮP, TỰ BỎ BỊCH || -
Thấy dị quá, chú đứng mua trước tốt bụng nói giúp || -
"Sao không đậy nắp ly đàng hoàng cho nó vậy?" || -
Thì bả thốt ra câu xanh rờn || -
"Mua có 10 ka bạc, mất công hơi đâu mà làm || -
đưa cho để vô là may rồi" || -
a lô? Menu người ta in 10k rành rành || -
chứ mình có trả giá || -
```
Lưu ý trong ví dụ: `:))` và `🤡` bị bỏ; `Alo???` → `a lô?` tách thành câu riêng; `take away` → `mang đi`; `v?` → `vậy?`. Bản mẫu của người dùng còn để lẫn `10 ka` và `10k` — mặc định **số tiền viết "ka" nhất quán cả bài** (`10 ka`), chỉ giữ `10k` khi người dùng nói rõ muốn giữ.

## Điểm cần chốt với người dùng (hỏi 1 lần, rồi nhớ)

Bản mẫu có vài chỗ không nhất quán; hỏi hoặc ghi chú ở cuối câu trả lời, không tự quyết:

1. **`TQ`**: có chỗ thành `Trung Quốc`, có chỗ `trung quốc` (chữ thường). Mặc định: **`Trung Quốc` viết hoa**; còn `trung quốc` chữ thường nếu gốc đã viết thường.
2. **Ảnh đính kèm**: không đánh dấu trong kịch bản — app tự thêm một nhịp zoom ở cuối mục có ảnh; mục chỉ có ảnh thì nhịp `[sound]` được bật zoom luôn (không phát lặp tiếng). Chỉ ghi chú ở "Cần bạn xác nhận" khi không chắc mục đó có ảnh hay không.

## Đầu ra cuối cùng

1. Bản đã chỉnh (khối code, đúng định dạng đầu vào), đầy đủ mọi comment của bản thô.
2. Một danh sách ngắn **"Cần bạn xác nhận"** (các điểm mơ hồ). Không lặp lại toàn bộ bản thô.

---

## PHẦN 2 — LẤY BÀI, DỰNG CARD VÀ RENDER

Bài/comment Threads là **phát ngôn của người khác**: giữ nguyên văn, chỉ chuẩn hóa cách TTS đọc.
Không áp dụng quy trình viết và quy tắc tìm ảnh minh hoạ của `skills/lam-video-thuong/SKILL.md`.

## 1. Lấy bài bằng scraper

Playwright headless, không tốn phí:

```powershell
.\.venv\Scripts\python.exe -m videomaker.threads_shot "<link>" --content <nội-dung> --tag post --top 4
```

Kết quả trong `assets/illus/<nội-dung>/post/`: `01-post-<handle>.png`, `02-cmt-<handle>.png`…
(rộng 1080, cao theo nội dung — tối đa 640), `threads.json` (dữ liệu đã bóc) và `script.txt`
(kịch bản sinh sẵn).

Kịch bản chữ có một mục `# <đường-dẫn-ảnh>   (mô tả)` cho mỗi card, bên dưới là từng nhịp đọc;
app đọc lại đúng các mục đó (`threads_shot.parse_sections`) nên sửa/thêm/bớt dòng đều được, và cột
clip của mỗi nhịp luôn là ảnh của mục chứa nó. Không muốn comment nào vào video thì tích ở ô
**Comment muốn xoá** rồi bấm **🗑 Xoá comment đã chọn**: ảnh của comment đó bị xoá, mục tương ứng
trong kịch bản chữ bị bỏ (bài gốc luôn giữ, các dòng đã sửa vẫn nguyên).

## 2. Lời đọc nguyên văn

- Lấy `post.text` trước, rồi `comments[].text` theo đúng thứ tự trên trang (comment chính theo thứ tự
  lướt, reply đứng ngay sau cha).
- Không viết lại, không thêm câu dẫn, không bỏ câu, không sửa chính tả/viết tắt của tác giả
  (`ko`, `b hít zô`, `ctrinh`). Chỉ được: chia nhịp, thêm tag, chuyển số viết bằng chữ sang chữ số.
- Ngày giờ / tuổi bài ("2 giờ", "26 thg 10", "26/10/2026") **đã hiện ở header card** nên không bao giờ
  đưa vào lời đọc — `card_from_raw` đã lọc bằng `is_dateish()`.
- Không xếp lại comment theo like: giữ đúng thứ tự Threads hiển thị. Threads dùng danh sách ảo, gỡ
  card khỏi DOM khi cuộn, nên scraper gom dần qua từng lượt cuộn (`crawl()`; dict giữ thứ tự lần đầu
  thấy = thứ tự trên trang), không đọc một lần ở cuối trang (làm vậy mất comment ở đầu trang).

## 3. Chia nhịp

- Mỗi nhịp khoảng 7–14 từ, cắt ở dấu câu; **dùng hàm của app**
  thay vì tự chia tay: `threads_shot.split_beats()`, `mark_emphasis()`, `build_editable_script()`.
  Chúng giữ nguyên từng chữ và ưu tiên cắt ở dấu câu / ranh giới ngoặc kép.
- `threads_shot.parse_sections()` đọc lại bản đã sửa để dựng bảng nhịp.

## 4. Ảnh của nhịp

**Mỗi nhịp dùng đúng ảnh của bài/comment chứa nó** — ghi thẳng tên file vào cột clip:
`post/01-post-uidasoda.png` cho mọi nhịp của bài gốc, `post/02-cmt-truogg36x.png` cho mọi nhịp của
comment đó… Đây là ngoại lệ của quy tắc "mỗi ảnh chỉ xuất hiện 1 lần": một ảnh card phải theo suốt
đoạn văn của nó. Không để trống cột clip (app sẽ bốc ảnh khác) và không chỉ ghi tag trần `[post]`.
Không tải ảnh minh hoạ thêm, không chèn meme: nội dung là phát ngôn của người khác, hình phải là
chính post/comment đó.

## 5. Bố cục card

- Card phủ **đủ bề ngang** khung overlay (`meme_w = 1080 − 2×threads_side_margin`; lề mặc định trong app
  là 108 → card rộng 864 = 80% khung) nên card vuông, dọc hay ngang đều cách mép trái/phải như nhau
  và không bị cắt nội dung.
- Chiều cao khung tự nở theo card cao nhất của cảnh (tab Threads tự tính, không còn dùng
  `threads_max_height`), nên mọi card kết thúc ở cùng một đường đáy chung.
- Chữ chạy **sát ngay dưới** card: neo **mép trên** tại đáy chung, cách card 0px, không đổi dù card cao
  thấp hay chữ 1–2 dòng. Card quá cao (dài hơn vùng an toàn) tự thu chiều cao để không tràn khung/chữ.
- Nhịp không phụ đề (`|| -`) canh **giữa dọc** khung (`THREADS_CARD_CENTER = 768`, tức 40% khung
  1920) chứ không dính đáy.
- Trên card, cỡ chữ cố định ~52px (không phóng to khi bài ngắn), header (avatar + ngày) dính mép trên,
  footer (like/bình luận) dính mép dưới; card không in dòng nguồn/link ở đáy. Bài dài quá 640px mới hạ
  cỡ chữ, cuối cùng mới cắt bớt.

## 6. Nhấn mạnh `*…*`

Chỉ đánh vào **số liệu** và **chữ tác giả cố ý viết HOA** (`KHÔNG`). Văn nói trên Threads không có
"từ khoá" đúng nghĩa — bọc từ dài nhất sẽ ra nhấn mạnh vô nghĩa (`*Thực* ra`, `*Vạn* lý trường thành`),
nên **thà không nhấn còn hơn nhấn bừa**. Đây là ngoại lệ của quy tắc "mỗi nhịp bắt buộc có ≥1 cụm
nhấn mạnh".

## 7. Chế độ ảnh và danh tính

- `auto` — post có ảnh/clip thì chụp nguyên card của Threads, post chỉ có chữ thì dựng card (cùng rộng
  1080, cao theo nội dung). `--mode shot|card` để ép.
- Danh tính trên card (`--ident`): mặc định `avatar` = ảnh đại diện + chữ "Threads" (không lộ tên tài
  khoản); `full` = avatar + tên; `no-avatar` = ẩn avatar giữ tên; `anon` = ẩn cả hai. Với `avatar`, ảnh
  chụp cũng bị ẩn link tên trong DOM trước khi chụp (giữ avatar + giờ đăng) nên không lộ tài khoản;
  `no-avatar`/`anon` thì mọi post tự chuyển sang dựng card.
- Ảnh chụp bị tối (lớp phủ đăng nhập) hoặc lỗi sẽ tự bỏ và dựng card thay thế.
- `threads.json` giữ `post.image` + `comments[].image` để đối chiếu; `script.txt` là bản đã gắn đúng ảnh
  cho từng nhịp.

## 8. Nhịp zoom và nhịp tiếng

- Mỗi mục (bài/comment) có ảnh/clip đính kèm thì app **tự thêm một nhịp `[zoom]`** (kèm nhạc) ở cuối
  mục đó. Comment chỉ có ảnh/không chữ → một nhịp `[sound] || -` và **chính nhịp đó bật zoom**, không
  viết thêm `[zoom]` (tiếng sẽ phát hai lần). GIF bỏ qua nhịp zoom.
- Nút 🗑 Xoá comment ghi `[nozoom]` vào dòng `#` của mục để không sinh nhịp zoom; chỉ có tác dụng sau
  khi bấm **Lưu kịch bản**. Tắt thủ công từng nhịp: bỏ chip Zoom ở bảng nhịp.
- Tiếng zoom nằm lẫn trong nhạc videoplayback nên không tách riêng được; đừng sửa file audio.

## 9. Chữ trên video Threads

- Kịch bản Threads luôn `|| -`: **không phụ đề, không karaoke** — người xem đọc đúng card. Luật parity
  số từ và cụm 2–4 từ của video thường **không áp dụng**; `mark_emphasis()` chỉ bọc số liệu và chữ tác
  giả cố ý viết HOA. Nhịp `[sound]`/`[zoom]` cũng mang `|| -`.

## 10. Render

- Cùng pipeline với video thường: `opt.threads=True`, `pl.analyze(script, content=...)` →
  `pl.render(rows, opt, preview=True)`.
- Preview: `work/preview_<topic>_<YYYYMMDD_HHMMSS>.mp4`; video hoàn chỉnh:
  `output/<topic>/video_<topic>_<YYYYMMDD_HHMMSS>.mp4`.
- **Không tự render và không ghi đè nguồn Threads** (`threads.json`, ảnh card đã chụp): chỉ dựng khi
  người dùng yêu cầu, luôn preview trước. Bản đã chỉnh lưu trong session; checkpoint bài scan và phiên
  chỉnh ở `work/threads-script/` — giữ lại khi dọn cache.

## 11. Trong app

Lấy bài/chụp ảnh xong, bản thô đổ thẳng vào ô Kịch bản (nhãn "BẢN CHỈNH") để người dùng sửa; bản thô
nguyên văn vẫn nằm ở card "Bản thô" (chỉ đọc, có nút sao chép) để đối chiếu; bấm **Lưu kịch bản** mới
ghi bản chỉnh vào session. Không tích hợp LLM vào app. Quy tắc UI: `docs/GIAO_DIEN_REACT.md`.
