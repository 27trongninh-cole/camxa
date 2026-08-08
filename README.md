# PKG Editor

Web tool chỉnh sửa 2 file `.pkg` (thực chất là zip chứa các XML nén bằng zstd + dictionary tuỳ chỉnh):

- `CommonActions_pkg.bytes` → chèn `Track` cố định vào `commonresource/Back.xml`, trước thẻ `</Action>` (bật/tắt bằng toggle).
- `Actor_530_Actions_pkg.bytes` → trong `530_Dirak/skill/P2E1.xml`:
  - đặt `leftTimeSlerpBack` = `true` (cố định)
  - đặt `heightRate` = giá trị người dùng chọn (1.000 – 5.000, hiển thị dạng hệ số nhân x1 – x5)

Hai file `.pkg` gốc và dictionary được lưu sẵn trong `backend/data/`. Khi game cập nhật file mới, chỉ cần
thay file tương ứng trong thư mục này (giữ nguyên tên) và commit lại — không cần sửa code, miễn là
cấu trúc XML bên trong (`Back.xml`, `P2E1.xml`) không đổi.

File tải về được đóng gói theo đúng cấu trúc thư mục game:

```
Resources/<version>/Ages/Prefab_Characters/Prefab_Hero/
  CommonActions_pkg.bytes
  Actor_530_Actions_pkg.bytes
```

`<version>` lấy từ `backend/data/version.txt` — khi game ra bản mới, chỉ cần sửa nội dung file này
(ví dụ đổi `1.63.1` thành `1.64.0`) rồi commit, không cần đụng code.

## Cấu trúc repo

```
backend/
  main.py           # FastAPI app, endpoint /api/generate + serve frontend tĩnh
  pkg_codec.py       # Core: giải mã / mã hoá định dạng zstd+dict, đóng gói lại zip
  edits.py            # Logic chỉnh sửa cố định cho Back.xml và P2E1.xml
  data/
    CommonActions_pkg.bytes
    Actor_530_Actions_pkg.bytes
    zstd_dict.bin
    back_insert_snippet.xml   # Đoạn Track cố định chèn vào Back.xml
  requirements.txt
frontend/
  index.html          # UI: toggle + slider chọn heightRate
render.yaml
```

## Chạy thử ở local

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Mở trình duyệt tại `http://localhost:8000`.

## Deploy lên Render

Repo đã có sẵn `render.yaml` (Blueprint). Cách deploy:

1. Push repo này lên GitHub.
2. Trên Render: **New → Blueprint**, chọn repo này. Render sẽ tự đọc `render.yaml` và tạo 1 Web Service
   (`rootDir: backend`, chạy `uvicorn main:app`).
3. Sau khi deploy xong, backend vừa phục vụ API (`/api/generate`) vừa phục vụ luôn giao diện web tại
   domain Render cấp — không cần Netlify hay service thứ 2.

## Cập nhật file pkg gốc sau này

1. Thay file `.bytes` mới vào `backend/data/`, giữ đúng tên file cũ.
2. Nếu cấu trúc bên trong file XML mục tiêu (`Back.xml`, `P2E1.xml`) thay đổi tên thuộc tính / vị trí thẻ,
   cập nhật lại regex/marker tương ứng trong `backend/edits.py`.
3. Commit & push — Render tự động build & deploy lại.

## API

`GET /api/generate?insert_back_snippet=true|false&height_rate=1.000..5.000`

Trả về file `pkg_edited.zip` chứa 2 file:
- `CommonActions_pkg.bytes`
- `Actor_530_Actions_pkg.bytes`
