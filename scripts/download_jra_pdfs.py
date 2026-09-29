from __future__ import annotations
import argparse,json,time
from pathlib import Path
import requests

UA="Mozilla/5.0 (compatible; KeibaEVTool/0.5; respectful-low-rate-fetch)"
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--year",type=int,required=True)
    ap.add_argument("--index-dir",default="data/processed")
    ap.add_argument("--out",default="data/raw")
    ap.add_argument("--sleep",type=float,default=0.5)
    ap.add_argument("--limit",type=int,default=0)
    a=ap.parse_args()
    index=Path(a.index_dir)/f"jra_{a.year}_pdfs.json"
    if not index.exists():
        raise FileNotFoundError(f"Discovery index not found: {index}")
    items=json.loads(index.read_text(encoding="utf-8"))["links"]
    if a.limit: items=items[:a.limit]
    outdir=Path(a.out)/str(a.year); outdir.mkdir(parents=True,exist_ok=True)
    s=requests.Session(); s.headers.update({"User-Agent":UA,"Accept":"application/pdf,*/*"})
    ok=skipped=failed=0
    for i,item in enumerate(items,1):
        target=outdir/item["url"].rsplit("/",1)[-1]
        if target.exists() and target.stat().st_size>1000:
            ok+=1; continue
        last=None
        for attempt in range(4):
            try:
                r=s.get(item["url"],timeout=60)
                last=r.status_code
                if r.status_code==200 and r.content[:4]==b"%PDF":
                    target.write_bytes(r.content); ok+=1
                    print(f"[{i}/{len(items)}] {target}")
                    break
                if r.status_code in (404,410):
                    skipped+=1
                    print(f"[{i}/{len(items)}] skip HTTP {r.status_code}: {item['url']}")
                    break
                time.sleep(min(8.0,1.5*(attempt+1)))
            except requests.RequestException as e:
                last=str(e); time.sleep(min(8.0,1.5*(attempt+1)))
        else:
            failed+=1
            print(f"[{i}/{len(items)}] failed after retries: {item['url']} ({last})")
        time.sleep(a.sleep)
    print(f"downloaded={ok} skipped={skipped} failed={failed}")
    if failed:
        raise RuntimeError(f"{failed} PDF downloads failed")
if __name__=="__main__": main()
