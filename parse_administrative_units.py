"""Parse the Vietnam administrative JSON into the population generator CSV contract."""
import argparse,csv,json
from pathlib import Path

BASE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--input',type=Path,default=BASE/'json'/'vn_only_simplified_json_generated_data_vn_units.json'); p.add_argument('--output',type=Path,default=BASE/'administrative_units.csv'); a=p.parse_args()
    data=json.loads(a.input.read_text(encoding='utf-8-sig')); out=[]; provinces=set(); wards=set()
    def get(obj,k):
        return obj[k] if k in obj else obj[k[0].lower()+k[1:]]
    for province in data:
        pc=str(get(province,'Code')); pn=get(province,'FullName')
        if pc in provinces: raise ValueError(f'Duplicate province: {pc}')
        provinces.add(pc)
        for ward in get(province,'Wards'):
            wc=str(get(ward,'Code')); wn=get(ward,'FullName')
            if wc in wards or str(get(ward,'ProvinceCode'))!=pc: raise ValueError(f'Invalid ward: {wc}')
            wards.add(wc); out.append((len(out)+1,wc,wn,pc,pn))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['STT','Mã xã/phường','Xã/phường/đặc khu','Mã tỉnh','Tỉnh/thành phố']); w.writerows(out)
    print(f'{len(provinces)} provinces; {len(wards)} wards; {a.output}')
if __name__=='__main__': main()
