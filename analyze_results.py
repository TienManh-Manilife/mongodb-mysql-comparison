"""Aggregate measured runs and validate same-workload results, standard library only."""
import argparse,csv,json,re,statistics
from pathlib import Path
from collections import defaultdict

def csvwrite(path,rows):
    if not rows: return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,keys); w.writeheader(); w.writerows(rows)

def readcsv(path):
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def number(s):
    try: return float(s.rstrip('%'))
    except (TypeError,ValueError,AttributeError): return None

def bytesval(s):
    m=re.fullmatch(r'\s*([\d.]+)\s*([a-zA-Z]+)\s*',s)
    if not m: return None
    units={'B':1,'kB':1000,'KB':1000,'MB':10**6,'GB':10**9,'TB':10**12,'KiB':1024,'MiB':1024**2,'GiB':1024**3,'TiB':1024**4}
    return float(m[1])*units[m[2]] if m[2] in units else None

def pair(s):
    if not isinstance(s,str) or '/' not in s: return None,None
    return tuple(bytesval(x) for x in s.split('/',1))

def resource_samples(path):
    if not path.exists(): return []
    return [r for line in path.read_text(encoding='utf-8').splitlines() if line.strip() for r in [json.loads(line)] if not r.get('error')]

def resources(m,samples):
    # Only fully-contained intervals: short workloads can have no reliable samples.
    ss=[r for r in samples if r['sample_start_epoch']>=m['start_epoch'] and r['sample_end_epoch']<=m['end_epoch']]
    cpu=[v for r in ss if (v:=number(r.get('CPUPerc'))) is not None]
    mem=[v/1024**2 for r in ss if (v:=pair(r.get('MemUsage'))[0]) is not None]
    io=[pair(r.get('BlockIO')) for r in ss]; io=[x for x in io if None not in x]
    return {'resource_samples':len(ss),'cpu_mean_pct_docker':statistics.mean(cpu) if cpu else None,'cpu_peak_pct_docker':max(cpu) if cpu else None,'ram_mean_mib':statistics.mean(mem) if mem else None,'ram_peak_mib':max(mem) if mem else None,'block_read_sample_delta_mib':max(0,io[-1][0]-io[0][0])/1024**2 if len(io)>=2 else None,'block_write_sample_delta_mib':max(0,io[-1][1]-io[0][1])/1024**2 if len(io)>=2 else None}

def main(root):
    rows=[]; comparisons=[]; import_rows=[]; index_rows=[]; storage_rows=[]; groups=defaultdict(list); resource_cache={}; raw_groups=defaultdict(list)
    for f in sorted(root.glob('*/*/import.json')):
        d=json.loads(f.read_text(encoding='utf-8')); profile,engine=f.parent.parent.name,f.parent.name
        import_rows.append({'profile':profile,'engine':engine,'version':d['version'],'schema_seconds':d['schema_seconds'],'import_seconds':d['import_seconds'],'logical_records':d['logical_records'],'logical_records_per_second':d['logical_records_per_second']})
        for t,seconds in d['table_seconds'].items(): import_rows.append({'profile':profile,'engine':engine,'table':t,'import_seconds':seconds,'logical_records':d['counts'][t]})
    for f in sorted(root.glob('*/*/index_*.json')):
        d=json.loads(f.read_text(encoding='utf-8')); profile,engine=f.parent.parent.name,f.parent.name
        index_rows.append({'profile':profile,'engine':engine,'index_mode':d['index_mode'],'transition_seconds':d['transition_seconds'],'data_bytes':sum(r['data_bytes'] for r in d['storage']),'index_bytes':sum(r['index_bytes'] for r in d['storage'])})
        for s in d['storage']: storage_rows.append({'profile':profile,'engine':engine,'index_mode':d['index_mode'],**s})
    for f in sorted(root.glob('*/*/*_W*_c*_r*.json')):
        d=json.loads(f.read_text(encoding='utf-8')); folder=f.parent
        if folder not in resource_cache: resource_cache[folder]=resource_samples(folder/'bench_resources.jsonl')
        d.update(resources(d,resource_cache[folder])); rows.append(d)
        k=(d['profile'],d['engine'],d['index_mode'],d['workload'],d['concurrency']); groups[k].append(d)
        raw=readcsv(f.with_suffix('.csv')); vector=[(r['op_index'],r['digest'],r['error']) for r in raw]
        raw_groups[(d['index_mode'],d['workload'],d['concurrency'],d['repeat'])].append((d['profile'],d['engine'],vector,d.get('validation')))
    config=json.loads((root/'config.json').read_text(encoding='utf-8')) if (root/'config.json').exists() else {}
    expected={(p,e) for p in config.get('profiles',[]) for e in config.get('engines',[])}
    for k,vals in sorted(raw_groups.items()):
        first=vals[0]; all_valid=all(v[3]=='passed' and all(not r[2] for r in v[2]) for v in vals)
        # Same plan for every backend/profile; compare digest vector, not timings.
        same=all(v[2]==first[2] for v in vals)
        status='FAIL' if not all_valid or not same else 'INCOMPLETE' if expected and {(v[0],v[1]) for v in vals}!=expected else 'PASS' if len({v[1] for v in vals})>1 else 'SINGLE_BACKEND_ONLY'
        comparisons.append(dict(zip(('index_mode','workload','concurrency','repeat'),k),participants=';'.join(f'{v[0]}/{v[1]}' for v in vals),status=status))
    metrics=['mean_ms','p50_ms','p95_ms','p99_ms','std_ms','throughput_ops_s','affected_records_s','success_rate_pct','cpu_mean_pct_docker','cpu_peak_pct_docker','ram_mean_mib','ram_peak_mib','block_read_sample_delta_mib','block_write_sample_delta_mib']
    agg=[]
    for k,g in sorted(groups.items()):
        r=dict(zip(('profile','engine','index_mode','workload','concurrency'),k),repeats=len(g),validated_runs=sum(x.get('validation')=='passed' for x in g))
        for metric in metrics:
            vals=[x[metric] for x in g if x.get(metric) is not None]
            r[metric+'_run_mean']=statistics.mean(vals) if vals else None
            r[metric+'_run_sd']=statistics.stdev(vals) if len(vals)>1 else None
            r[metric+'_n']=len(vals)
        agg.append(r)
    speedups=[]; by_key={(r['profile'],r['index_mode'],r['workload'],r['concurrency'],r['engine']):r for r in agg}
    for key,m in by_key.items():
        if key[-1]!='mysql': continue
        other=by_key.get((*key[:-1],'mongodb'))
        if not other: continue
        matched=[v for v in comparisons if (v['index_mode'],v['workload'],v['concurrency'])==key[1:4]]
        valid=bool(matched) and all(v['status']=='PASS' for v in matched) and m['validated_runs']==m['repeats'] and other['validated_runs']==other['repeats'] and m['repeats']==other['repeats']
        def ratio(a,b): return a/b if valid and a is not None and b is not None and b>0 else None
        speedups.append(dict(zip(('profile','index_mode','workload','concurrency'),key[:-1]),validation='PASS' if valid else 'FAIL_OR_INCOMPLETE',mongo_latency_speedup=ratio(m['mean_ms_run_mean'],other['mean_ms_run_mean']),mongo_throughput_speedup=ratio(other['throughput_ops_s_run_mean'],m['throughput_ops_s_run_mean'])))
    for name,data in [('runs.csv',rows),('aggregated.csv',agg),('validation.csv',comparisons),('speedups.csv',speedups),('imports.csv',import_rows),('indexes.csv',index_rows),('storage.csv',storage_rows)]: csvwrite(root/name,data)
    print(f'{len(rows)} runs; {len(comparisons)} result groups; {sum(r["status"]=="FAIL" for r in comparisons)} mismatches')
    if any(r['status']=='FAIL' for r in comparisons): raise SystemExit('Validation failed: see validation.csv; do not use invalid speedups.')
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('results',type=Path); a=p.parse_args(); main(a.results)
