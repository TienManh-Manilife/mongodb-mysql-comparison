#!/usr/bin/env python3
"""Generate synthetic Vietnamese population CSV tables (standard library only).
The synthetic 12-digit identifier is NOT a valid identity credential.
"""
import argparse
import csv
import json
import random
import sys
import time
from collections import Counter
from contextlib import ExitStack
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
MAX_PEOPLE = 20_000_000
DEFAULT_PEOPLE = 10_000_000
DEFAULT_MIN = 3_000
DEFAULT_AS_OF = date(2026, 11, 24)

# Name pools are illustrative, not a census-derived distribution.
COMMON_SURNAMES = {
    'Nguyễn': 38, 'Trần': 12, 'Lê': 9, 'Phạm': 7, 'Hoàng': 5,
    'Huỳnh': 4, 'Phan': 4, 'Vũ': 3, 'Võ': 3, 'Đặng': 3,
    'Bùi': 3, 'Đỗ': 2, 'Hồ': 2, 'Ngô': 2, 'Dương': 2, 'Lý': 1,
}
OTHER_SURNAMES = ('Đào Đinh Mai Trịnh Đoàn Lương Lưu Trương Hà Cao Tạ Tô '
    'Châu Chử Chu La Lâm Lại Lã Tăng Từ Thái Thạch Trà Quách Kiều '
    'Tống Ninh Nông Mạc Mã Mạnh Vương Vi Văn Doãn Dư Dụ Trình '
    'Bạch Cấn Cù Khổng Khuất Khúc Lục Lữ Lò Lường Sầm Tôn '
    'Tưởng Uông Ung Phùng Phí Phó Tiêu Tề Thiều Thân Thẩm '
    'Thôi Thừa Triệu Nghiêm Hứa Hàn Giang Giáp Cung Cảnh '
    'Bành Bế Âu Bồ Cầm Đồng Hồng Hầu Hạ Liêu Lư Tào Tần').split()
SURNAME_POOL = tuple(s for s, weight in COMMON_SURNAMES.items()
                     for _ in range(weight * 20)) + tuple(OTHER_SURNAMES)

# Empty middle names are handled separately. Compound middle/given names
# are individual entries, separated by a vertical bar.
def pool(s):
    return tuple(dict.fromkeys(x.strip() for x in s.split('|') if x.strip()))

MALE_MIDDLE = pool('''Văn|Hữu|Đức|Minh|Quang|Hoàng|Quốc|Thành|Tuấn|Anh|Ngọc|Xuân|Thanh|Trọng|Đình|Công|Duy|Gia|Khắc|Khánh|Tiến|Thế|Nhật|Phúc|Bảo|Thiên|Hải|Hồng|Trung|Mạnh|Chí|Vĩnh|Đăng|Tấn|Thái|Hưng|Việt|Sỹ|Sĩ|Tường|Lâm|Bá|Đại|Đông|Nam|Huy|Long|Phong|Khang|Tùng|Kiến|Phước|Thịnh|Hiếu|Tuệ|Đan|Thiện|Trí|Nhân|Cảnh|Kim|Quý|Dũng|Thắng|Hiển|Hào|Khôi|Tâm|Kỳ|An|Bình|Cao|Thi|Tất|Trí Đức|Đức Minh|Hữu Phúc|Quốc Anh|Quang Minh|Gia Bảo|Hoàng Gia|Minh Đức|Thành Công|Văn Đức|Duy Khánh|Ngọc Minh|Xuân Trường|Thiên Ân|Tấn Phát|Đình Quang|Nhật Minh|Trọng Nghĩa|Phúc An|Bảo Long|Anh Tuấn|Hữu Nghĩa|Quốc Bảo|Đức Huy|Minh Quang|Gia Hưng|Thanh Phong|Hoàng Long''')
FEMALE_MIDDLE = pool('''Thị|Ngọc|Thu|Phương|Thanh|Mai|Hồng|Kim|Bảo|Minh|Khánh|Thùy|Thúy|Hoài|Diệu|Mỹ|Hà|Hải|Ánh|Như|Quỳnh|Tuyết|Xuân|Yến|Lan|Trúc|Thảo|Gia|Bích|Cẩm|Hương|Hiền|Tâm|Tuệ|An|Đan|Huyền|Thiên|Nhã|Tường|Vân|Tú|Linh|Ngân|Khả|Kiều|Hạnh|Anh|Hoàng|Nhật|Thục|Thư|Lệ|Hạ|Uyên|Lam|Vỹ|Mộc|Nhi|Bình|Châu|Diệp|Hân|Nguyệt|Vi|Hoài An|Ngọc Mai|Thị Thu|Thị Ngọc|Bảo Ngọc|Khánh Linh|Thanh Mai|Minh Anh|Phương Thảo|Thu Hà|Hồng Nhung|Kim Anh|Thùy Dương|Diệu Linh|Nhã Phương|Gia Hân|Tường Vy|Thiên Kim|Tuệ An|Cẩm Tú|Hà My|Ngọc Anh|Hoài Thương|Bích Ngọc|Mỹ Duyên|Hải Yến|Thanh Trúc|Xuân Mai|Quỳnh Anh|Ngọc Hà|Thảo Nguyên|Huyền Anh|An Nhiên''')
MALE_GIVEN = pool('''An|Anh|Bảo|Bình|Cảnh|Châu|Chiến|Chính|Chí|Công|Cường|Danh|Dũng|Duy|Đạt|Đăng|Đức|Đoàn|Đông|Giang|Hải|Hào|Hậu|Hiếu|Hiển|Hiệp|Hoàng|Hòa|Hoàn|Hùng|Hưng|Huy|Hữu|Hạnh|Khang|Khải|Khánh|Khiêm|Khôi|Kiên|Khoa|Khuê|Kiệt|Kỳ|Lâm|Lân|Long|Luân|Lộc|Lợi|Lương|Mạnh|Minh|Nam|Nghĩa|Nguyên|Nghị|Nhân|Nhật|Nhựt|Ninh|Phong|Phú|Phúc|Phước|Phương|Phát|Phi|Phụng|Quân|Quang|Quốc|Quý|Quyết|Sang|Sơn|Sỹ|Tài|Tân|Tâm|Tấn|Thái|Thành|Thắng|Thiện|Thiên|Thịnh|Thông|Thuận|Thức|Tiến|Toàn|Trí|Triết|Triều|Trọng|Trung|Trường|Tuấn|Tùng|Tú|Tuệ|Tuyên|Uy|Vinh|Vĩnh|Việt|Vũ|Vương|Xuân|Bách|Đại|Đan|Định|Đình|Kha|Khắc|Khương|Lực|Ngọc|Phan|Tín|Tĩnh|Viễn|Văn|Vượng|Hòa Bình|Hữu Tài|Minh Khang|Đức Anh|Bảo An|Quốc Huy|Thiên Phúc|Gia Huy|Anh Khoa|Tuấn Kiệt|Hoàng Nam|Nhật Huy|Duy Anh|Minh Triết|Đức Tâm|Phúc Lâm|Bảo Khôi|Thành Đạt|Quang Vinh|Hải Đăng|Gia Khánh|Trường An|Khánh Duy|Tấn Lộc|Việt Anh|Chí Thành''')
FEMALE_GIVEN = pool('''An|Anh|Ánh|Ân|Băng|Bích|Bình|Châu|Chi|Cúc|Diễm|Diệp|Diệu|Dung|Duyên|Dương|Đan|Đào|Giang|Hà|Hạ|Hải|Hân|Hạnh|Hiền|Hoa|Hoài|Hòa|Hồng|Huệ|Hương|Huyền|Khanh|Khánh|Kiều|Kim|Lam|Lan|Lệ|Liên|Linh|Loan|Ly|Mai|Mi|My|Minh|Mỹ|Na|Nga|Ngân|Ngọc|Nguyên|Nguyệt|Nhàn|Nhi|Như|Nhung|Nhã|Oanh|Phương|Phượng|Quỳnh|Quyên|Sa|San|Sương|Tâm|Tân|Thảo|Thanh|Thi|Thơ|Thư|Thùy|Thúy|Thục|Thu|Thương|Tiên|Trang|Trâm|Trinh|Trúc|Tú|Tuệ|Tuyết|Uyên|Uyển|Vân|Vi|Vy|Xuân|Yến|Yên|Ý|Tường|Hằng|Hảo|Hòa|Hợp|Hường|Thắm|Thơm|Thủy|Di|Hạ Vy|An Nhiên|Bảo Châu|Bảo Ngọc|Cẩm Ly|Diễm Quỳnh|Gia Hân|Hải Yến|Hoài An|Khánh An|Khánh Linh|Kim Ngân|Minh Anh|Minh Châu|Ngọc Anh|Ngọc Diệp|Ngọc Hà|Ngọc Hân|Ngọc Lan|Nhã Uyên|Phương Anh|Phương Linh|Phương Nhi|Quỳnh Anh|Quỳnh Chi|Thanh Hà|Thanh Hằng|Thanh Tâm|Thảo My|Thảo Nhi|Thiên An|Thu Hương|Thu Trang|Thùy Dương|Thúy Nga|Trúc Anh|Trúc Linh|Tường Vy|Tuệ Nhi|Uyên Nhi|Yến Nhi|Ánh Dương|Hà My|Hương Giang|Mộc Miên|Tú Anh|Vân Anh''')

ETHNICITIES = ('Kinh', 'Tày', 'Thái', 'Mường', 'Khmer', 'Mông', 'Nùng',
               'Dao', 'Hoa', 'Gia Rai', 'Ê Đê', 'Ba Na', 'Chăm', 'Sán Chay',
               'Sán Dìu', 'Hrê', 'Cơ Ho', 'Raglay', 'Khơ Mú', 'Khác')
# Illustrative weights, not official demographic statistics.
ETHNICITY_POOL = ('Kinh',) * 85 + ETHNICITIES[1:]
HOUSING = ('apartment', 'detached_house', 'townhouse', 'rural_house', 'other')
TENURE = ('owned', 'rented', 'family_provided', 'other')
OCCUPATIONS = ('farmer', 'factory_worker', 'office_worker', 'retail_worker',
               'driver', 'construction_worker', 'teacher', 'healthcare_worker',
               'engineer', 'software_developer', 'accountant', 'service_worker',
               'civil_servant', 'technician', 'fisher', 'craft_worker',
               'researcher', 'salesperson', 'designer', 'other')
SELF_EMPLOYED = ('shop_owner', 'farmer', 'freelancer', 'craft_worker', 'other')
SIZE_POOL = tuple(size for size, weight in enumerate((8, 15, 20, 25, 15, 9, 5, 3), 1)
                  for _ in range(weight))

HEADERS = {
    'provinces': ('province_code', 'province_name'),
    'wards': ('ward_code', 'ward_name', 'province_code'),
    'households': ('household_id', 'ward_code', 'household_size', 'housing_type',
                   'housing_tenure', 'address_label'),
    'persons': ('person_id', 'cccd', 'last_name', 'middle_name', 'given_name',
                'full_name', 'gender', 'date_of_birth', 'birth_ward_code',
                'nationality', 'ethnicity', 'marital_status', 'education_level',
                'employment_status', 'occupation'),
    'household_members': ('person_id', 'household_id', 'relationship_to_head'),
    'residence_history': ('residence_id', 'person_id', 'ward_code', 'residence_type',
                          'start_date', 'end_date', 'is_current'),
    'ward_population': ('ward_code', 'province_code', 'population', 'household_count'),
}


class SyntheticCCCD:
    """Random sampling without replacement using a fixed 1-billion-bit bitmap.
    000 prefix intentionally marks the synthetic namespace; no real CCCD rules.
    """
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.used = bytearray(125_000_000)  # ~119.2 MiB, independent of population

    def next(self):
        while True:
            n = self.rng.randrange(1_000_000_000)
            i, bit = divmod(n, 8)
            mask = 1 << bit
            if not self.used[i] & mask:
                self.used[i] |= mask
                return f'000{n:09d}'


def read_units(path):
    provinces, wards = {}, {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'Mã xã/phường', 'Xã/phường/đặc khu', 'Mã tỉnh', 'Tỉnh/thành phố'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f'CSV must contain columns: {sorted(required)}')
        for line, row in enumerate(reader, 2):
            pc, pn = row['Mã tỉnh'].strip(), row['Tỉnh/thành phố'].strip()
            wc, wn = row['Mã xã/phường'].strip(), row['Xã/phường/đặc khu'].strip()
            if not pc.isascii() or not pc.isdigit() or len(pc) > 2 or not pn:
                raise ValueError(f'Invalid province at line {line}')
            pc = pc.zfill(2)
            if pc in provinces and provinces[pc] != pn:
                raise ValueError(f'Conflicting province name: {pc}')
            provinces[pc] = pn
            if not wc and not wn:
                continue  # optional province-only rows
            if not wc.isascii() or not wc.isdigit() or len(wc) > 5 or not wn:
                raise ValueError(f'Invalid ward at line {line}')
            wc = wc.zfill(5)
            if wc in wards:
                raise ValueError(f'Duplicate ward: {wc} (line {line})')
            wards[wc] = (wn, pc)
    if not wards:
        raise ValueError('No wards found')
    return dict(sorted(provinces.items())), dict(sorted(wards.items()))


def allocate(wards, total, minimum, rng):
    """Exact integer allocation: base minimum + synthetic random weights."""
    n = len(wards)
    extra = total - minimum * n
    if extra < 0:
        raise ValueError(f'Need at least {minimum*n:,} people for {n:,} wards')
    weights = [rng.randint(1, 100) for _ in wards]
    denom = sum(weights)
    quotient, remainder = [], []
    for weight in weights:
        q, r = divmod(extra * weight, denom)
        quotient.append(q)
        remainder.append(r)
    left = extra - sum(quotient)
    for i in sorted(range(n), key=lambda j: (-remainder[j], j))[:left]:
        quotient[i] += 1
    return {wc: minimum + q for wc, q in zip(wards, quotient)}


def years_before(d, years):
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # Feb 29 -> Feb 28 in a non-leap year
        return d.replace(year=d.year - years, day=28)


def age_ranges(as_of):
    return [(years_before(as_of, age + 1).toordinal() + 1,
             years_before(as_of, age).toordinal()) for age in range(101)]


def person_status(age, rng):
    """Age-conditioned illustrative education and employment."""
    if age < 6:
        return 'none', 'not_applicable', ''
    if age < 12:
        return 'primary', 'student', ''
    if age < 15:
        return 'lower_secondary', 'student', ''
    if age < 18:
        return 'upper_secondary', 'student', ''
    if age < 23 and rng.random() < .35:
        return rng.choice(('upper_secondary', 'vocational', 'college')), 'student', ''
    education = rng.choice(('primary', 'lower_secondary', 'upper_secondary',
                            'upper_secondary', 'vocational', 'college', 'university'))
    if age >= 24 and rng.random() < .04:
        education = 'postgraduate'
    p = rng.random()
    if age >= 60 and p < .70:
        return education, 'retired', ''
    if p < .07 or (age >= 60 and p < .77):
        return education, 'unemployed', ''
    if p < .22 or (age >= 60 and p < .87):
        return education, 'self_employed', rng.choice(SELF_EMPLOYED)
    occupation = rng.choice(OCCUPATIONS)
    # Avoid assigning selected degree-dependent jobs to low education levels.
    if occupation in ('teacher', 'healthcare_worker', 'engineer', 'researcher') and education not in ('college', 'university', 'postgraduate'):
        occupation = 'service_worker'
    return education, 'employed', occupation


def household_members(size, rng):
    """Return tuples of (role, gender, age, marital_status)."""
    head_gender = rng.choice(('male', 'female'))
    head_age = rng.randint(20, 92) if size == 1 else rng.randint(24, 78)
    has_spouse = size >= 2 and rng.random() < .76
    if has_spouse:
        head_marital = 'married'
    elif head_age < 28:
        head_marital = rng.choice(('single', 'single', 'divorced'))
    else:
        head_marital = rng.choice(('single', 'single', 'divorced', 'widowed'))
    yield 'head', head_gender, head_age, head_marital
    remaining = size - 1
    youngest_parent = head_age
    if has_spouse:
        spouse_gender = 'female' if head_gender == 'male' else 'male'
        spouse_age = max(20, min(95, head_age + rng.randint(-8, 8)))
        yield 'spouse', spouse_gender, spouse_age, 'married'
        youngest_parent = min(head_age, spouse_age)
        remaining -= 1
    for _ in range(remaining):
        gender = rng.choice(('male', 'female'))
        draw = rng.random()
        if draw < .82:
            age = rng.randint(0, min(55, youngest_parent - 18))
            marital = 'single' if age < 22 else rng.choice(('single', 'single', 'married', 'divorced'))
            yield 'child', gender, age, marital
        elif draw < .94 and head_age <= 82:
            age = rng.randint(head_age + 18, min(100, head_age + 35))
            yield 'parent', gender, age, rng.choice(('married', 'widowed', 'divorced'))
        else:
            age = rng.randint(18, 90)
            yield 'other', gender, age, 'single' if age < 22 else rng.choice(('single', 'married', 'divorced', 'widowed'))


def generate(args):
    if not 1 <= args.people <= MAX_PEOPLE:
        raise ValueError(f'--people must be between 1 and {MAX_PEOPLE:,}')
    if args.min_per_ward < 1:
        raise ValueError('--min-per-ward must be at least 1')
    if args.as_of.year < 1901:
        raise ValueError('--as-of must be 1901 or later')
    if not 0 <= args.history_rate <= 1:
        raise ValueError('--history-rate must be between 0 and 1')
    if args.progress_every < 1:
        raise ValueError('--progress-every must be positive')
    provinces, wards = read_units(args.input)
    rng = random.Random(args.seed)
    allocation = allocate(wards, args.people, args.min_per_ward, rng)
    output = args.output or BASE / 'datasets' / f'population_{args.people}'
    output = output.resolve()
    # Never silently overwrite files or leave a new manifest claiming success.
    output.mkdir(parents=True, exist_ok=True)
    names = [f'{t}.csv' for t in HEADERS] + ['metadata.json']
    existing = [name for name in names if (output / name).exists()]
    if existing:
        raise FileExistsError(f'Output files already exist: {existing}. Use a new --output directory.')
    codes = tuple(wards)
    ranges = age_ranges(args.as_of)
    as_of_ord = args.as_of.toordinal()
    cccd = SyntheticCCCD(args.seed ^ 0x98A76B35)
    person_id = household_id = residence_id = 0
    gender_counts = Counter()
    next_progress = args.progress_every
    started = time.monotonic()
    print(f'Generating {args.people:,} people in {len(wards):,} wards; output: {output}', flush=True)
    with ExitStack() as stack:
        writers = {}
        for table, header in HEADERS.items():
            f = stack.enter_context((output / f'{table}.csv').open('x', encoding='utf-8', newline='', buffering=1024 * 1024))
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(header)
            writers[table] = writer
        writers['provinces'].writerows(provinces.items())
        writers['wards'].writerows((wc, wn, pc) for wc, (wn, pc) in wards.items())
        person_write = writers['persons'].writerow
        household_write = writers['households'].writerow
        member_write = writers['household_members'].writerow
        residence_write = writers['residence_history'].writerow
        for wc, (_, pc) in wards.items():
            target = allocation[wc]
            remaining = target
            start_households = household_id
            while remaining:
                size = min(remaining, rng.choice(SIZE_POOL))
                remaining -= size
                household_id += 1
                hh = household_id
                family_surname = rng.choice(SURNAME_POOL)
                household_write((hh, wc, size, rng.choice(HOUSING), rng.choice(TENURE), f'SYN-H-{hh:09d}'))
                for role, gender, age, marital in household_members(size, rng):
                    person_id += 1
                    gender_counts[gender] += 1
                    last_name = family_surname if role == 'head' or (role == 'child' and rng.random() < .88) else rng.choice(SURNAME_POOL)
                    middle_pool, given_pool = (MALE_MIDDLE, MALE_GIVEN) if gender == 'male' else (FEMALE_MIDDLE, FEMALE_GIVEN)
                    middle = '' if rng.random() < .14 else rng.choice(middle_pool)
                    given = rng.choice(given_pool)
                    full_name = ' '.join(part for part in (last_name, middle, given) if part)
                    birth_ord = rng.randint(*ranges[age])
                    dob = date.fromordinal(birth_ord).isoformat()
                    prior = (len(codes) > 1 and birth_ord < as_of_ord and rng.random() < args.history_rate)
                    previous_ward = wc
                    if prior:
                        while previous_ward == wc:
                            previous_ward = rng.choice(codes)
                    birth_ward = previous_ward if prior else wc
                    education, employment, occupation = person_status(age, rng)
                    person_write((person_id, cccd.next(), last_name, middle, given, full_name,
                                  gender, dob, birth_ward, 'Việt Nam', rng.choice(ETHNICITY_POOL),
                                  marital, education, employment, occupation))
                    member_write((person_id, hh, role))
                    current_start = dob
                    if prior:
                        current_start = date.fromordinal(rng.randint(birth_ord + 1, as_of_ord)).isoformat()
                        residence_id += 1
                        residence_write((residence_id, person_id, previous_ward, 'permanent', dob, current_start, 0))
                    residence_id += 1
                    current_type = 'temporary' if rng.random() < .10 else 'permanent'
                    residence_write((residence_id, person_id, wc, current_type, current_start, '', 1))
                    if person_id >= next_progress:
                        elapsed = time.monotonic() - started
                        print(f'{person_id:,}/{args.people:,} | {person_id / elapsed:,.0f} persons/s', flush=True)
                        next_progress += args.progress_every
            writers['ward_population'].writerow((wc, pc, target, household_id - start_households))
    assert person_id == args.people
    row_counts = {'provinces': len(provinces), 'wards': len(wards), 'households': household_id,
                  'persons': person_id, 'household_members': person_id,
                  'residence_history': residence_id, 'ward_population': len(wards)}
    metadata = {
        'synthetic': True, 'seed': args.seed, 'as_of': args.as_of.isoformat(),
        'minimum_requested_per_ward': args.min_per_ward,
        'minimum_actual_per_ward': min(allocation.values()),
        'maximum_actual_per_ward': max(allocation.values()),
        'history_rate_requested': args.history_rate,
        'cccd_namespace': '000 + 9 randomly sampled unique digits; synthetic only',
        'name_pool_sizes': {'surnames': len(set(SURNAME_POOL)), 'male_middle_including_empty': len(MALE_MIDDLE)+1,
                            'female_middle_including_empty': len(FEMALE_MIDDLE)+1,
                            'male_given': len(MALE_GIVEN), 'female_given': len(FEMALE_GIVEN)},
        'row_counts': row_counts, 'gender_counts': dict(gender_counts),
        'file_bytes': {f'{t}.csv': (output / f'{t}.csv').stat().st_size for t in HEADERS},
        'notes': ['Only administrative geography is sourced from input; all persons and households are synthetic.',
                  'Ward allocations, age, family, ethnicity and other distributions are illustrative, not calibrated to census.',
                  'Names can coincide with real people; identifiers are synthetic, not proof of identity.',
                  'Dates use ISO YYYY-MM-DD. Residence end_date is exclusive; empty means ongoing.',
                  'Current residence is a simplified single-primary-residence model, not legal registration history.',
                  'CSV uses UTF-8, comma delimiter, empty fields for missing values; preserve identifier codes as strings.'],
    }
    with (output / 'metadata.json').open('x', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
        f.write('\n')
    for table, count in row_counts.items():
        print(f'{table:20s} {count:>12,}')
    print(f'Completed. CSV size: {sum(metadata["file_bytes"].values()) / 1e9:.3f} GB. Output: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE / 'administrative_units.csv')
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--people', type=int, default=DEFAULT_PEOPLE)
    parser.add_argument('--min-per-ward', type=int, default=DEFAULT_MIN, help='Default 3000; lower only for test datasets')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--as-of', type=date.fromisoformat, default=DEFAULT_AS_OF)
    parser.add_argument('--history-rate', type=float, default=.15)
    parser.add_argument('--progress-every', type=int, default=100_000)
    args = parser.parse_args()
    try:
        generate(args)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')
    except KeyboardInterrupt:
        print('\nInterrupted. Partial CSVs may exist; no completion manifest was written. Use a new output directory.', file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    sys.exit(main())
