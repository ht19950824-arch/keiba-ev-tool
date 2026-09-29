from __future__ import annotations
import argparse,json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

UA="Mozilla/5.0 (compatible; KeibaEVTool/0.3; respectful-low-rate-fetch)"

def collect(year:int,out:Path):
    url=f"https://www.jra.go.jp/datafile/seiseki/report/{year}.html"
    r=requests.get(url,headers={"User-Agent":UA},timeout=30)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    links=[]
    for a in soup.select('a[href$=".pdf"]'):
        href=a.get("href")
        if not href: continue
        if href.startswith("/"): href="https://www.jra.go.jp"+href
        elif not href.startswith("http"): href="https://www.jra.go.jp/datafile/seiseki/report/"+href
        links.append({"text":a.get_text(" ",strip=True),"url":href})
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"year":year,"source":url,"links":links},ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--year",type=int,required=True); ap.add_argument("--out",default="data/processed")
    a=ap.parse_args(); collect(a.year,Path(a.out)/f"jra_{a.year}_index.json")
