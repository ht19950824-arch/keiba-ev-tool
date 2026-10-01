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
    soup=BeautifulSoup(r.text,"html.parser"); links=[]
    def add(href,text=""):
        href=urljoin(BASE,href)
        if "accessD.html?CNAME=" in href: links.append({"url":href,"text":text})
    for a in soup.select('a[href]'):
        href=urljoin(BASE,a.get("href",""))
        if "/keiba/race/" in href and ("syutsuba" in href or "accessD" in href):
            try:
                pr=session.get(href,headers={"User-Agent":UA},timeout=30)
                if pr.ok:
                    ps=BeautifulSoup(pr.text,"html.parser")
                    for x in ps.select('a[href*="accessD.html?CNAME="]'): add(x.get("href",""),x.get_text(" ",strip=True))
                    for m in re.finditer(r'accessD\.html\?CNAME=([^\'"]+)',pr.text,flags=re.I): add(f"/JRADB/accessD.html?CNAME={m.group(1)}")
            except Exception as e: print(f"WARN race-page {href}: {e}")
    for direct in ("/keiba/race/090/syutsuba.html","/keiba/race/091/syutsuba.html"):
        try:
            pr=session.get(urljoin(BASE,direct),headers={"User-Agent":UA},timeout=30)
            if pr.ok:
                ps=BeautifulSoup(pr.text,"html.parser")
                for x in ps.select('a[href*="accessD.html?CNAME="]'): add(x.get("href",""),x.get_text(" ",strip=True))
                for m in re.finditer(r'accessD\.html\?CNAME=([^\'"]+)',pr.text,flags=re.I): add(f"/JRADB/accessD.html?CNAME={m.group(1)}")
        except Exception as e: print(f"WARN direct syutsuba {direct}: {e}")
    # JRA's public DB selector exposes the complete current meeting/day navigation
    # even when the feature-page syutsuba notice still says "scheduled".
    seeds=[
        "https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0105202604021120261004%2FC5",
        "https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0108202604021120261004%2FA3",
    ]
    seeds += list(dict.fromkeys(x["url"] for x in links))
    for seed in dict.fromkeys(seeds):
        try:
            pr=session.get(seed,headers={"User-Agent":UA},timeout=30)
            if pr.ok:
                ps=BeautifulSoup(pr.text,"html.parser")
                for x in ps.select('a[href*="accessD.html?CNAME="]'): add(x.get("href",""),x.get_text(" ",strip=True))
                for m in re.finditer(r'accessD\.html\?CNAME=([^\'"]+)',pr.text,flags=re.I): add(f"/JRADB/accessD.html?CNAME={m.group(1)}")
        except Exception as e: print(f"WARN accessD seed {seed}: {e}")
    unique=[]; seen=set()
    for item in links:
        if item["url"] not in seen: seen.add(item["url"]); unique.append(item)
    return unique
def parse_page(session,url):
    r=session.get(url,headers={"User-Agent":UA},timeout=30); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser"); page_text=soup.get_text(" ",strip=True); target=None
    for t in pd.read_html(r.text):
        if hasattr(t.columns,"levels"):
            flat=[]
            for col in t.columns:
                parts=[str(v).strip() for v in (col if isinstance(col,tuple) else (col,)) if str(v).strip() not in ("","nan")]
                flat.append(" ".join(parts))
            t=t.copy(); t.columns=flat
        if "馬名" in " ".join(map(str,t.columns)) and "騎手" in " ".join(map(str,t.columns)): target=t; break
    if target is None:
        for table in soup.find_all("table"):
            if "馬名" in " ".join(table.stripped_strings) and "騎手" in " ".join(table.stripped_strings):
                try: target=pd.read_html(str(table))[0]; break
                except Exception: pass
    if target is None: return None
    target=target.copy(); target.columns=[str(c) for c in target.columns]; out=[]
    for _,row in target.iterrows():
        vals={k:(None if pd.isna(v) else str(v)) for k,v in row.items()}
        if re.search(r"\d+"," ".join(v or "" for v in vals.values())): out.append(vals)
    meta={}
    m=re.search(r"(\d{4})年(\d+)月(\d+)日.*?(\d+)回(.+?)(\d+)日\s*(\d+)レース.*?コース：([\d,]+)メートル（(芝|ダート)",page_text)
    if m: meta={"race_date":f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}","course":m.group(5),"meeting_no":m.group(4),"day_no":int(m.group(6)),"race_no":int(m.group(7)),"distance":int(m.group(8).replace(",","")),"surface":m.group(9)}
    return {"meta":meta,"rows":out}
def main(out):
    s=requests.Session(); links=links_from_homepage(s); races=[]
    for i,item in enumerate(links,1):
        try:
            parsed=parse_page(s,item["url"])
            if parsed: races.append({"url":item["url"],"label":item["text"],**parsed})
        except Exception as e: print(f"WARN {item['url']}: {e}")
        print(f"[{i}/{len(links)}]")
    out.parent.mkdir(parents=True,exist_ok=True); status="published" if races else "not_published_or_no_entries"
    payload={"source":BASE,"fetched_at":pd.Timestamp.now(tz="Asia/Tokyo").isoformat(),"status":status,"race_count":len(races),"row_count":sum(len(r.get("rows",[])) for r in races),"races":races}
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); print(f"status={status} races={len(races)} rows={sum(len(r.get('rows',[])) for r in races)}")
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="data/processed/current_entries.json"); a=ap.parse_args(); main(Path(a.out))
