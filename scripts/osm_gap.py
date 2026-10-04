"""Measure how much food and lodging information OpenStreetMap has for one region.

For a regency (default: Samosir, Indonesia) this script downloads every
restaurant/cafe/lodging that OpenStreetMap (OSM) lists, plus every village
point, and reports:
  - how many food and lodging places OSM lists, and how many have a phone
    number or opening hours;
  - for each village, how many of those places lie within --radius-km;
  - how many villages have none.

A village with zero places in OSM means OSM has no record, not that the village
has no food or lodging. That gap in public information is what this project
targets.

Usage:
    python scripts/osm_gap.py
    python scripts/osm_gap.py --area-name Samosir --admin-level 5 --radius-km 2

Writes data/real/osm/<area>/: raw.json (Overpass response), places.csv
(one row per village), summary.json. Data (c) OpenStreetMap contributors, ODbL.
"""

import argparse
import csv
import json
import math
import pathlib
import urllib.parse
import urllib.request

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
LODGING = {"hotel", "guest_house", "hostel", "motel", "apartment", "chalet", "camp_site"}
FOOD = {"restaurant", "cafe", "fast_food", "food_court"}
PLACE_TYPES = {"village", "hamlet", "town", "suburb", "neighbourhood"}
ROOT = pathlib.Path(__file__).resolve().parents[1]


def build_query(area_name: str, admin_level: int) -> str:
    return f"""
[out:json][timeout:180];
area["boundary"="administrative"]["admin_level"="{admin_level}"]["name"~"{area_name}"]->.r;
(
  nwr(area.r)["tourism"~"^({'|'.join(sorted(LODGING))})$"];
  nwr(area.r)["amenity"~"^({'|'.join(sorted(FOOD))})$"];
  node(area.r)["place"~"^({'|'.join(sorted(PLACE_TYPES))})$"];
);
out tags center;
"""


def fetch(query: str) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        OVERPASS_URL, data=data, headers={"User-Agent": "offgrid-tourism/0.1 (research)"}
    )
    with urllib.request.urlopen(req, timeout=200) as resp:
        return json.load(resp)


def coords(el: dict):
    if "lat" in el:
        return el["lat"], el["lon"]
    if "center" in el:
        return el["center"]["lat"], el["center"]["lon"]
    return None


def km(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--area-name", default="Samosir")
    ap.add_argument("--admin-level", type=int, default=5, help="5 = regency (kabupaten) in Indonesia")
    ap.add_argument("--radius-km", type=float, default=2.0)
    ap.add_argument("--hub-radius-km", type=float, default=3.0, help="radius around the busiest village")
    ap.add_argument("--cached", action="store_true", help="reuse raw.json instead of querying Overpass")
    args = ap.parse_args()

    out_dir = ROOT / "data" / "real" / "osm" / args.area_name.lower().replace(" ", "-")
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.cached:
        raw = json.loads((out_dir / "raw.json").read_text())
    else:
        raw = fetch(build_query(args.area_name, args.admin_level))
        (out_dir / "raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1))

    pois, places = [], []
    for el in raw["elements"]:
        tags, xy = el.get("tags", {}), coords(el)
        if xy is None:
            continue
        if tags.get("tourism") in LODGING or tags.get("amenity") in FOOD:
            kind = "lodging" if tags.get("tourism") in LODGING else "food"
            pois.append({"kind": kind, "xy": xy, "tags": tags})
        elif tags.get("place") in PLACE_TYPES:
            places.append({"name": tags.get("name", ""), "place": tags["place"], "xy": xy})

    rows = []
    for p in places:
        near = [q for q in pois if km(p["xy"], q["xy"]) <= args.radius_km]
        rows.append({
            "name": p["name"],
            "place": p["place"],
            "lat": round(p["xy"][0], 5),
            "lon": round(p["xy"][1], 5),
            "food_within_r": sum(q["kind"] == "food" for q in near),
            "lodging_within_r": sum(q["kind"] == "lodging" for q in near),
        })
    rows.sort(key=lambda r: -(r["food_within_r"] + r["lodging_within_r"]))
    with open(out_dir / "places.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["name"])
        w.writeheader()
        w.writerows(rows)

    def has(tag_keys):
        return sum(any(k in q["tags"] for k in tag_keys) for q in pois)

    villages = [r for r in rows if r["place"] == "village"]
    hub = rows[0] if rows else None
    near_hub = sum(km((hub["lat"], hub["lon"]), q["xy"]) <= args.hub_radius_km for q in pois) if hub else 0
    summary = {
        "area_name": args.area_name,
        "admin_level": args.admin_level,
        "radius_km": args.radius_km,
        "osm_snapshot": raw.get("osm3s", {}).get("timestamp_osm_base"),
        "food_places": sum(q["kind"] == "food" for q in pois),
        "lodging_places": sum(q["kind"] == "lodging" for q in pois),
        "places_with_phone": has(["phone", "contact:phone", "contact:whatsapp", "mobile"]),
        "places_with_opening_hours": has(["opening_hours"]),
        "place_points": len(rows),
        "village_points": len(villages),
        "villages_with_zero_food_and_lodging_within_r": sum(
            r["food_within_r"] + r["lodging_within_r"] == 0 for r in villages
        ),
        "busiest_village": hub["name"] if hub else None,
        "places_within_hub_radius": near_hub,
        "top_places": rows[:5],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
