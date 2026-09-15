#!/usr/bin/env python3
"""연금복권720+ 데이터 수집 → JSON 생성"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    import requests

BASE = "https://lottoclip.github.io/lottoclip-api/pension"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "docs" / "data" / "pension_history.json"


def fetch_json(url: str, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries:
                raise
            print(f"  [warn] 재시도 {attempt}/{retries}: {e}", flush=True)
            time.sleep(2 * attempt)


def main() -> int:
    print("=" * 55)
    print(" 연금복권720+ 데이터 수집 시작")
    print("=" * 55)

    try:
        print("index.json 다운로드 중...")
        index = fetch_json(f"{BASE}/index.json")
    except Exception as e:
        print(f"[오류] 인덱스 로드 실패: {e}")
        return 1

    draws = index.get("draws", [])
    print(f"전체 회차: {len(draws)}")

    existing = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
            for d in old.get("draws", []):
                existing[d["draw_no"]] = d
        except Exception:
            pass

    new_draws = []
    for i, item in enumerate(draws):
        draw_no = item["draw_no"]
        if draw_no in existing:
            new_draws.append(existing[draw_no])
            continue

        try:
            detail = fetch_json(f"{BASE}/draws/pension_{draw_no}.json")
            new_draws.append(detail)
        except Exception as e:
            print(f"  [warn] {draw_no}회 실패: {e}")
            continue

        if (i + 1) % 30 == 0:
            print(f"  [{i+1}/{len(draws)}] {draw_no}회 수집 완료", flush=True)
        time.sleep(0.2)

    new_draws.sort(key=lambda x: x["draw_no"])

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(new_draws),
        "latest_round": new_draws[-1]["draw_no"] if new_draws else 0,
        "draws": new_draws,
    }

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"저장: {JSON_PATH.relative_to(ROOT)}")
    print(f"총 {len(new_draws)}회차")
    return 0


if __name__ == "__main__":
    sys.exit(main())