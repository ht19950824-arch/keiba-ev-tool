from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import pdfplumber

JP_NUM = str.maketrans("０１２３４５６７８９．，", "0123456789.,")

def norm(s: str) -> str:
    return s.translate(JP_NUM).replace("\u3000", " ").strip()

def num(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", norm(s).replace(",", ""))
    return float(m.group()) if m else None

def extract_text(path: str | Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def _parse_runner_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    m = re.match(r"^(?P<bracket>[1-8])\s*(?P<post>\d{1,2})\s+(?P<body>.+)$", line)
    if not m:
        return None
    body = m.group("body")
    sm = re.search(r"(?P<horse>.+?)\s+(?P<sex>[牡牝セ])(?P<age>\d{1,2})[^\s]*\s+(?P<weight>\d{2}(?:\.\d+)?)\s+", body)
    if not sm:
        return None
    tail = body[sm.end():]
    odds_matches = list(re.finditer(r"(?P<odds>\d{1,4}(?:[．.]\d)?)\s*$", tail))
    if not odds_matches:
        return None
    om = odds_matches[-1]
    odds = num(om.group("odds"))
    before = tail[:om.start()].strip()
    tm = re.search(r"(?P<time>\d{1,2}[:：]\d{2}[．.]\d)", before)
    if not tm:
        return None
    prefix = before[:tm.start()].strip()
    wm = re.search(r"(?P<hw>\d{3})(?P<diff>[＋+－−±-]\s*\d{1,2})?$", prefix)
    if not wm:
        return None
    diff = (wm.group("diff") or "0").replace(" ", "")
    if diff in ("±0","0"):
        hw_diff = 0
    elif diff.startswith(("－","-","−")):
        hw_diff = -int(re.sub(r"[^0-9]","",diff))
    else:
        hw_diff = int(re.sub(r"[^0-9]","",diff))
    return {
        "bracket": int(m.group("bracket")), "post": int(m.group("post")),
        "horse": sm.group("horse").strip(), "sex": sm.group("sex"),
        "age": int(sm.group("age")), "weight_carried": num(sm.group("weight")),
        "horse_weight": int(wm.group("hw")), "horse_weight_diff": hw_diff,
        "time": tm.group("time").replace("：",":").replace("．","."),
        "odds": odds,
    }

def parse_text(text: str) -> list[dict[str, Any]]:
    text = norm(text)
    chunks = re.split(r"(?=\b\d{5}\s+\d+月\s*\d+日)", text)
    rows = []
    for chunk in chunks:
        hm = re.search(
            r"(?P<raceid>\d{5})\s+(?P<month>\d+)月\s*(?P<day>\d+)日.*?"
            r"（(?P<year>\d{4})年(?P<meeting>\d+)(?P<course>[^）]+)）\s+"
            r"第\d+日\s+第(?P<raceno>\d+)競走.*?"
            r"(?P<distance>[\d,]{3,5})\s*[^\d\n]{0,4}\n",
            chunk,
            re.S,
        )
        if not hm:
            continue
        race = {
            "race_key": f"{hm.group('year')}-{hm.group('course')}-{hm.group('meeting')}-{hm.group('raceid')}",
            "race_date": f"{hm.group('year')}-{int(hm.group('month')):02d}-{int(hm.group('day')):02d}",
            "course": hm.group("course"), "meeting_no": hm.group("meeting"),
            "race_no": int(hm.group("raceno")),
            "distance": int(hm.group("distance").replace(",","")),
            "surface": "ダート" if "（ダート" in chunk[:1800] else ("芝" if "（芝" in chunk[:1800] else "障害"),
            "track_condition": "不良" if "不良" in chunk[:1800] else ("稍重" if "稍重" in chunk[:1800] else ("重" if re.search(r"\n重\s*\n",chunk[:1800]) else "良")),
        }
        runners=[]
        for line in chunk.split("売得金",1)[0].splitlines():
            p=_parse_runner_line(line)
            if p: runners.append({**race,**p})
        for finish,row in enumerate(runners,1):
            row["finish"]=finish
            rows.append(row)
    return rows

def parse_pdf(path: str | Path) -> list[dict[str, Any]]:
    return parse_text(extract_text(path))
