from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

JP_NUM = str.maketrans("０１２３４５６７８９．，", "0123456789.,")

COURSES = ("札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉")


def norm(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", s)
    s = re.sub(r"\(cid:(987[2-9]|988[0-1])\)", lambda m: str(int(m.group(1)) - 9872), s)
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
    line = norm(line)
    m = re.match(r"^(?P<bracket>[1-8])\s*(?P<post>\d{1,2})\s+(?P<body>.+)$", line)
    if not m:
        return None

    body = m.group("body")
    sm = re.search(
        r"(?P<horse>.+?)\s*(?P<sex>[牡牝セ])(?P<age>\d{1,2})[^\s]*\s+"
        r"(?P<weight>\d{2}(?:\.\d+)?)\s+",
        body,
    )
    if not sm:
        return None

    tail = body[sm.end():]
    om = re.search(r"(?P<odds>\d{1,4}(?:[．.]\d)?)\s*$", tail)
    if not om:
        return None

    odds = num(om.group("odds"))
    before = tail[:om.start()].strip()
    tm = re.search(r"(?P<time>\d{1,2}[:：]\d{2}[．.]\d)", before)
    if not tm:
        return None

    prefix = before[:tm.start()].strip()
    wm = re.search(
        r"(?P<hw>\d{3})(?:\s*(?P<diff>[＋+－−±-―ー](?:\s*\d{1,2})?))?\s*$",
        prefix,
    )
    if not wm:
        return None

    diff = (wm.group("diff") or "0").replace(" ", "")
    digits = re.sub(r"[^0-9]", "", diff)
    if not digits:
        hw_diff = 0
    elif diff.startswith(("－", "-", "−")):
        hw_diff = -int(digits)
    else:
        hw_diff = int(digits)

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


def _race_header(chunk: str, year_hint: str) -> tuple[dict[str, Any], str] | None:
    prefix = "\n".join(chunk.splitlines()[:12])
    hm = re.search(
        r"(?P<raceid>\d{5})\s*(?P<month>\d{1,2})月\s*(?P<day>\d{1,2})日.*?"
        r"（(?:(?P<year>\d{4})年)?(?P<meeting>\d+)"
        r"(?P<course>" + "|".join(COURSES) + r")(?P<meeting_day>\d+)）"
        r"\s*第(?P<day_no>\d+)日\s*第(?P<raceno>\d+)競走",
        prefix,
        re.S,
    )
    if not hm:
        return None

    year = hm.group("year") or year_hint
    if not re.fullmatch(r"\d{4}", year):
        return None

    dm = re.search(
        r"第\d+競走.*?(?P<distance>\d[\d,]{2,6})",
        prefix,
        re.S,
    )
    if not dm:
        return None

    distance = int(dm.group("distance").replace(",", ""))
    race = {
        "race_key": f"{year}-{hm.group('course')}-{hm.group('meeting')}-{hm.group('raceid')}",
        "race_date": f"{year}-{int(hm.group('month')):02d}-{int(hm.group('day')):02d}",
        "course": hm.group("course"),
        "meeting_no": hm.group("meeting"),
        "day_no": int(hm.group("day_no")),
        "race_no": int(hm.group("raceno")),
        "distance": distance,
        "surface": "ダート" if "（ダート" in prefix else ("芝" if "（芝" in prefix else "障害"),
        "track_condition": (
            "不良" if "不良" in prefix else
            "稍重" if "稍重" in prefix else
            "重" if re.search(r"\n重\s*\n", prefix) else
            "良"
        ),
    }
    return race, hm.group("raceid")


def parse_text(text: str, year_hint: str | None = None) -> list[dict[str, Any]]:
    text = norm(text)
    if year_hint is None:
        year_hint = "unknown"

    chunks = re.split(r"(?=\d{5}\s*\d{1,2}月\s*\d{1,2}日)", text)
    rows: list[dict[str, Any]] = []

    for chunk in chunks:
        parsed = _race_header(chunk, year_hint)
        if parsed is None:
            continue
        race, _ = parsed

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
    m = re.search(r"(19|20)\d{2}", str(path))
    return parse_text(extract_text(path), m.group(0) if m else None)
