"""SafeRoute Flask app.   Run from the project root:   python -m backend.app"""
import json
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from backend import db, facilities, routing, scoring
from ml.common import HOTSPOT_PATH, ROOT

app = Flask(__name__,
            template_folder=str(ROOT / "frontend" / "templates"),
            static_folder=str(ROOT / "frontend" / "static"))
db.init_db()


def _float_args(*names):
    return [float(request.args[n]) for n in names]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/geocode")
def api_geocode():
    q = request.args.get("q", "").strip()
    if len(q) < 3:
        return jsonify(error="Type at least 3 characters."), 400
    try:
        return jsonify(results=routing.geocode(q))
    except Exception as exc:  # network / service problems
        return jsonify(error=f"Place search failed: {exc}"), 502


@app.get("/api/routes")
def api_routes():
    try:
        src = tuple(_float_args("src_lat", "src_lon"))
        dst = tuple(_float_args("dst_lat", "dst_lon"))
        hour = int(request.args.get("hour", datetime.now().hour))
        w_safety = float(request.args.get("w_safety", 0.5))
    except (KeyError, ValueError):
        return jsonify(error="Give src_lat, src_lon, dst_lat, dst_lon (numbers)."), 400

    try:
        routes = routing.get_routes(src, dst)
    except Exception as exc:
        return jsonify(error=f"Routing service failed: {exc}"), 502
    try:
        return jsonify(routes=scoring.score_routes(routes, hour, w_safety))
    except FileNotFoundError as exc:
        return jsonify(error=str(exc)), 503


@app.get("/api/hotspots")
def api_hotspots():
    if not HOTSPOT_PATH.exists():
        return jsonify(hotspots=[])
    return jsonify(hotspots=json.loads(HOTSPOT_PATH.read_text()))


@app.get("/api/facilities")
def api_facilities():
    try:
        lat, lon = _float_args("lat", "lon")
        radius = min(int(request.args.get("radius", 2000)), 5000)
    except (KeyError, ValueError):
        return jsonify(error="Give lat and lon."), 400
    try:
        return jsonify(facilities=facilities.nearby_facilities(lat, lon, radius))
    except Exception as exc:
        return jsonify(error=f"Facility lookup failed: {exc}"), 502


@app.post("/api/report")
def api_report():
    data = request.get_json(silent=True) or {}
    try:
        lat, lon = float(data["lat"]), float(data["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="lat and lon are required."), 400
    kind = data.get("incident_type")
    if kind not in db.INCIDENT_TYPES:
        return jsonify(error="Unknown incident type."), 400
    new_id = db.add_incident(lat, lon, kind, str(data.get("description", "")))
    return jsonify(id=new_id), 201


@app.get("/api/incidents")
def api_incidents():
    return jsonify(incidents=db.list_incidents())


if __name__ == "__main__":
    app.run(debug=True)
