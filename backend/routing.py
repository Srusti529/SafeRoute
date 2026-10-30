"""Route generation (OSRM) and place search (Nominatim). Both use OpenStreetMap data."""
import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "SafeRoute-MiniProject/1.0 (college project)"}


def get_routes(src, dst):
    """src, dst = (lat, lon). Returns up to ~3 alternative routes.

    Each route: {"coords": [[lon, lat], ...], "distance_m": float, "duration_s": float}
    """
    url = f"{OSRM_URL}/{src[1]},{src[0]};{dst[1]},{dst[0]}"
    params = {"alternatives": "true", "overview": "full",
              "geometries": "geojson", "steps": "false"}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise RuntimeError(data.get("message") or data.get("code") or "No route found")
    return [{
        "coords": r["geometry"]["coordinates"],
        "distance_m": r["distance"],
        "duration_s": r["duration"],
    } for r in data["routes"]]


def geocode(query, limit=5):
    """Turn a place name into coordinates."""
    resp = requests.get(NOMINATIM_URL, headers=HEADERS, timeout=15,
                        params={"q": query, "format": "json", "limit": limit})
    resp.raise_for_status()
    return [{"name": p["display_name"], "lat": float(p["lat"]), "lon": float(p["lon"])}
            for p in resp.json()]
