/* SafeRoute frontend: map, route search, layers, reporting, SOS. */
const COLORS = { Low: "#2a8a4f", Medium: "#c98a00", High: "#c63a2f" };
const INCIDENT_TYPES = ["Theft", "Harassment", "Assault", "Snatching", "Stalking",
                        "Poor lighting", "Other"];

const $ = (id) => document.getElementById(id);
const map = L.map("map").setView([16.18, 75.696], 13);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const layers = {
  routes: L.layerGroup().addTo(map),
  endpoints: L.layerGroup().addTo(map),
  facilities: L.layerGroup(),
  hotspots: L.layerGroup(),
  incidents: L.layerGroup(),
};
let currentRoutes = [];
let polylines = [];
let destination = null;
let reportMode = false;
let reportPoint = null;

/* ---------- helpers ---------- */
function setStatus(text, isError = false) {
  const el = $("status");
  el.textContent = text;
  el.classList.toggle("error", isError);
}

async function api(url, options) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// "16.18, 75.7" -> {lat, lon};  otherwise search by place name
async function resolvePlace(text) {
  const m = text.trim().match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);
  if (m) return { lat: parseFloat(m[1]), lon: parseFloat(m[2]) };
  const data = await api(`/api/geocode?q=${encodeURIComponent(text)}`);
  if (!data.results.length) throw new Error(`Could not find "${text}". Try a more specific name.`);
  return data.results[0];
}

function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}

/* ---------- routes ---------- */
function drawRoutes(selectedId) {
  layers.routes.clearLayers();
  polylines = currentRoutes.map((r) => {
    const selected = r.id === selectedId;
    const line = L.polyline(r.path, {
      color: COLORS[r.risk_level],
      weight: selected ? 8 : 5,
      opacity: selected ? 0.95 : 0.5,
      dashArray: selected ? null : "8 8",
    }).addTo(layers.routes);
    line.on("click", () => selectRoute(r.id));
    return line;
  });
  const chosen = polylines[selectedId];
  if (chosen) chosen.bringToFront();
}

function renderResults() {
  const box = $("results");
  box.replaceChildren();
  currentRoutes.forEach((r) => {
    const card = el("div", undefined, "route");
    card.dataset.level = r.risk_level;
    card.dataset.id = r.id;
    card.tabIndex = 0;
    card.append(el("h3", `Route ${r.id + 1}: ${r.risk_level} risk`));
    if (r.tags.length) card.append(el("div", r.tags.join(", "), "tags"));
    const stats = el("div", undefined, "stats");
    stats.append(
      el("span", `Safety ${r.safety_score}/100`, "score"),
      el("span", `${r.distance_km} km`),
      el("span", `${r.duration_min} min`)
    );
    card.append(stats);
    card.addEventListener("click", () => selectRoute(r.id));
    card.addEventListener("keydown", (e) => { if (e.key === "Enter") selectRoute(r.id); });
    box.append(card);
  });
}

function selectRoute(id) {
  document.querySelectorAll(".route").forEach((c) =>
    c.classList.toggle("selected", Number(c.dataset.id) === id));
  drawRoutes(id);
  if (polylines[id]) map.fitBounds(polylines[id].getBounds(), { padding: [30, 30] });
}

$("route-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("go").disabled = true;
  setStatus("Finding routes...");
  try {
    const [src, dst] = await Promise.all([resolvePlace($("src").value), resolvePlace($("dst").value)]);
    const hour = parseInt($("time").value.split(":")[0], 10);
    const params = new URLSearchParams({
      src_lat: src.lat, src_lon: src.lon, dst_lat: dst.lat, dst_lon: dst.lon,
      hour, w_safety: $("w").value / 100,
    });
    const data = await api(`/api/routes?${params}`);
    currentRoutes = data.routes;
    destination = dst;

    layers.endpoints.clearLayers();
    L.marker([src.lat, src.lon]).bindPopup("Start").addTo(layers.endpoints);
    L.marker([dst.lat, dst.lon]).bindPopup("Destination").addTo(layers.endpoints);

    renderResults();
    const best = currentRoutes.find((r) => r.tags.includes("Recommended")) || currentRoutes[0];
    selectRoute(best.id);
    setStatus(`${currentRoutes.length} route(s) found. Recommended: Route ${best.id + 1}.`);
    if ($("t-fac").checked) loadFacilities();
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    $("go").disabled = false;
  }
});

$("use-loc").addEventListener("click", () => {
  if (!navigator.geolocation) return setStatus("Location is not supported on this device.", true);
  navigator.geolocation.getCurrentPosition(
    (p) => { $("src").value = `${p.coords.latitude.toFixed(5)}, ${p.coords.longitude.toFixed(5)}`; },
    () => setStatus("Could not get your location. Allow location access and try again.", true)
  );
});

/* ---------- map layers ---------- */
async function loadFacilities() {
  layers.facilities.clearLayers();
  if (!destination) return setStatus("Find a route first, then turn this layer on.");
  try {
    const data = await api(`/api/facilities?lat=${destination.lat}&lon=${destination.lon}&radius=5000`);
    data.facilities.forEach((f) => {
      const police = f.type === "police";
      L.circleMarker([f.lat, f.lon], {
        radius: 8, color: "#fff", weight: 2, fillOpacity: 1,
        fillColor: police ? "#1d5fd1" : "#c63a2f",
      }).bindPopup(`${police ? "Police station" : "Hospital"}: ${f.name}`).addTo(layers.facilities);
    });
    setStatus(`${data.facilities.length} police stations/hospitals within 5 km of the destination.`);
  } catch (err) { setStatus(err.message, true); }
}

async function loadHotspots() {
  layers.hotspots.clearLayers();
  try {
    const data = await api("/api/hotspots");
    data.hotspots.forEach((h) => {
      L.circle([h.lat, h.lon], {
        radius: Math.max(h.radius_m, 80), color: COLORS[h.level], weight: 1, fillOpacity: 0.25,
      }).bindPopup(`${h.level} risk hotspot (${h.incidents} past incidents)`).addTo(layers.hotspots);
    });
  } catch (err) { setStatus(err.message, true); }
}

async function loadIncidents() {
  layers.incidents.clearLayers();
  try {
    const data = await api("/api/incidents");
    data.incidents.forEach((i) => {
      L.circleMarker([i.lat, i.lon], { radius: 6, color: "#6a1b9a", fillOpacity: 0.9 })
        .bindPopup(`${i.incident_type}: ${i.description || "no details"}`).addTo(layers.incidents);
    });
  } catch (err) { setStatus(err.message, true); }
}

function bindToggle(id, layer, loader) {
  $(id).addEventListener("change", (e) => {
    if (e.target.checked) { map.addLayer(layer); loader(); } else { map.removeLayer(layer); }
  });
}
bindToggle("t-fac", layers.facilities, loadFacilities);
bindToggle("t-hot", layers.hotspots, loadHotspots);
bindToggle("t-inc", layers.incidents, loadIncidents);

/* ---------- incident reporting ---------- */
INCIDENT_TYPES.forEach((t) => $("r-type").append(new Option(t, t)));

$("report-btn").addEventListener("click", () => {
  reportMode = !reportMode;
  $("report-btn").textContent = reportMode ? "Cancel reporting" : "Report an incident";
  setStatus(reportMode ? "Tap the map where it happened." : "");
});

map.on("click", (e) => {
  if (!reportMode) return;
  reportPoint = e.latlng;
  $("report-where").textContent = `Location: ${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`;
  $("report-dialog").showModal();
});

$("r-cancel").addEventListener("click", () => $("report-dialog").close());
$("report-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: reportPoint.lat, lon: reportPoint.lng,
        incident_type: $("r-type").value, description: $("r-desc").value,
      }),
    });
    $("report-dialog").close();
    $("r-desc").value = "";
    reportMode = false;
    $("report-btn").textContent = "Report an incident";
    setStatus("Report saved. Thank you.");
    if ($("t-inc").checked) loadIncidents();
  } catch (err) { setStatus(err.message, true); }
});

/* ---------- SOS ---------- */
$("sos-btn").addEventListener("click", () => { $("sos-msg").textContent = ""; $("sos-dialog").showModal(); });
$("sos-close").addEventListener("click", () => $("sos-dialog").close());
$("share-loc").addEventListener("click", () => {
  if (!navigator.geolocation) { $("sos-msg").textContent = "Location is not supported here."; return; }
  navigator.geolocation.getCurrentPosition(async (p) => {
    const link = `https://maps.google.com/?q=${p.coords.latitude},${p.coords.longitude}`;
    const text = `I need help. My location: ${link}`;
    try {
      if (navigator.share) await navigator.share({ text });
      else { await navigator.clipboard.writeText(text); $("sos-msg").textContent = "Location link copied. Paste it in a message."; }
    } catch { $("sos-msg").textContent = text; }
  }, () => { $("sos-msg").textContent = "Could not get your location."; });
});

/* ---------- defaults ---------- */
const now = new Date();
$("time").value = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
