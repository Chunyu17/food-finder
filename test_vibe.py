import os
import requests

STATIONS = {
    "科技大樓站": (25.0266, 121.5436),
    "大安站": (25.0330, 121.5436),
    "公館站": (25.0147, 121.5345),
}

KEYWORDS = [
    "約會餐廳",
    "情侶約會 餐廳",
    "網美咖啡廳",
    "打卡甜點",
    "適合聊天 咖啡廳",
    "氣氛佳 餐廳",
]

RADIUS_METERS = 1600  # 約步行 20 分鐘


def read_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        with open("api_key.txt", encoding="utf-8") as f:
            key = f.read().strip()
    return key


def search(api_key, query, lat, lng):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.primaryType",
    }
    body = {
        "textQuery": query,
        "languageCode": "zh-TW",
        "pageSize": 8,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": RADIUS_METERS,
            }
        },
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        print("查詢失敗：", query, response.status_code, response.text[:200])
        return []
    return response.json().get("places", [])


def main():
    api_key = read_api_key()
    for station, (lat, lng) in STATIONS.items():
        print(f"\n========== {station}（半徑 {RADIUS_METERS} 公尺）==========")
        for keyword in KEYWORDS:
            print(f"\n--- 關鍵字：{keyword} ---")
            for p in search(api_key, keyword, lat, lng):
                name = p["displayName"]["text"]
                print(name, "| 評分", p.get("rating"), "|", p.get("userRatingCount"), "則評論 |", p.get("primaryType"))


main()