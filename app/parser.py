from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import pdfplumber

JP_NUM = str.maketrans("０１２３４５６７８９．，", "0123456789.,")

def norm(s: str) -> str:
    # pdfplumber may emit control-marker glyphs (e.g. \\x02, \\x03) around
    # odds, symbols, etc. Remove those markers while preserving line breaks.
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", s)
    # JRA PDFs can encode ASCII digits as pdfminer CID markers. In these
    # result PDFs the digit glyphs are 9872..9881 => 0..9.
    s = re.sub(r"\(cid:(987[2-9]|988[0-1])\)", lambda m: str(int(m.group(1)) - 9872), s)
    # Other CID markers are layout/annotation glyphs, not data digits.
    s = re.sub(r"\(cid:\d+\)", " ", s)
    return s.translate(JP_NUM).replace("\u3000", " ").strip()

def num(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", norm(s).replace(",", ""))
    return float(m.group()) if m else None

def extract_text(path: str | Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text(layout=True) or "" for page in pdf.pages)

def _parse_runner_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    m = re.match(r"^(?P<bracket>[1-8])\s*(?P<post>\d{1,2})\s+(?P<body>.+)$", line)
    if not m:
        return None
    body = m.group("body")
    sm = re.search(r"(?P<horse>.+?)(?P<sex>[牡牝セ])(?P<age>\d{1,2})[^\s]*\s+(?P<weight>\d{2}(?:\.\d+)?)\s+", body)
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
    wm = re.search(r"(?P<hw>\d{3})(?:\s*(?P<diff>[＋+－−±-―ー](?:\s*\d{1,2})?))?\s*$", prefix)
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
    chunks = re.split(r"(?=\d{5}\s+\d+月\s*\d+日)", text)
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        lines = chunk.splitlines()
        if not lines:
            continue

        header = re.search(
            r"(?P<raceid>\d{5})\s+(?P<month>\d+)月\s*(?P<day>\d+)日.*?"
            r"（(?P<year>\d{4})年(?P<meeting>\d+)(?P<course>[^）]+)）\s+"
            r"第(?P<day_no>\d+)日\s+第(?P<raceno>\d+)競走",
            lines[0],
        )
        if not header:
            # Some PDF extractors wrap the race header; search a short prefix.
            header = re.search(
                r"(?P<raceid>\d{5})\s+(?P<month>\d+)月\s*(?P<day>\d+)日.*?"
                r"（(?P<year>\d{4})年(?P<meeting>\d+)(?P<course>[^）]+)）\s+"
                r"第(?P<day_no>\d+)日\s+第(?P<raceno>\d+)競走",
                "\n".join(lines[:8]),
                re.S,
            )
        if not header:
            continue

        prefix = "\n".join(lines[:12])
        dm = re.search(r"(?P<distance>\d{3,5})\s*[\x00-\x1f\uFFFD]?\s*$", prefix.split("発走", 1)[0])
        if not dm:
            # Distance is normally the last number on the race-title line.
            dm = re.search(r"(?P<distance>\d{3,5})\s*[\x00-\x1f\uFFFD]?(?:\n|$)", prefix)
        if not dm:
            continue

        first = "\n".join(lines[:20])
        if "（ダート" in first:
            surface = "ダート"
        elif "（芝" in first:
            surface = "芝"
        else:
            surface = "障害"

        if "不良" in first:
            condition = "不良"
        elif "稍重" in first:
            condition = "稍重"
        elif re.search(r"\n重\s*\n", first):
            condition = "重"
        else:
            condition = "良"

        race = {
            "race_key": f"{header.group('year')}-{header.group('course')}-{header.group('meeting')}-{header.group('raceid')}",
            "race_date": f"{header.group('year')}-{int(header.group('month')):02d}-{int(header.group('day')):02d}",
            "course": header.group("course"),
            "meeting_no": header.group("meeting"),
            "day_no": int(header.group("day_no")),
            "race_no": int(header.group("raceno")),
            "distance": int(dm.group("distance").replace(",", "")),
            "surface": surface,
            "track_condition": condition,
        }

        runners: list[dict[str, Any]] = []
        for line in chunk.split("売得金", 1)[0].splitlines():
            p = _parse_runner_line(line)
            if p:
                runners.append({**race, **p})
        for finish, row in enumerate(runners, 1):
            row["finish"] = finish
            rows.append(row)
    return rows

def parse_pdf(path: str | Path) -> list[dict[str, Any]]:
    text = extract_text(path)
    rows = parse_text(text)
    return rows
