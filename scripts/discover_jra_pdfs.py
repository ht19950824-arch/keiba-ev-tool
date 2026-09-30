from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.jra.go.jp/"
REPORT = "https://www.jra.go.jp/datafile/seiseki/report/{year}.html"
COURSES = ("sapporo","hakodate","fukushima","niigata","tokyo","nakayama","chukyo","kyoto","hanshin","kokura")
UA = "Mozilla/5.0 (compatible; KeibaEVTool/0.5; respectful-low-rate-fetch)"

def discover(year: int, out: Path, sleep: float = 0.0):
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    page_url = REPORT.format(year=year)
    response = session.get(page_url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found = []
    seen = set()
    filename_re = re.compile(r"^" + str(year) + r"-([1-6])(" + "|".join(COURSES) + r")([0-9]{1,2})[.]pdf$", re.I)

    for anchor in soup.select("a[href]"):
        href = urljoin(page_url, anchor.get("href", ""))
        filename = href.rsplit("/", 1)[-1]
        match = filename_re.match(filename)
        if not match or href in seen:
            continue
        meeting = int(match.group(1))
        course = match.group(2).lower()
        day = int(match.group(3))
        seen.add(href)
        found.append({"year": year, "meeting": meeting, "course": course, "day": day, "url": href})

    course_order = {name: i for i, name in enumerate(COURSES)}
    found.sort(key=lambda item: (item["meeting"], course_order[item["course"]], item["day"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"year": year, "source": page_url, "links": found, "count": len(found)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return found

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--out", default="data/processed")
    parser.add_argument("--sleep", type=float, default=0.0)
    args = parser.parse_args()
    links = discover(args.year, Path(args.out) / f"jra_{args.year}_pdfs.json", args.sleep)
    print(f"discovered={len(links)}")
