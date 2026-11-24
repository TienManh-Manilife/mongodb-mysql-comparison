# TÌM HIỂU MONGODB, ÁP DỤNG XÂY DỰNG CSDL QUẢN LÝ NHÂN KHẨU VỚI DỮ LIỆU LỚN, SO SÁNH HIỆU NĂNG VỚI MYSQL TRÊN CÙNG DỮ LIỆU

## Thành viên:

```
Kiều Nhật Minh
Nguyễn Tuấn Linh
Nguyễn Tiến Mạnh
```

## Chạy thực nghiệm - Quy trình 1: Tạo dữ liệu và import dữ liệu (Dành cho lần đầu chưa tạo)

### Bước 1: Tạo môi trường ảo, kích hoạt, tải thư viện cần thiết

```
python -m venv venv

venv/Scripts/activate
```

### Bước 2: Sinh dữ liệu (Nếu dữ liệu chưa có trên máy)

```
python generate_population.py
```

### Bước 3: Pull MySQL và MongoDB về và kiểm tra dữ liệu

```
docker compose pull mysql mongodb

docker compose run --rm --no-deps -T client plan --run-id pop10m --seed 42 --ops 1000
```

### Bước 4: Import dữ liệu vào MySQL và MongoDB

- Khởi động MySQL -> import -> Dừng để giải phóng tài nguyên:

```
docker compose up -d --wait mysql

docker compose run --rm --no-deps -T client import --run-id pop10m --engine mysql --profile equivalent --batch-size 1000

docker compose stop mysql
```

- Khởi động MongoDB -> import -> Dừng để giải phóng tài nguyên:

```
docker compose up -d --wait mongodb

docker compose run --rm --no-deps -T client import --run-id pop10m --engine mongodb --profile equivalent --batch-size 1000

docker compose stop mongodb
```

## Chạy thực nghiệm - Quy trình 2: Chạy các kịch bản
