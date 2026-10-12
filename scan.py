import json
import os
import sys
import time
from datetime import date

import requests

# ---------- 設定區 ----------
STATIONS_FILE = "stations.json"
RADIUS_METERS = 1600  # 約步行 20 分鐘
KEYWORDS = [
    "約會餐廳", "情侶約會 餐廳", "網美咖啡廳", "打卡甜點",
    "適合聊天 咖啡廳", "氣氛佳 餐廳",
]
MAX_PAGES = 2               # 每組關鍵字最多翻幾頁（每頁 20 間）
MAX_DETAILS = 150           # 每次最多查幾間新店的詳細資料（費用保險）
MAX_REVIEWS_FOR_NEW = 100   # 評論數超過這個數字，就不當成新店候選
SNAPSHOT_FILE = "snapshot.json"
PROGRESS_FILE = "scan_progress.json"

FOOD_TYPES = {
    "restaurant", "cafe", "coffee_shop", "bar", "pub", "bakery",
    "meal_takeaway", "meal_delivery", "ice_cream_shop", "dessert_shop",
    "tea_house", "food_court", "sandwich_shop", "juice_shop", "bistro",
    "pastry_shop", "brunch_restaurant",
}
EXCLUDE_KEYWORDS = ["食品有限公司", "團膳", "企業社", "股份有限公司", "有限公司", "批發", "工廠"]
# ----------------------------


def is_food(types):
    return any(t in FOOD_TYPES or t.endswith("_restaurant") for t in types)


def read_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        with open("api_key.txt", encoding="utf-8") as f:
            key = f.read().strip()
    return key


def load_stations():
    with open(STATIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def request_with_retry(method, url, **kwargs):
    """遇到連線問題時自動重試，最多 4 次，間隔越來越長。"""
    last_error = None
    for attempt in range(4):
        try:
            return requests.request(method, url, timeout=20, **kwargs)
        except requests.exceptions.RequestException as e:
            last_error = e
            wait = 3 * (attempt + 1)
            print(f"  連線問題，{wait} 秒後重試（第 {attempt + 1} 次）：{e}")
            time.sleep(wait)
    raise last_error


def search_ids(api_key, query, lat, lng):
    """階段一：只要店家代碼，不要評分等詳細資料。"""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,nextPageToken",
    }
    ids = []
    page_token = None
    for _ in range(MAX_PAGES):
        body = {
            "textQuery": query,
            "languageCode": "zh-TW",
            "pageSize": 20,
            "locationBias": {
                "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": RADIUS_METERS}
            },
        }
        if page_token:
            body["pageToken"] = page_token
        response = request_with_retry("POST", url, headers=headers, json=body)
        if response.status_code != 200:
            print("查詢失敗：", query, response.status_code, response.text[:200])
            break
        data = response.json()
        ids += [p["id"] for p in data.get("places", [])]
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return ids


def get_details(api_key, place_id):
    """查店名、評分、評論數、類型、是否營業中、價位、照片。"""
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "displayName,formattedAddress,rating,userRatingCount,businessStatus,"
            "primaryType,types,currentOpeningHours.openNow,priceLevel,photos"
        ),
    }
    response = request_with_retry("GET", url, headers=headers, params={"languageCode": "zh-TW"})
    if response.status_code != 200:
        print("詳細資料查詢失敗：", place_id, response.status_code)
        return None
    p = response.json()
    photos = p.get("photos", [])
    return {
        "name": p.get("displayName", {}).get("text"),
        "address": p.get("formattedAddress"),
        "rating": p.get("rating"),
        "reviews": p.get("userRatingCount"),
        "status": p.get("businessStatus"),
        "type": p.get("primaryType"),
        "is_food": is_food(p.get("types", [])),
        "open_now": p.get("currentOpeningHours", {}).get("openNow"),
        "price_level": p.get("priceLevel"),
        "photo_name": photos[0]["name"] if photos else None,
    }


def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"places": {}}


def save_snapshot(snapshot):
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        print(f"發現上次中斷的進度：已完成 {len(data['done_stations'])} 站，從這裡繼續。")
        station_map = {pid: set(names) for pid, names in data.get("station_map", {}).items()}
        return set(data["done_stations"]), set(data["found_ids"]), station_map
    return set(), set(), {}


def save_progress(done_stations, found, station_map):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "done_stations": list(done_stations),
            "found_ids": list(found),
            "station_map": {pid: list(names) for pid, names in station_map.items()},
        }, f, ensure_ascii=False)


def main():
    baseline_mode = "--baseline" in sys.argv
    api_key = read_api_key()
    stations = load_stations()
    snapshot = load_snapshot()
    known = snapshot["places"]
    today = date.today().isoformat()

    # ===== 階段一：以每個捷運站為中心搜尋，只收集店家代碼（可續跑）=====
    done_stations, found, station_map = load_progress()
    for name, loc in stations.items():
        if name in done_stations:
            continue
        station_ids = set()
        for keyword in KEYWORDS:
            station_ids.update(search_ids(api_key, keyword, loc["lat"], loc["lng"]))
        found.update(station_ids)
        for pid in station_ids:
            station_map.setdefault(pid, set()).add(name)
        done_stations.add(name)
        save_progress(done_stations, found, station_map)
        print(f"{name}站 掃描完成，累計 {len(found)} 個店家代碼")

    # 把這次掃到的站名，補進已經存在的店家資料裡（新舊資料都適用）
    for pid, names in station_map.items():
        if pid in known:
            existing = set(known[pid].get("stations", []))
            known[pid]["stations"] = sorted(existing | names)

    new_ids = [i for i in found if i not in known]
    print(f"\n共找到 {len(found)} 個店家代碼，其中 {len(new_ids)} 個是快照裡沒有的")

    # ===== 基準模式：只記錄代碼，不查詳細資料 =====
    if baseline_mode:
        for i in new_ids:
            known[i] = {"first_seen": today, "baseline": True, "stations": sorted(station_map.get(i, []))}
        save_snapshot(snapshot)
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        print(f"基準模式：已記錄 {len(new_ids)} 個代碼作為基準。")
        return

    # ===== 階段二：只查新店的詳細資料 =====
    to_fetch = new_ids[:MAX_DETAILS]
    if len(new_ids) > MAX_DETAILS:
        print(f"新店數超過上限，本次只查前 {MAX_DETAILS} 間，其餘留到下次。")

    still_watching = 0
    skipped = 0
    for place_id in to_fetch:
        info = get_details(api_key, place_id)
        if info is None:
            continue
        info["first_seen"] = today
        info["baseline"] = False
        info["seen_count"] = 1
        info["stations"] = sorted(station_map.get(place_id, []))
        name = info["name"] or ""
        is_excluded = any(kw in name for kw in EXCLUDE_KEYWORDS)
        qualifies = (
            info["is_food"]
            and info["status"] == "OPERATIONAL"
            and (info["reviews"] or 0) <= MAX_REVIEWS_FOR_NEW
            and not is_excluded
        )
        info["candidate"] = False
        known[place_id] = info
        if qualifies:
            still_watching += 1
        else:
            skipped += 1

    for place_id in found:
        info = known.get(place_id)
        if info is None or info.get("baseline"):
            continue
        if place_id in to_fetch:
            continue
        if info.get("seen_count", 1) == 1:
            info["seen_count"] = 2

    for info in known.values():
        if info.get("baseline"):
            continue
        name = info.get("name") or ""
        is_excluded = any(kw in name for kw in EXCLUDE_KEYWORDS)
        qualifies = (
            info.get("is_food")
            and info.get("status") == "OPERATIONAL"
            and (info.get("reviews") or 0) <= MAX_REVIEWS_FOR_NEW
            and not is_excluded
        )
        info["candidate"] = qualifies and info.get("seen_count", 1) >= 2

    save_snapshot(snapshot)
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    candidates = [p for p in known.values() if p.get("candidate")]
    candidates.sort(key=lambda p: p["reviews"] or 0)
    print(f"\n新店候選 {len(candidates)} 間（{still_watching} 間剛發現、進入觀察中，{skipped} 間因非餐飲、已歇業或評論過多而略過）：")
    for info in candidates:
        print("-", info["name"], "| 評分", info["rating"], "|", info["reviews"], "則評論 |", info["type"])


main()