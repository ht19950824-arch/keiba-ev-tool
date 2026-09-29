from __future__ import annotations
import argparse,json,time
from pathlib import Path
import requests

UA="Mozilla/5.0 (compatible; KeibaEVTool/0.3; respectful-low-rate-fetch)"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--year",type=int,required=True); ap.add_argument("--index-dir",default="data/processed")
    ap.add_argument("--out",default="data/raw"); ap.add_argument("--sleep",type=float,default=1.0); ap.add_argument("--limit",type=int,default=0)
    a=ap.parse_args()
    items=json.loads((Path(a.index_dir)/f"jra_{a.year}_index.json").read_text(encoding="utf-8"))["links"]
    if a.limit: items=items[:a.limit]
    outdir=Path(a.out)/str(a.year); outdir.mkdir(parents=True,exist_ok=True)
    s=requests.Session(); s.headers.update({"User-Agent":UA})
    for i,item in enumerate(items,1):
        target=outdir/item["url"].rsplit("/",1)[-1]
        if target.exists() and target.stat().st_size>1000: continue
        r=s.get(item["url"],timeout=60); r.raise_for_status(); target.write_bytes(r.content)
        print(f"[{i}/{len(items)}] {target}"); time.sleep(a.sleep)

if __name__=="__main__": main()
