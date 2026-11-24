import csv
import json
import time
from pathlib import Path
from collections import defaultdict


# ==================== CONFIG ====================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "datasets" / "population_10000000"

MAX_RESULTS = 20


# ==================== CSV UTILITIES ====================

def read_csv(table):
    path = DATA_DIR / f"{table}.csv"

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        yield from csv.DictReader(file)


def find_one(table, column, value):
    return next(
        (row for row in read_csv(table)
         if row[column] == str(value)),
        None
    )


def find_many(table, column, value, limit=None):
    results = []

    for row in read_csv(table):
        if row[column] == str(value):
            results.append(row)

            if limit is not None and len(results) >= limit:
                break

    return results


def display(data):
    print(json.dumps(data, ensure_ascii=False, indent=4))


# ==================== ADMINISTRATIVE UNITS ====================

PROVINCES = {
    row["province_code"]: row
    for row in read_csv("provinces")
}

WARDS = {
    row["ward_code"]: row
    for row in read_csv("wards")
}


def get_address(ward_code):
    ward = WARDS[ward_code]
    province = PROVINCES[ward["province_code"]]

    return {
        "ward_code": ward_code,
        "ward_name": ward["ward_name"],
        "province_code": province["province_code"],
        "province_name": province["province_name"]
    }


# ==================== PERSON QUERIES ====================

def find_by_cccd(cccd):
    return find_one("persons", "cccd", cccd)


def find_by_id(person_id):
    return find_one("persons", "person_id", person_id)


def find_by_name(name, limit=MAX_RESULTS):
    results = []
    name = name.strip().casefold()

    for row in read_csv("persons"):
        if name in row["full_name"].casefold():
            results.append(row)

            if len(results) >= limit:
                break

    return results


# ==================== RESIDENCE QUERIES ====================

def get_residence_history(person_id):
    results = find_many(
        "residence_history",
        "person_id",
        person_id
    )

    for row in results:
        row.update(get_address(row["ward_code"]))

    return results


def get_current_residence(person_id):
    for row in read_csv("residence_history"):
        if (
            row["person_id"] == str(person_id)
            and row["is_current"] == "1"
        ):
            row.update(get_address(row["ward_code"]))
            return row

    return None


# ==================== HOUSEHOLD QUERIES ====================

def get_household(person_id):
    member = find_one(
        "household_members",
        "person_id",
        person_id
    )

    if member is None:
        return None

    household = find_one(
        "households",
        "household_id",
        member["household_id"]
    )

    if household is None:
        return None

    household.update(
        get_address(household["ward_code"])
    )

    household["relationship_to_head"] = (
        member["relationship_to_head"]
    )

    return household


def get_household_members(household_id):
    members = find_many(
        "household_members",
        "household_id",
        household_id
    )

    if not members:
        return []

    member_map = {
        row["person_id"]: row["relationship_to_head"]
        for row in members
    }

    results = []

    # Chỉ duyệt persons.csv một lần
    for person in read_csv("persons"):
        person_id = person["person_id"]

        if person_id in member_map:
            person["relationship_to_head"] = (
                member_map[person_id]
            )

            results.append(person)

            if len(results) == len(member_map):
                break

    return results


# ==================== FULL PERSON PROFILE ====================

def get_person_profile(person):
    if person is None:
        return None

    person_id = person["person_id"]

    history = get_residence_history(person_id)

    current = next(
        (row for row in history
         if row["is_current"] == "1"),
        None
    )

    return {
        "personal_information": person,
        "birthplace": get_address(
            person["birth_ward_code"]
        ),
        "current_residence": current,
        "household": get_household(person_id),
        "residence_history": history
    }


# ==================== POPULATION STATISTICS ====================

def population_by_ward():
    results = []

    for row in read_csv("ward_population"):
        results.append({
            **get_address(row["ward_code"]),
            "population": int(row["population"]),
            "household_count": int(row["household_count"])
        })

    return sorted(
        results,
        key=lambda x: x["population"],
        reverse=True
    )


def population_by_province():
    stats = defaultdict(
        lambda: {
            "population": 0,
            "household_count": 0,
            "ward_count": 0
        }
    )

    for row in read_csv("ward_population"):
        code = row["province_code"]

        stats[code]["population"] += int(
            row["population"]
        )

        stats[code]["household_count"] += int(
            row["household_count"]
        )

        stats[code]["ward_count"] += 1

    results = [
        {
            "province_code": code,
            "province_name": PROVINCES[code]["province_name"],
            **data
        }
        for code, data in stats.items()
    ]

    return sorted(
        results,
        key=lambda x: x["population"],
        reverse=True
    )


# ==================== MAIN ====================

def main():
    while True:
        print("\n" + "=" * 60)
        print("POPULATION DATABASE - CSV QUERY SYSTEM")
        print("=" * 60)

        print("1. Tìm nhân khẩu theo CCCD")
        print("2. Tìm nhân khẩu theo ID")
        print("3. Tìm nhân khẩu theo họ tên")
        print("4. Tra cứu nơi cư trú hiện tại")
        print("5. Tra cứu lịch sử cư trú")
        print("6. Tra cứu hộ gia đình")
        print("7. Tra cứu thành viên hộ gia đình")
        print("8. Thống kê dân số theo xã/phường")
        print("9. Thống kê dân số theo tỉnh/thành phố")
        print("10. Thống kê tổng dân số")
        print("0. Thoát")

        choice = input("\nLựa chọn: ").strip()

        if choice == "0":
            break

        try:
            if choice == "1":
                value = input("Nhập CCCD: ").strip()
                query = lambda: get_person_profile(
                    find_by_cccd(value)
                )

            elif choice == "2":
                value = input("Nhập person_id: ").strip()
                query = lambda: get_person_profile(
                    find_by_id(value)
                )

            elif choice == "3":
                value = input("Nhập họ tên: ").strip()

                if not value:
                    print("Họ tên không được để trống.")
                    continue

                query = lambda: find_by_name(value)

            elif choice == "4":
                value = input("Nhập person_id: ").strip()
                query = lambda: get_current_residence(value)

            elif choice == "5":
                value = input("Nhập person_id: ").strip()
                query = lambda: get_residence_history(value)

            elif choice == "6":
                value = input("Nhập person_id: ").strip()
                query = lambda: get_household(value)

            elif choice == "7":
                value = input("Nhập household_id: ").strip()
                query = lambda: get_household_members(value)

            elif choice == "8":
                query = population_by_ward

            elif choice == "9":
                query = population_by_province

            elif choice == "10":
                query = lambda: {
                    "total_population": sum(
                        row["population"]
                        for row in population_by_province()
                    )
                }

            else:
                print("Lựa chọn không hợp lệ.")
                continue

            start = time.perf_counter()

            result = query()

            elapsed = time.perf_counter() - start

            if result is None or result == []:
                print("Không tìm thấy dữ liệu.")
            else:
                display(result)

            print(f"\nQuery time: {elapsed:.6f} seconds")
            print(f"Query latency: {elapsed * 1000:.3f} ms")

        except Exception as error:
            print(f"Lỗi truy vấn: {error}")


if __name__ == "__main__":
    main()
