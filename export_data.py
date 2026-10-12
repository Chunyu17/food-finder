import json

CATEGORY_MAP = {
    "brunch_restaurant": "早午餐", "breakfast_restaurant": "早午餐",
    "bistro": "餐酒館", "bar": "餐酒館", "pub": "餐酒館", "wine_bar": "餐酒館",
    "cafe": "咖啡廳", "coffee_shop": "咖啡廳", "tea_house": "咖啡廳",
    "dessert_shop": "甜點", "pastry_shop": "甜點", "ice_cream_shop": "甜點",
    "chinese_restaurant": "台式/中式", "taiwanese_restaurant": "台式/中式",
    "hot_pot_restaurant": "火鍋", "barbecue_restaurant": "燒烤",
    "japanese_restaurant": "日式", "ramen_restaurant": "日式", "sushi_restaurant": "日式",
    "korean_restaurant": "韓式",
    "thai_restaurant": "泰式", "vietnamese_restaurant": "東南亞",
    "italian_restaurant": "義式", "french_restaurant": "歐陸",
    "mediterranean_restaurant": "歐陸", "european_restaurant": "歐陸", "spanish_restaurant": "歐陸",
    "american_restaurant": "美式", "indian_restaurant": "印度料理",
    "vegetarian_restaurant": "蔬食",
}


def categorize(p):
    return CATEGORY_MAP.get(p.get("type"), "其他")


with open("snapshot.json", encoding="utf-8") as f:
    places = list(json.load(f)["places"].values())

for p in places:
    p["category"] = categorize(p)


def has_details(p):
    return "name" in p and p.get("name")


new_radar = [p for p in places if p.get("candidate")]
new_radar.sort(key=lambda p: p.get("first_seen", ""), reverse=True)

quick_date = [
    p for p in places
    if has_details(p)
    and p.get("is_food")
    and p.get("status") == "OPERATIONAL"
    and (p.get("rating") or 0) >= 4.3
]
quick_date.sort(key=lambda p: (p.get("open_now") is True, p.get("rating") or 0), reverse=True)
quick_date = quick_date[:150]

data = {"new_radar": new_radar, "quick_date": quick_date}

with open("data.js", "w", encoding="utf-8") as f:
    f.write("const RESTAURANT_DATA = ")
    json.dump(data, f, ensure_ascii=False)
    f.write(";\n")

print(f"新開幕雷達：{len(new_radar)} 間")
print(f"快速約會候選：{len(quick_date)} 間")
print("已產生 data.js")