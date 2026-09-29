from __future__ import annotations
import argparse,json,re
from pathlib import Path
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup
UA="Mozilla/5.0 (compatible; KeibaEVTool/0.4; respectful-low-rate-fetch)"
BASE="https://www.jra.go.jp/"
def links_from_homepage(session):
    r=session.get(BASE,headers={"User-Agent":UA},timeout=30); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser"); seen=set(); links=[]
    for a in soup.select('a[href*="accessD.html?CNAME="]'):
        href=urljoin(BASE,a.get("href","")); text=a.get_text(" ",strip=True)
        if href and href not in seen: seen.add(href); links.append({"url":href,"text":text})
    return links
def parse_page(session,url):
    r=session.get(url,headers={"User-Agent":UA},timeout=30); r.raise_for_status()
    tables=pd.read_html(r.text); target=None
    for t in tables:
        cols=" ".join(str(c) for c in t.columns)
        if "馬名" in cols and "騎手" in cols: target=t; break
    if target is None: return None
    target=target.copy(); target.columns=[str(c) for c in target.columns]; out=[]
    for _,row in target.iterrows():
        vals={k:(None if pd.isna(v) else str(v)) for k,v in row.items()}
        if re.search(r"\d+"," ".join(v or "" for v in vals.values())): out.append(vals)
    return out
def main(out):
    s=requests.Session(); links=links_from_homepage(s); races=[]
    for i,item in enumerate(links,1):
        try:
            rows=parse_page(s,item["url"])
            if rows: races.append({"url":item["url"],"label":item["text"],"rows":rows})
        except Exception as e: print(f"WARN {item['url']}: {e}")
        print(f"[{i}/{len(links)}]")
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({"source":BASE,"races":races},ensure_ascii=False,indent=2),encoding="utf-8"); print(f"races={len(races)}")
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="data/processed/current_entries.json"); a=ap.parse_args(); main(Path(a.out))
