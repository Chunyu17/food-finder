import json

with open("snapshot.json", encoding="utf-8") as f:
    places = json.load(f)["places"]

print("總共", len(places), "間店")

buckets = {"0-20 則": 0, "21-100 則": 0, "101-500 則": 0, "500 則以上": 0}
for p in places.values():
    n = p.get("reviews") or 0
    if n <= 20:
        buckets["0-20 則"] += 1
    elif n <= 100:
        buckets["21-100 則"] += 1
    elif n <= 500:
        buckets["101-500 則"] += 1
    else:
        buckets["500 則以上"] += 1

for name, count in buckets.items():
    print(name, ":", count, "間")

print()
print("評論少但評分高的店（可能是較新的店）：")
candidates = [
    p for p in places.values()
    if p.get("rating") and p["rating"] >= 4.3
    and (p.get("reviews") or 0) <= 100
    and p.get("status") == "OPERATIONAL"
]
candidates.sort(key=lambda p: p["reviews"] or 0)
for p in candidates[:15]:
    print("-", p["name"], "| 評分", p["rating"], "|", p["reviews"], "則評論 |", p["address"])