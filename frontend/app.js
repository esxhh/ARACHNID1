const state = { vessels: [], selectedVessel: null, vesselLayer: null, trackLayer: null, baseLayer: null, satelliteLayer: null, globeMode: false };
let liveSocket;
const home = [25.18, 55.46];
const map = L.map("map", { zoomControl: false, attributionControl: false }).setView(home, 9);
L.control.zoom({ position: "bottomright" }).addTo(map);
state.baseLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);
state.satelliteLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 18, attribution: "&copy; Esri" });
state.vesselLayer = L.layerGroup().addTo(map); state.trackLayer = L.layerGroup().addTo(map);
const vesselIcon = L.divIcon({ className: "", html: '<div class="vessel-marker"></div>', iconSize: [10, 10], iconAnchor: [5, 5] });

async function request(path, options = {}) { const response = await fetch(path, options); if (!response.ok) throw new Error(`${path} returned ${response.status}`); return response.json(); }
async function loadData() {
  const [status, world, monitor] = await Promise.all([request("/api/status"), request("/api/vessels/world"), request("/api/monitor/status")]);
  const vessels = world.vessels;
  state.vessels = vessels; document.querySelector("#service-status").textContent = status.services.django_control_plane === "ok" ? "Control plane connected" : "Control plane unavailable";
  document.querySelector("#coverage-status").textContent = world.coverage === "global" ? "GLOBAL AIS" : "DEMO REGION / PROVIDER READY";
  document.querySelector(".pipeline-status").innerHTML = `<i></i> AIS streaming / Sentinel ${monitor.configured ? "monitoring" : "awaiting credentials"} <em id="last-sync">--</em>`;
  renderMetrics(); renderFleet(); renderVessels();
  const now = new Date(); document.querySelector("#updated-at").textContent = `AIS synced ${now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`; document.querySelector("#last-sync").textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
function applyLiveVessels(vessels) {
  state.vessels = vessels; renderMetrics(); renderFleet(); renderVessels();
  if (state.selectedVessel) {
    const updated = state.vessels.find((vessel) => vessel.mmsi === state.selectedVessel.mmsi);
    if (updated) { state.selectedVessel = updated; renderDetail(updated); }
  }
  const now = new Date(); document.querySelector("#updated-at").textContent = `AIS stream ${now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`; document.querySelector("#last-sync").textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
function connectLiveFeed() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  liveSocket = new WebSocket(`${protocol}://${window.location.host}/ws/live`);
  liveSocket.onopen = () => { document.querySelector("#service-status").textContent = "AIS WebSocket connected"; };
  liveSocket.onmessage = (event) => { const message = JSON.parse(event.data); if (message.type === "vessel_positions" || message.type === "ais_ingest") applyLiveVessels(message.vessels); };
  liveSocket.onerror = () => liveSocket.close();
  liveSocket.onclose = () => { document.querySelector("#service-status").textContent = "AIS reconnecting"; setTimeout(connectLiveFeed, 3000); };
}
function renderMetrics() {
  const underway = state.vessels.filter((vessel) => vessel.status === "Underway").length;
  document.querySelector("#vessel-count").textContent = state.vessels.length;
  document.querySelector("#fleet-count").textContent = String(state.vessels.length).padStart(2, "0");
  document.querySelector("#underway-count").textContent = underway;
  document.querySelector("#anchored-count").textContent = state.vessels.length - underway;
}
function renderVessels() {
  state.vesselLayer.clearLayers(); state.trackLayer.clearLayers();
  state.vessels.forEach((vessel, index) => {
    const marker = L.marker([vessel.lat, vessel.lon], { icon: vesselIcon }).on("click", () => selectVessel(vessel.mmsi)).bindTooltip(`<strong>${vessel.name}</strong><br>${vessel.type} / ${vessel.speed} kn`, { direction: "top", offset: [0, -6] });
    state.vesselLayer.addLayer(marker);
    const track = [[vessel.lat - .08 - index * .004, vessel.lon - .04], [vessel.lat, vessel.lon], [vessel.lat + .05, vessel.lon + .07]];
    state.trackLayer.addLayer(L.polyline(track, { color: "#78a9c3", weight: 1, opacity: .45, dashArray: "3 8" }));
  });
}
function renderFleet() {
  const list = document.querySelector("#fleet-list"); list.innerHTML = "";
  state.vessels.forEach((vessel) => {
    const item = document.createElement("button"); item.className = "incident-card vessel-card"; item.dataset.mmsi = vessel.mmsi;
    item.innerHTML = `<div class="incident-card-top"><strong>${vessel.name}</strong><span class="incident-confidence">${vessel.speed} kn</span></div><div class="incident-card-bottom"><small>${vessel.type} / ${vessel.flag}</small><small><i class="status-mini"></i>${vessel.status}</small></div>`;
    item.addEventListener("click", () => selectVessel(vessel.mmsi)); list.appendChild(item);
  });
}
function renderSearchResults(query) {
  const results = document.querySelector("#search-results");
  const matches = state.vessels.filter((vessel) => `${vessel.name} ${vessel.mmsi} ${vessel.flag}`.toLowerCase().includes(query.toLowerCase())).slice(0, 5);
  results.innerHTML = matches.map((vessel) => `<button data-mmsi="${vessel.mmsi}"><strong>${vessel.name}</strong><small>${vessel.mmsi} / ${vessel.flag}</small></button>`).join("");
  results.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => { selectVessel(button.dataset.mmsi); results.innerHTML = ""; document.querySelector("#vessel-search").value = ""; }));
}
function selectVessel(mmsi) {
  const vessel = state.vessels.find((item) => item.mmsi === mmsi); if (!vessel) return; state.selectedVessel = vessel;
  document.querySelectorAll(".vessel-card").forEach((item) => item.classList.toggle("selected", item.dataset.mmsi === mmsi)); map.flyTo([vessel.lat, vessel.lon], 11, { duration: .7 }); renderDetail(vessel);
}
function renderDetail(vessel) {
  document.querySelector("#detail-content").innerHTML = `<div class="vessel-hero"><span class="hero-vessel-icon">+</span><div><strong>${vessel.name}</strong><small>${vessel.type} / ${vessel.flag} flagged</small></div><span class="live-chip"><i></i> LIVE</span></div><div class="detail-summary"><div class="summary-cell"><span>MMSI</span><strong>${vessel.mmsi}</strong></div><div class="summary-cell"><span>STATUS</span><strong>${vessel.status}</strong></div><div class="summary-cell"><span>SPEED</span><strong>${vessel.speed} kn</strong></div><div class="summary-cell"><span>COURSE</span><strong>${vessel.course} deg</strong></div></div><div class="rank-heading"><span>Current position</span><small>${vessel.position_source || "AIS"}</small></div><div class="position-readout"><span>LAT ${vessel.lat.toFixed(4)} N</span><span>LON ${vessel.lon.toFixed(4)} E</span></div><div class="rank-heading"><span>Route signal</span><small>heading ${vessel.course} deg</small></div><div class="motion-bar"><span style="width: ${Math.min(100, Math.max(12, vessel.speed * 5))}%"></span></div><p class="motion-note">This vessel is moving at ${vessel.speed} knots. ARACHNID can explain AIS, routes, vessel types, and maritime context.</p>`;
}
function updateClock() { document.querySelector("#clock").textContent = new Date().toISOString().slice(11, 19); }
function setLayer(layer, visible) { if (visible) layer.addTo(map); else map.removeLayer(layer); }
document.querySelector("#refresh-data").addEventListener("click", () => loadData().catch(showOffline));
document.querySelector("#focus-area").addEventListener("click", () => map.flyTo(home, 9, { duration: .8 }));
document.querySelector("#locate-me").addEventListener("click", () => map.flyTo(home, 9, { duration: .8 }));
document.querySelector("#reset-layers").addEventListener("click", () => document.querySelectorAll(".layer-toggle input").forEach((input) => { input.checked = true; setLayer({ vessels: state.vesselLayer, tracks: state.trackLayer }[input.dataset.layer], true); }));
document.querySelector("#map-mode").addEventListener("click", () => { map.removeLayer(state.satelliteLayer); state.baseLayer.addTo(map); document.querySelector("#map-mode").classList.add("active"); document.querySelector("#satellite-mode").classList.remove("active"); });
document.querySelector("#satellite-mode").addEventListener("click", () => { map.removeLayer(state.baseLayer); state.satelliteLayer.addTo(map); document.querySelector("#satellite-mode").classList.add("active"); document.querySelector("#map-mode").classList.remove("active"); });
document.querySelector("#globe-mode").addEventListener("click", () => { state.globeMode = !state.globeMode; if (state.globeMode) { map.removeLayer(state.baseLayer); map.removeLayer(state.satelliteLayer); } else { state.baseLayer.addTo(map); } map.setView(state.globeMode ? [10, 35] : home, state.globeMode ? 3 : 9, { animate: true }); document.querySelector("#globe-mode").classList.toggle("active", state.globeMode); document.querySelector("#view-mode-label").textContent = state.globeMode ? "SEA GLOBE / OCEAN ONLY" : "REGIONAL VIEW"; document.querySelector("#map").classList.toggle("ocean-only", state.globeMode); });
document.querySelectorAll(".layer-toggle input").forEach((input) => input.addEventListener("change", (event) => setLayer({ vessels: state.vesselLayer, tracks: state.trackLayer }[event.target.dataset.layer], event.target.checked)));
document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => { document.querySelectorAll(".nav-item").forEach((nav) => nav.classList.remove("active")); item.classList.add("active"); document.querySelector(".page").dataset.section = item.dataset.section; const target = item.dataset.section === "spills" ? "#spill-lab" : item.dataset.section === "academy" ? "#marine-academy" : "#map"; document.querySelector(target).scrollIntoView({ behavior: "smooth", block: "center" }); }));
document.querySelectorAll(".academy-topics button").forEach((button) => button.addEventListener("click", () => { const input = document.querySelector("#copilot-question"); input.value = button.dataset.question; input.focus(); document.querySelector("#marine-academy").scrollIntoView({ behavior: "smooth", block: "center" }); }));
document.querySelector("#spill-status-button").addEventListener("click", async () => { const result = await request("/api/spills/model-status"); document.querySelector("#spill-model-label").textContent = result.checkpoint_type; });
document.querySelector("#spill-upload").addEventListener("change", async (event) => {
  const file = event.target.files[0]; if (!file) return;
  const result = document.querySelector("#spill-prediction-result"); result.textContent = "Running U-Net scene inference...";
  const form = new FormData(); form.append("upload", file);
  try { const prediction = await request("/api/spills/predict", { method: "POST", body: form }); result.textContent = `${prediction.classification} / ${(prediction.confidence * 100).toFixed(1)}% confidence / ${(prediction.spill_area_fraction * 100).toFixed(2)}% scene area`; } catch (error) { result.textContent = "Inference failed. Check the raster format and API logs."; }
});
document.querySelector("#vessel-search").addEventListener("input", (event) => renderSearchResults(event.target.value));
document.querySelector("#clear-search").addEventListener("click", () => { document.querySelector("#vessel-search").value = ""; document.querySelector("#search-results").innerHTML = ""; });
document.querySelector("#copilot-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const input = document.querySelector("#copilot-question"); const answer = document.querySelector("#copilot-answer"); const question = input.value.trim(); if (!question) return;
  answer.textContent = "Consulting current operational context...";
  try { const result = await request("/api/copilot", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) }); answer.textContent = result.answer; input.value = ""; } catch (error) { answer.textContent = "Copilot is unavailable. The live map remains operational."; }
});
function showOffline(error) { console.error(error); document.querySelector("#status-pulse").classList.add("offline"); document.querySelector("#service-status").textContent = "AIS unavailable"; }
setInterval(updateClock, 1000); setInterval(() => loadData().catch(showOffline), 15000); updateClock(); loadData().then(connectLiveFeed).catch(showOffline);
