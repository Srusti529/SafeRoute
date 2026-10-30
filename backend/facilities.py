"""Nearby police stations and hospitals.

Order of use:
  1. data/facilities.csv  - YOUR own list. Instant, works offline, always reliable.
  2. OpenStreetMap (Overpass) - used only when the CSV has nothing near the destination.
     Successful answers are remembered in data/facilities_cache.json.
"""
import csv
import json
import math

import requests

from ml.common import ROOT

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {"User-Agent": "SafeRoute-MiniProject/1.0 (college project)"}
LOCAL_FILE = ROOT / "data" / "facilities.csv"        # columns: name,type,lat,lon
CACHE_FILE = ROOT / "data" / "facilities_cache.json"
_memory = {}


def _distance_m(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p) / 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2)
    return 12_742_000 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------- your own list
def _local_places(lat, lon, radius_m):
    places = []
    try:
        with open(LOCAL_FILE, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return places
    for row in rows:
        try:
            name = (row.get("name") or "").strip()
            kind = (row.get("type") or "").strip().lower()
            p_lat, p_lon = float(row["lat"]), float(row["lon"])
        except (KeyError, TypeError, ValueError):
            continue  # skip incomplete or example rows
        if not name or name.startswith("#") or kind not in ("police", "hospital"):
            continue
        if _distance_m(lat, lon, p_lat, p_lon) <= radius_m:
            places.append({"type": kind, "name": name, "lat": p_lat, "lon": p_lon})
    return places


# ------------------------------------------------------------------- Overpass
def _key(lat, lon, radius_m):
    return f"{round(lat, 3)},{round(lon, 3)},{int(radius_m)}"


def _load_cache():
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(key, places):
    cache = _load_cache()
    cache[key] = places
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass


def _query(lat, lon, radius_m):
    r = int(radius_m)
    return f"""
    [out:json][timeout:18];
    (
      nw["amenity"="police"](around:{r},{lat},{lon});
      nw["amenity"="hospital"](around:{r},{lat},{lon});
    );
    out center 40;
    """


def _parse(elements):
    places = []
    for el in elements:
        centre = el if "lat" in el else el.get("center", {})
        if "lat" not in centre:
            continue
        tags = el.get("tags", {})
        places.append({"type": tags.get("amenity"),
                       "name": tags.get("name", "Unnamed " + str(tags.get("amenity"))),
                       "lat": centre["lat"], "lon": centre["lon"]})
    return places


def nearby_facilities(lat, lon, radius_m=2000):
    local = _local_places(lat, lon, radius_m)
    if local:
        return local

    key = _key(lat, lon, radius_m)
    if key in _memory:
        return _memory[key]

    cached = _load_cache().get(key)
    for url in OVERPASS_URLS:
        try:
            resp = requests.post(url, data={"data": _query(lat, lon, radius_m)},
                                 headers=HEADERS, timeout=25)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            continue
        # A busy server may reply "OK" with an empty list plus a "remark" about a timeout.
        if not data.get("elements") and "remark" in data:
            continue
        places = _parse(data.get("elements", []))
        _memory[key] = places
        _save_cache(key, places)
        return places

    if cached is not None:
        _memory[key] = cached
        return cached
    raise RuntimeError("The online map data service is busy. Add the places to "
                       "data/facilities.csv, or try again in a minute.")
