"""Optional SVG figures from validated speedups; no extra packages."""
import argparse,csv,html
from pathlib import Path
from collections import defaultdict

def main(root):
    path=root/'speedups.csv'
    if not path.exists(): raise SystemExit('Run analyze_results.py first; no speedup data')
    groups=defaultdict(list)
    with path.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['validation']=='PASS' and r['mongo_latency_speedup'] and r['mongo_throughput_speedup']:
                groups[(r['profile'],r['index_mode'],r['concurrency'])].append(r)
    output=root/'figures'; output.mkdir(exist_ok=True)
    for key,rows in sorted(groups.items()):
        rows.sort(key=lambda r:r['workload']); w=880; h=110+len(rows)*40
        for metric,title in [('mongo_latency_speedup','Mean latency: MySQL / MongoDB'),('mongo_throughput_speedup','Throughput: MongoDB / MySQL')]:
            values=[float(r[metric]) for r in rows]; maximum=max(1.0,*values)*1.14; x0=105; span=670
            svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" fill="white"/>',f'<text x="22" y="31" font-family="sans-serif" font-size="20" font-weight="bold">{html.escape(title)}</text>',f'<text x="22" y="56" font-family="sans-serif" font-size="13" fill="#475569">{html.escape(" / ".join(key))} · &gt;1 favors MongoDB; &lt;1 favors MySQL</text>']
            for i,(r,v) in enumerate(zip(rows,values)):
                y=72+i*40; bar=v/maximum*span
                svg.extend([f'<text x="22" y="{y+18}" font-family="sans-serif" font-size="13">{r["workload"]}</text>',f'<rect x="{x0}" y="{y}" width="{bar:.2f}" height="25" rx="3" fill="#287a67"/>',f'<text x="{min(x0+bar+7,w-75):.2f}" y="{y+18}" font-family="sans-serif" font-size="12">{v:.3g}×</text>'])
            ref=x0+span/maximum; svg.extend([f'<line x1="{ref}" x2="{ref}" y1="66" y2="{h-20}" stroke="#475569" stroke-dasharray="4 4"/>','</svg>'])
            (output/('_'.join(key)+'_'+metric+'.svg')).write_text('\n'.join(svg),encoding='utf-8')
    print(f'{len(groups)*2} SVG figures written to {output}')
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('results',type=Path); main(p.parse_args().results)
