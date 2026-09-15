#!/usr/bin/env python3
"""
로또 데이터 수집 (smok95/lotto API) → CSV + JSON 생성
GitHub Actions에서 실행됨.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests 설치 중...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    import requests

API_ALL = "https://smok95.github.io/lotto/results/all.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "lotto_history.csv"
JSON_PATH = ROOT / "docs" / "data" / "lotto_history.json"


def fetch_all(retries: int = 3) -> list:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(API_ALL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                raise RuntimeError("빈 응답")
            return data
        except Exception as e:
            if attempt == retries:
                raise
            print(f"  [warn] 시도 {attempt}/{retries} 실패: {e}", flush=True)
            time.sleep(2 * attempt)
    return []


def load_csv() -> dict:
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


def save_csv(data: dict) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["round", "date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"],
        )
        w.writeheader()
        for r in sorted(data):
            w.writerow(data[r])


def save_json(data: dict) -> None:
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
    print(" 로또 데이터 수집 시작 (smok95 API)")
    print("=" * 55)

    existing = load_csv()
    print(f"기존: {len(existing)}회차")

    try:
        print("all.json 다운로드 중...")
        all_draws = fetch_all()
    except Exception as e:
        print(f"[오류] API 요청 실패: {e}")
        return 1

    print(f"서버: {len(all_draws)}회차")

    added = 0
    for item in all_draws:
        r = int(item["draw_no"])
        if r in existing:
            continue
        nums = item["numbers"]
        existing[r] = {
            "round": r,
            "date": item.get("date", "")[:10],
            "n1": nums[0], "n2": nums[1], "n3": nums[2],
            "n4": nums[3], "n5": nums[4], "n6": nums[5],
            "bonus": item.get("bonus_no", ""),
        }
        added += 1

    if not existing:
        print("[오류] 데이터 없음")
        return 1

    print(f"추가: {added}회차  (총 {len(existing)}회차)")

    save_csv(existing)
    save_json(existing)
    print(f"저장: data/lotto_history.csv")
    print(f"저장: docs/data/lotto_history.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())