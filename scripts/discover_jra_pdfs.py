from __future__ import annotations
import argparse,json,time
from pathlib import Path
import requests
COURSES=("sapporo","hakodate","fukushima","niigata","tokyo","nakayama","chukyo","kyoto","hanshin","kokura")
UA="Mozilla/5.0 (compatible; KeibaEVTool/0.4; respectful-low-rate-fetch)"
def discover(year:int,out:Path,sleep:float=.15):
    s=requests.Session(); s.headers.update({"User-Agent":UA}); found=[]
    for m in range(1,7):
        for course in COURSES:
            misses=0
            for d in range(1,13):
                url=f"https://www.jra.go.jp/datafile/seiseki/report/{year}/{year}-{m}{course}{d}.pdf"
                r=s.get(url,timeout=30)
                if r.status_code==200 and r.content[:4]==b"%PDF":
                    found.append({"year":year,"meeting":m,"course":course,"day":d,"url":url}); misses=0
                else: misses+=1
                time.sleep(sleep)
                if misses>=4 and d>=4: break
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"year":year,"source":"JRA official PDF URL pattern","links":found},ensure_ascii=False,indent=2),encoding="utf-8")
    return found
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--year",type=int,required=True); ap.add_argument("--out",default="data/processed"); ap.add_argument("--sleep",type=float,default=.15)
    a=ap.parse_args(); print(f"discovered={len(discover(a.year,Path(a.out)/f'jra_{a.year}_pdfs.json',a.sleep))}")

# annual index optimization will be applied after the current queued run
