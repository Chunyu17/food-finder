import json
import time

import requests


def read_api_key():
    import os
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        with open("api_key.txt", encoding="utf-8") as f:
            key = f.read().strip()
    return key


STATIONS = [
    "淡水", "紅樹林", "竹圍", "關渡", "忠義", "復興崗", "北投", "新北投", "奇岩", "唭哩岸",
    "石牌", "明德", "芝山", "士林", "劍潭", "圓山", "民權西路", "雙連", "中山", "台北車站",
    "台大醫院", "中正紀念堂", "東門", "大安森林公園", "大安", "信義安和", "台北101/世貿", "象山",
    "松山", "南京三民", "台北小巨蛋", "南京復興", "中山國小", "松江南京", "北門", "西門", "小南門",
    "古亭", "台電大樓", "公館", "萬隆", "景美", "大坪林", "七張", "新店區公所", "新店",
    "南勢角", "景安", "永安市場", "頂溪", "大橋頭", "台北橋", "菜寮", "三重", "先嗇宮",
    "頭前庄", "新莊", "輔大", "丹鳳", "迴龍", "三重國小", "三和國中", "徐匯中學",
    "泰山", "泰山貴和", "體育大學", "新北產業園區",
    "頂埔", "永寧", "土城", "海山", "亞東醫院", "府中", "板橋", "新埔", "江子翠", "龍山寺",
    "善導寺", "忠孝新生", "忠孝復興", "忠孝敦化", "國父紀念館", "市政府", "永春", "後山埤",
    "昆陽", "南港", "南港展覽館",
    "動物園", "木柵", "萬芳社區", "萬芳醫院", "辛亥", "麟光", "六張犁", "科技大樓",
    "中山國中", "松山機場", "大直", "劍南路", "西湖", "港墘", "文德", "內湖", "大湖公園",
    "葫洲", "東湖", "南港軟體園區",
    "十四張", "秀朗橋", "景平", "中和", "橋和", "中原", "板新", "新埔民生",
]


def main():
    api_key = read_api_key()
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.location",
    }

    stations = {}
    failed = []
    for name in STATIONS:
        body = {"textQuery": f"台北捷運 {name}站", "languageCode": "zh-TW"}
        response = requests.post(url, headers=headers, json=body)
        if response.status_code != 200:
            failed.append(name)
            continue
        places = response.json().get("places", [])
        if not places:
            failed.append(name)
            continue
        loc = places[0]["location"]
        stations[name] = {"lat": loc["latitude"], "lng": loc["longitude"]}
        print(f"{name}站：{loc['latitude']:.5f}, {loc['longitude']:.5f}")
        time.sleep(0.05)

    with open("stations.json", "w", encoding="utf-8") as f:
        json.dump(stations, f, ensure_ascii=False, indent=2)

    print(f"\n完成，共取得 {len(stations)} 站座標")
    if failed:
        print("這些站查詢失敗，請人工確認：", "、".join(failed))


main()