import json
import sys

import requests

from scan import get_details, read_api_key, save_snapshot, load_snapshot

BATCH_SIZE = 600  # 每次執行最多補幾間（費用保險，可自行調整）


def main():
    api_key = read_api_key()
    snapshot = load_snapshot()
    known = snapshot["places"]

    # 還沒有詳細資料的店（只有基準紀錄、沒查過 name 的）
    todo = [pid for pid, info in known.items() if info.get("baseline") and "name" not in info]
    print(f"還有 {len(todo)} 間店尚未補齊詳細資料")

    if not todo:
        print("全部補齊完成！")
        return

    batch = todo[:BATCH_SIZE]
    print(f"本次處理 {len(batch)} 間...")

    done = 0
    for place_id in batch:
        info = get_details(api_key, place_id)
        if info is None:
            continue
        info["baseline"] = True       # 維持基準身份，不算新店
        info["candidate"] = False
        known[place_id] = info
        done += 1
        if done % 20 == 0:
            save_snapshot(snapshot)   # 每 20 間存一次，避免中斷白做
            print(f"  已完成 {done} / {len(batch)}")

    save_snapshot(snapshot)
    remaining = len(todo) - done
    print(f"本次補齊 {done} 間，剩餘 {remaining} 間，之後重新執行同一個指令即可繼續。")


main()