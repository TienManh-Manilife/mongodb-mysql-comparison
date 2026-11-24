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

- Khởi động MySQL -> import -> Tạo index -> Dừng để giải phóng tài nguyên:

```
docker compose up -d --wait mysql

docker compose run --rm --no-deps -T client import --run-id pop10m --engine mysql --profile equivalent --batch-size 1000

docker compose run --rm --no-deps -T --entrypoint python client -c "from benchmark.backends import connect; db = connect('mysql', 'equivalent'); db.set_secondary(True); print('MySQL indexing completed'); db.close()"

docker compose stop mysql
```

- Khởi động MongoDB -> import -> Tạo index -> Dừng để giải phóng tài nguyên:

```
docker compose up -d --wait mongodb

docker compose run --rm --no-deps -T client import --run-id pop10m --engine mongodb --profile equivalent --batch-size 1000

docker compose run --rm --no-deps -T --entrypoint python client -c "from benchmark.backends import connect; db = connect('mongodb', 'equivalent'); db.set_secondary(True); print('MongoDB indexing completed'); db.close()"

docker compose stop mongodb
```

## Chạy thực nghiệm - Quy trình 2: Chạy các kịch bản

Chạy tất cả workload, có index, 5 mức concurrency và 5 lần lặp.

Cả hai lệnh đều tự động khởi động container tương ứng, tạo secondary index, chạy benchmark, thu thập metrics CPU, RAM, Disk I/O và dừng container sau khi hoàn thành.

```
# MySQL:

python run_experiment.py --run-id mysql_indexed --engines mysql --profiles equivalent --indexes secondary --concurrency 1 4 8 16 32 --repeats 5 --ops 200 --aggregate-ops 3 --warmup 3 --seed 42 --reuse-import --reuse-plan results/pop10m/plan.json
```

```
MongoDB:

python run_experiment.py --run-id mongodb_indexed --engines mongodb --profiles equivalent --indexes secondary --concurrency 1 4 8 16 32 --repeats 5 --ops 200 --aggregate-ops 3 --warmup 3 --seed 42 --reuse-import --reuse-plan results/pop10m/plan.json
```

Tham số và Ý nghĩa:
--reuse-import: Sử dụng CSDL đã import
--engines: Chọn hệ quản trị cần benchmark
--profiles equivalent: Mô hình dữ liệu tương đương
--indexes secondary: Sử dụng secondary index
--concurrency 1 4 8: Thực nghiệm với 1, 4 và 8 client
--repeats 3: Lặp lại mỗi kịch bản 3 lần
--ops 100: 100 thao tác mỗi lượt
--aggregate-ops 2: 2 truy vấn mỗi lượt aggregation
--warmup 3: Làm nóng trước khi đo
--seed 42: Cố định tham số truy vấn ngẫu nhiên

## Tổng hợp kết quả và so sánh

- Gộp và phân tích toàn bộ kết quả:

```
$mysql = "results/mysql_indexed"
$mongo = "results/mongodb_indexed"
$import = "results/pop10m"
$output = "results/compare_10m_indexed"

New-Item -ItemType Directory -Force "$output/equivalent/mysql"
New-Item -ItemType Directory -Force "$output/equivalent/mongodb"

Copy-Item "$mysql/equivalent/mysql/*" "$output/equivalent/mysql/" -Recurse -Force
Copy-Item "$mongo/equivalent/mongodb/*" "$output/equivalent/mongodb/" -Recurse -Force

Copy-Item "$import/equivalent/mysql/import.json" "$output/equivalent/mysql/" -Force
Copy-Item "$import/equivalent/mongodb/import.json" "$output/equivalent/mongodb/" -Force

Copy-Item "$mysql/plan.json" "$output/plan.json" -Force

$config = Get-Content "$mysql/config.json" -Raw | ConvertFrom-Json
$config.engines = @("mysql", "mongodb")
$config.run_id = "compare_10m_indexed"

$config | ConvertTo-Json -Depth 100 |
    Set-Content "$output/config.json" -Encoding UTF8

python -c "from pathlib import Path; p=Path('$output/config.json'); p.write_text(p.read_text(encoding='utf-8-sig'), encoding='utf-8')"

python analyze_results.py $output
python plot_results.py $output

```

## Nguồn thông tin đầy đủ đơn vị hành chính (File administrative_units.csv)

Được trích xuất từ các file trên Github: thanglequoc/vietnamese-provinces-database
