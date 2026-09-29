from __future__ import annotations
import argparse,json,re,time
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

UA="Mozilla/5.0 (compatible; KeibaEVTool/0.4; respectful-low-rate-fetch)"
BASE="https://www.jra.go.jp/"

def collect(out:Path):
    r=requests.get(BASE,headers={"User-Agent":UA},timeout=30); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    links=[]
    for a in soup.select('a[href*="accessD.html?CNAME="]'):
        href=urljoin(BASE,a.get("href",""))
        text=a.get_text(" ",strip=True)
        if href and href not in [x["url"] for x in links]:
            links.append({"url":href,"text":text})
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"source":BASE,"links":links},ensure_ascii=False,indent=2),encoding="utf-8")
    return links

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="data/processed/current_entry_links.json")
    a=ap.parse_args(); print(f"links={len(collect(Path(a.out)))}")
