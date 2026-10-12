import os
import requests

api_key = os.environ.get("GOOGLE_API_KEY", "")
if not api_key:
    with open("api_key.txt", encoding="utf-8") as f:
        api_key = f.read().strip()
print("已讀到金鑰，長度：", len(api_key))

url = "https://places.googleapis.com/v1/places:searchText"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount",
}
body = {
    "textQuery": "台北市大安區 餐廳",
    "languageCode": "zh-TW",
    "maxResultCount": 5,
}

response = requests.post(url, headers=headers, json=body)
print("狀態碼：", response.status_code)

data = response.json()
if response.status_code == 200:
    for p in data.get("places", []):
        name = p["displayName"]["text"]
        print(name, "| 評分", p.get("rating"), "|", p.get("userRatingCount"), "則評論 |", p.get("formattedAddress"))
else:
    print(data)