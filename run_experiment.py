"""Host-side Docker orchestration. Never mounts the Docker socket in the client."""
import argparse,csv,json,os,re,subprocess,threading,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def compose(*args,capture=False):
    cmd=['docker','compose',*map(str,args)]
    return subprocess.run(cmd,cwd=ROOT,check=True,text=True,capture_output=capture)

def client(*args): return compose('run','--rm','--no-deps','-T','client',*args)

class Monitor:
    def __init__(self,container,path): self.container=container; self.path=path; self.stop=threading.Event(); self.thread=threading.Thread(target=self.run,daemon=True)
    def run(self):
        with self.path.open('w',encoding='utf-8') as f:
            while not self.stop.is_set():
                begin=time.time()
                try:
                    r=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}',self.container],cwd=ROOT,capture_output=True,text=True,timeout=15,check=True)
                    for line in r.stdout.splitlines():
                        if line.strip():
                            obj=json.loads(line); obj.update(sample_start_epoch=begin,sample_end_epoch=time.time()); f.write(json.dumps(obj)+'\n'); f.flush()
                except Exception as e:
                    f.write(json.dumps({'sample_start_epoch':begin,'sample_end_epoch':time.time(),'error':str(e)})+'\n'); f.flush()
                self.stop.wait(.5)
    def __enter__(self): self.thread.start(); return self
    def __exit__(self,*args): self.stop.set(); self.thread.join(timeout=20)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id',default=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    p.add_argument('--profiles',nargs='+',choices=['equivalent','optimized'],default=['equivalent','optimized'])
    p.add_argument('--engines',nargs='+',choices=['mysql','mongodb'],default=['mysql','mongodb'])
    p.add_argument('--indexes',nargs='+',choices=['core','secondary'],default=['core','secondary'])
    p.add_argument('--workloads',nargs='+',choices=[f'W{i:02d}' for i in range(1,17)],default=[f'W{i:02d}' for i in range(1,17)])
    p.add_argument('--concurrency',nargs='+',type=int,default=[1,4,8]); p.add_argument('--repeats',type=int,default=3); p.add_argument('--ops',type=int,default=200); p.add_argument('--aggregate-ops',type=int,default=3); p.add_argument('--write-batch',type=int,default=100); p.add_argument('--import-batch',type=int,default=1000); p.add_argument('--warmup',type=int,default=3); p.add_argument('--seed',type=int,default=42)
    p.add_argument('--reuse-import',action='store_true',help='Skip destructive import only when DB manifest matches. Normally use one profile and one engine with this option.')
    p.add_argument('--confirm-reset',action='store_true',help='Required before dropping dedicated benchmark database tables.')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.run_id): p.error('Invalid run-id')
    if not a.reuse_import and not a.confirm_reset: p.error('Import drops the dedicated benchmark database. Pass --confirm-reset explicitly.')
    if min(a.concurrency)<1 or max(a.concurrency)>64 or min(a.ops,a.repeats,a.aggregate_ops,a.write_batch,a.import_batch)<1 or a.warmup<0 or a.write_batch>1000 or a.import_batch>5000: p.error('Invalid numeric settings')
    if len(set(a.profiles))!=len(a.profiles) or len(set(a.engines))!=len(a.engines) or len(set(a.workloads))!=len(a.workloads) or len(set(a.indexes))!=len(a.indexes) or len(set(a.concurrency))!=len(a.concurrency): p.error('Duplicate options')
    if a.reuse_import and (len(a.profiles)!=1 or len(a.engines)!=1): p.error('--reuse-import requires exactly one profile and one engine')
    out=ROOT/'results'/a.run_id; out.mkdir(parents=True,exist_ok=False)
    (out/'config.json').write_text(json.dumps(vars(a),indent=2),encoding='utf-8')
    # Store effective configuration without credentials.
    conf=json.loads(compose('config','--format','json',capture=True).stdout)
    for s in conf.get('services',{}).values():
        if 'environment' in s:
            for k in list(s['environment']):
                if 'PASSWORD' in k.upper(): s['environment'][k]='[REDACTED]'
    (out/'compose_effective.json').write_text(json.dumps(conf,indent=2),encoding='utf-8')
    (out/'docker_version.txt').write_text(subprocess.run(['docker','version'],capture_output=True,text=True,check=True).stdout,encoding='utf-8')
    info=json.loads(subprocess.run(['docker','info','--format','{{json .}}'],capture_output=True,text=True,check=True).stdout)
    (out/'docker_info.json').write_text(json.dumps({k:info.get(k) for k in ['ServerVersion','OSType','OperatingSystem','Architecture','NCPU','MemTotal','Driver','CgroupDriver','CgroupVersion','KernelVersion']},indent=2),encoding='utf-8')
    compose('build','client')
    client('plan','--run-id',a.run_id,'--seed',a.seed,'--ops',max(a.ops,a.aggregate_ops,a.warmup,1))
    try:
        for i,profile in enumerate(a.profiles):
            # Reverse backend order on the second profile to reduce systematic order bias.
            engines=a.engines if i%2==0 else a.engines[::-1]
            for engine in engines:
                compose('stop','mysql','mongodb'); compose('up','-d','--wait',engine)
                cid=compose('ps','-q',engine,capture=True).stdout.strip()
                if not cid: raise RuntimeError(f'Cannot find {engine} container')
                d=out/profile/engine; d.mkdir(parents=True,exist_ok=True)
                image_id=subprocess.run(['docker','inspect','--format','{{.Image}}',cid],capture_output=True,text=True,check=True).stdout.strip()
                (d/'image_id.txt').write_text(image_id+'\n',encoding='utf-8')
                (d/'image_inspect.json').write_text(subprocess.run(['docker','image','inspect',image_id],capture_output=True,text=True,check=True).stdout,encoding='utf-8')
                common=['--run-id',a.run_id,'--engine',engine,'--profile',profile]
                if not a.reuse_import:
                    with Monitor(cid,d/'import_resources.jsonl'): client('import',*common,'--batch-size',a.import_batch)
                with Monitor(cid,d/'bench_resources.jsonl'):
                    client('bench',*common,'--indexes',*a.indexes,'--workloads',*a.workloads,'--concurrency',*a.concurrency,'--repeats',a.repeats,'--ops',a.ops,'--aggregate-ops',a.aggregate_ops,'--write-batch',a.write_batch,'--warmup',a.warmup)
                compose('stop',engine)
    finally: compose('stop','mysql','mongodb')
    subprocess.run([os.sys.executable,str(ROOT/'analyze_results.py'),str(out)],check=True,cwd=ROOT)
    if (out/'speedups.csv').exists(): subprocess.run([os.sys.executable,str(ROOT/'plot_results.py'),str(out)],check=True,cwd=ROOT)
    print(f'Results: {out}')
if __name__=='__main__': main()
