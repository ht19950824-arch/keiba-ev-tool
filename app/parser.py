from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

JP_NUM = str.maketrans("０１２３４５６７８９．，", "0123456789.,")
CID_NUM = {str(9872+i): str(i) for i in range(10)}
COURSES = ("札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉")


def norm(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", s)
    s = re.sub(r"\(cid:(\d+)\)", lambda m: CID_NUM.get(m.group(1), " "), s)
    return s.translate(JP_NUM).replace("\u3000", " ").strip()


def num(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", norm(s).replace(",", ""))
    return float(m.group()) if m else None


def extract_text(path: str | Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text(layout=False) or "" for page in pdf.pages)


def _parse_runner_line(line: str) -> dict[str, Any] | None:
    line = norm(line)
    m = re.match(r"^(?P<bracket>[1-8])\s*(?P<post>\d{1,2})\s+(?P<body>.+)$", line)
    if not m:
        return None
    body = m.group("body")
    sm = re.search(
        r"(?P<horse>.+?)\s*(?P<sex>[牡牝セ])(?P<age>\d{1,2})[^\s\d]*\s+"
        r"(?P<weight>\d{2}(?:\.\d+)?)\s+",
        body,
    )
    if not sm:
        return None
    tail = body[sm.end():]
    om = re.search(r"(?P<odds>\d{1,4}(?:[.．]\d)?)\s*$", tail)
    if not om:
        return None
    odds = num(om.group("odds"))
    before = tail[:om.start()].strip()
    tm = re.search(r"(?P<time>\d{1,2}[:：]\d{2}[.．]\d)", before)
    if not tm:
        return None
    prefix = before[:tm.start()].strip()
    wm = re.search(r"(?P<hw>\d{3})(?:\s*(?P<diff>[＋+－−±-]\s*\d{1,2}))?\s*$", prefix)
    if not wm:
        return None
    diff = (wm.group("diff") or "0").replace(" ", "")
    digits = re.sub(r"[^0-9]", "", diff)
    hw_diff = 0 if not digits else (-int(digits) if diff.startswith(("－", "-", "−")) else int(digits))
    return {
        "bracket": int(m.group("bracket")),
        "post": int(m.group("post")),
        "horse": sm.group("horse").strip(),
        "sex": sm.group("sex"),
        "age": int(sm.group("age")),
        "weight_carried": num(sm.group("weight")),
        "horse_weight": int(wm.group("hw")),
        "horse_weight_diff": hw_diff,
        "time": tm.group("time").replace("：", ":").replace("．", "."),
        "odds": odds,
    }


def _race_header(chunk: str, year_hint: str) -> dict[str, Any] | None:
    lines = [norm(x) for x in chunk.splitlines() if norm(x)]
    header_idx = next((i for i, line in enumerate(lines[:30]) if re.search(r"\b\d{5}\s*\d{1,2}月\s*\d{1,2}日", line)), None)
    if header_idx is None:
        return None
    header = lines[header_idx]
    dm = re.search(
        r"(?P<raceid>\d{5})\s*(?P<month>\d{1,2})月\s*(?P<day>\d{1,2})日.*?"
        r"（(?P<inside>[^）]+)）\s*第(?P<day_no>\d+)日\s*第(?P<raceno>\d+)競走",
        header,
    )
    if not dm:
        return None
    inside = dm.group("inside")
    course_re = "|".join(COURSES)
    modern = re.fullmatch(r"(?P<year>\d{4})年(?P<meeting>\d+)(?P<course>" + course_re + r")", inside)
    legacy = re.fullmatch(r"(?P<meeting>\d+)(?P<course>" + course_re + r")", inside)
    if modern:
        year, meeting, course = modern.group("year"), modern.group("meeting"), modern.group("course")
    elif legacy:
        year, meeting, course = year_hint, legacy.group("meeting"), legacy.group("course")
    else:
        return None
    dm_distance = re.search(r"第\d+競走.*?(?P<distance>\d[\d,]{2,6})\s*[ｍm]?\s*$", header)
    if not dm_distance:
        return None
    distance = int(dm_distance.group("distance").replace(",", ""))
    context = "\n".join(lines[header_idx:header_idx + 6])
    surface = "ダート" if "（ダート" in context else ("芝" if "（芝" in context else "障害")
    if "不良" in context:
        condition = "不良"
    elif "稍重" in context:
        condition = "稍重"
    elif re.search(r"(?:^|\n)重(?:$|\n)", context):
        condition = "重"
    else:
        condition = "良"
    return {
        "race_key": f"{year}-{course}-{meeting}-{dm.group('raceid')}",
        "race_date": f"{year}-{int(dm.group('month')):02d}-{int(dm.group('day')):02d}",
        "course": course,
        "meeting_no": meeting,
        "day_no": int(dm.group("day_no")),
        "race_no": int(dm.group("raceno")),
        "distance": distance,
        "surface": surface,
        "track_condition": condition,
    }


def parse_text(text: str, year_hint: str | None = None) -> list[dict[str, Any]]:
    text = norm(text)
    year_hint = year_hint or "unknown"
    chunks = re.split(r"(?m)(?=^\s*\d{5}\s*\d{1,2}月\s*\d{1,2}日)", text)
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        race = _race_header(chunk, year_hint)
        if race is None:
            continue
        runners = []
        for line in chunk.split("売得金", 1)[0].splitlines():
            p = _parse_runner_line(line)
            if p:
                runners.append({**race, **p})
        for finish, row in enumerate(runners, 1):
            row["finish"] = finish
            rows.append(row)
    return rows


def parse_pdf(path: str | Path) -> list[dict[str, Any]]:
    m = re.search(r"(19|20)\d{2}", str(path))
    return parse_text(extract_text(path), m.group(0) if m else None)
