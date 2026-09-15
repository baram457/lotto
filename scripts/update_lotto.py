#!/usr/bin/env python3
"""로또 당첨번호 자동 수집 → CSV + JSON 생성"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote
try:
    import requests
except ImportError:
    print("requests 필요: pip install requests")
    sys.exit(1)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.dhlottery.co.kr/",
}
API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "lotto_history.csv"
JSON_PATH = ROOT / "docs" / "data" / "lotto_history.json"

START_DATE = date(2002, 12, 7)
SLEEP_BETWEEN = 0.3


def fetch_draw(round_no: int, retries: int = 2) -> dict | None:
    target = API.format(round_no)
    urls = [
        f"https://api.allorigins.win/raw?url={quote(target, safe='')}",
        f"https://corsproxy.io/?url={quote(target, safe='')}",
        f"https://thingproxy.freeboard.io/fetch/{target}",
        target,
    ]

    for url in urls:
        for attempt in range(1, retries + 1):
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    break
                data = r.json()
                if data.get("returnValue") != "success":
                    return None
                return {
                    "round": round_no,
                    "date": data.get("drwNoDate", ""),
                    "nums": sorted(int(data[f"drwtNo{i}"]) for i in range(1, 7)),
                    "bonus": int(data["bnusNo"]),
                }
            except Exception:
                if attempt < retries:
                    time.sleep(0.3)
                continue

    print(f"  [warn] {round_no}회 실패 (모든 경로)", flush=True)
    return None


def estimate_latest() -> int:
    return (date.today() - START_DATE).days // 7 + 1


def find_latest() -> int:
    guess = estimate_latest()
    for r in range(guess + 2, max(1, guess - 10), -1):
        if fetch_draw(r, retries=1):
            return r
    raise RuntimeError("최신 회차를 찾지 못했습니다.")


def load_csv() -> dict[int, dict]:
    if not CSV_PATH.exists():
        return {}
    out = {}
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[int(row["round"])] = row
            except (KeyError, ValueError):
                continue
    return out


def save_csv(data: dict[int, dict]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["round", "date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"],
        )
        w.writeheader()
        for r in sorted(data):
            w.writerow(data[r])


def save_json(data: dict[int, dict]) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    draws = []
    for r in sorted(data):
        row = data[r]
        draws.append({
            "round_no": int(row["round"]),
            "date": row["date"],
            "numbers": [int(row[f"n{i}"]) for i in range(1, 7)],
            "bonus": int(row["bonus"]) if row["bonus"] else None,
        })
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(draws),
        "latest_round": draws[-1]["round_no"] if draws else 0,
        "draws": draws,
    }
    JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main() -> int:
    print("=" * 55)
    print(" 로또 데이터 수집 시작")
    print("=" * 55)

    existing = load_csv()
    print(f"기존: {len(existing)}회차" + (f" (최신 {max(existing)}회)" if existing else ""))

    try:
        latest = find_latest()
    except Exception as e:
        print(f"[오류] {e}")
        return 1
    print(f"최신: {latest}회")

    todo = [r for r in range(1, latest + 1) if r not in existing]
    if not todo:
        print("신규 회차 없음")
    else:
        print(f"수집 대상: {len(todo)}회차")
        added = 0
        for i, r in enumerate(todo, 1):
            d = fetch_draw(r)
            if not d:
                continue
            existing[d["round"]] = {
                "round": d["round"],
                "date": d["date"],
                "n1": d["nums"][0], "n2": d["nums"][1], "n3": d["nums"][2],
                "n4": d["nums"][3], "n5": d["nums"][4], "n6": d["nums"][5],
                "bonus": d["bonus"],
            }
            added += 1
            if i % 20 == 0 or i == len(todo):
                print(f"  [{i/len(todo)*100:5.1f}%] {r}회  (+{added})", flush=True)
            time.sleep(SLEEP_BETWEEN)
        print(f"추가: {added}회차")

    if not existing:
        print("[오류] 데이터 없음")
        return 1

    save_csv(existing)
    save_json(existing)
    print(f"저장: {CSV_PATH.relative_to(ROOT)}")
    print(f"저장: {JSON_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
