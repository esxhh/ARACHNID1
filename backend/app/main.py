import asyncio
import json
from datetime import datetime, timezone
from math import cos, sin, sqrt
import os
from pathlib import Path
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from asgiref.sync import sync_to_async

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"
DJANGO_DIR = BASE_DIR / "backend" / "django"
sys.path.insert(0, str(DJANGO_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from maritime.models import SpillDetection, Vessel
from django.db import connection
from ml.oil_spill_screening import screen_candidate
from backend.app.sentinel import SentinelHubError, configured as sentinel_configured, search_scenes
from backend.app.monitor import SceneMonitor
from pydantic import BaseModel, Field

app = FastAPI(title="ARACHNID Maritime Intelligence", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VESSELS = [
    {"mmsi": "636019874", "name": "Northwind Trader", "type": "Tanker", "flag": "LR", "lat": 25.18, "lon": 55.31, "speed": 12.4, "course": 92, "status": "Underway"},
    {"mmsi": "477091200", "name": "Blue Meridian", "type": "Cargo", "flag": "HK", "lat": 25.43, "lon": 55.05, "speed": 8.7, "course": 261, "status": "Underway"},
    {"mmsi": "538008912", "name": "Asteria", "type": "Tanker", "flag": "MH", "lat": 25.31, "lon": 55.62, "speed": 10.1, "course": 78, "status": "Underway"},
    {"mmsi": "311000742", "name": "Pelagic Dawn", "type": "Cargo", "flag": "BS", "lat": 25.03, "lon": 55.68, "speed": 6.3, "course": 184, "status": "Anchored"},
    {"mmsi": "367772910", "name": "Coastal Sentinel", "type": "Service", "flag": "US", "lat": 25.55, "lon": 55.46, "speed": 14.8, "course": 135, "status": "Underway"},
    {"mmsi": "249781000", "name": "Silver Current", "type": "Tanker", "flag": "MT", "lat": 24.82, "lon": 55.18, "speed": 11.2, "course": 24, "status": "Underway"},
]

SPILLS = [
    {"id": "SPL-2026-0912-01", "name": "Jebel Ali dark spot", "lat": 25.24, "lon": 55.48, "area_km2": 4.8, "confidence": 0.91, "classification": "OIL_SPILL", "detected_at": "2026-09-12T05:40:00Z", "color": "#ef7d5b"},
    {"id": "SPL-2026-0911-03", "name": "Offshore look-alike", "lat": 24.98, "lon": 55.83, "area_km2": 2.1, "confidence": 0.63, "classification": "LOOK_ALIKE", "detected_at": "2026-09-11T18:15:00Z", "color": "#e6b85c"},
]


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        stale = []
        for websocket in self.connections:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


live_manager = ConnectionManager()
scene_monitor = SceneMonitor(live_manager.broadcast)
live_overrides: dict[str, dict] = {}


@app.on_event("startup")
async def start_background_monitor() -> None:
    scene_monitor.start()


@app.on_event("shutdown")
async def stop_background_monitor() -> None:
    await scene_monitor.stop()


def score_vessel(vessel: dict, spill: dict) -> dict:
    distance = sqrt(((vessel["lat"] - spill["lat"]) * 111) ** 2 + ((vessel["lon"] - spill["lon"]) * 101) ** 2)
    distance_score = max(0, 1 - distance / 45)
    time_score = 0.88 if vessel["status"] == "Underway" else 0.52
    trajectory_score = max(0.25, 1 - abs(vessel["course"] - 90) / 180)
    overall = round((distance_score * 0.5 + time_score * 0.25 + trajectory_score * 0.25) * 100)
    return {
        "mmsi": vessel["mmsi"],
        "vessel_name": vessel["name"],
        "distance_km": round(distance, 1),
        "distance_score": round(distance_score * 100),
        "time_score": round(time_score * 100),
        "trajectory_score": round(trajectory_score * 100),
        "overall_score": overall,
        "interpretation": "Priority for review" if overall >= 70 else "Context only",
    }


def database_vessels() -> list[dict]:
    records = list(Vessel.objects.values())
    if not records:
        return VESSELS
    return [
        {
            "mmsi": record["mmsi"],
            "name": record["name"],
            "type": record["vessel_type"],
            "flag": record["flag"],
            "lat": record["latitude"],
            "lon": record["longitude"],
            "speed": record["speed_knots"],
            "course": record["course"],
            "status": record["status"],
        }
        for record in records
    ]


def live_vessels() -> list[dict]:
    elapsed_hours = (time.time() % 86400) / 3600
    vessels = []
    source_vessels = {vessel["mmsi"]: vessel for vessel in database_vessels()}
    source_vessels.update(live_overrides)
    for vessel in source_vessels.values():
        distance = vessel["speed"] * elapsed_hours * 0.018
        angle = vessel["course"] * 3.141592653589793 / 180
        vessels.append({
            **vessel,
            "lat": round(vessel["lat"] + distance * cos(angle), 5),
            "lon": round(vessel["lon"] + distance * sin(angle), 5),
            "live": True,
            "position_source": "AIS simulation",
            "position_updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return vessels


def database_spills() -> list[dict]:
    records = list(SpillDetection.objects.values())
    if not records:
        return SPILLS
    return [
        {
            "id": record["detection_id"],
            "name": record["name"],
            "lat": record["latitude"],
            "lon": record["longitude"],
            "area_km2": record["area_km2"],
            "confidence": record["confidence"],
            "classification": record["classification"],
            "detected_at": record["detected_at"].isoformat(),
            "color": "#ef7d5b" if record["classification"] == "OIL_SPILL" else "#e6b85c",
        }
        for record in records
    ]


class SpillScreenRequest(BaseModel):
    is_land: bool = False
    distance_to_shore_km: float = Field(ge=0)
    darkness_score: float = Field(ge=0, le=1)
    texture_score: float = Field(ge=0, le=1)
    wind_speed_ms: float = Field(ge=0)


class CopilotRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class SentinelSearchRequest(BaseModel):
    bbox: list[float] = Field(min_length=4, max_length=4)
    start: str
    end: str
    limit: int = Field(default=10, ge=1, le=100)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "arachnid-data-plane", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/status")
def status() -> dict:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {
        "status": "ok",
        "services": {
            "fastapi": "ok",
            "django_control_plane": "ok",
            "database": "ok",
        },
        "counts": {"vessels": Vessel.objects.count(), "spills": SpillDetection.objects.count()},
    }


@app.get("/api/vessels")
def get_vessels() -> list[dict]:
    return live_vessels()


@app.get("/api/vessels/live")
def get_live_vessels() -> list[dict]:
    return live_vessels()


@app.get("/api/vessels/world")
def get_world_traffic() -> dict:
    provider = os.getenv("AIS_PROVIDER_NAME")
    return {
        "coverage": "global" if provider else "demo-region",
        "provider": provider or "demo-simulation",
        "live": bool(provider),
        "vessels": live_vessels(),
        "message": "Configure AIS_PROVIDER_NAME and the provider adapter for global live coverage." if not provider else "Provider-backed global traffic adapter configured.",
    }


@app.websocket("/ws/live")
async def live_vessel_stream(websocket: WebSocket) -> None:
    await live_manager.connect(websocket)
    try:
        while True:
            vessels = await sync_to_async(live_vessels, thread_sensitive=True)()
            await websocket.send_json({
                "type": "vessel_positions",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vessels": vessels,
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        live_manager.disconnect(websocket)


@app.post("/api/v1/fast/ingest/ais")
async def ingest_ais(vessels: list[dict] | dict) -> dict:
    """Accept normalized AIS fixes and fan them out to every connected client.

    Persistence remains owned by Django; this MVP fan-out keeps the data-plane
    contract ready for a provider adapter or Redis stream in production.
    """
    if isinstance(vessels, dict):
        vessels = [vessels]
    required = {"mmsi", "name", "lat", "lon", "speed", "course", "status"}
    accepted = [vessel for vessel in vessels if required.issubset(vessel)]
    live_overrides.update({vessel["mmsi"]: vessel for vessel in accepted})
    await live_manager.broadcast({
        "type": "ais_ingest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vessels": accepted,
    })
    return {"accepted": len(accepted), "connected_clients": len(live_manager.connections)}


def grounded_copilot_answer(question: str, vessels: list[dict], spills: list[dict]) -> str:
    underway = [vessel for vessel in vessels if vessel["status"] == "Underway"]
    tankers = [vessel for vessel in vessels if vessel["type"].lower() == "tanker"]
    lower = question.lower()
    if "tanker" in lower:
        names = ", ".join(vessel["name"] for vessel in tankers)
        return f"I found {len(tankers)} tankers in the current AIS context: {names}. This is based on {len(vessels)} loaded vessel positions."
    if "underway" in lower or "moving" in lower:
        names = ", ".join(vessel["name"] for vessel in underway)
        return f"{len(underway)} of {len(vessels)} tracked vessels are underway: {names}. Positions are marked as simulated AIS until a provider feed is configured."
    if "spill" in lower or "slick" in lower:
        return f"There are {len(spills)} stored spill candidates. Treat them as investigative indicators; the current live map is focused on {len(vessels)} vessel positions."
    return f"The current operational context contains {len(vessels)} vessel positions and {len(spills)} spill candidates. Ask about tankers, underway vessels, or spill context for a focused answer."


def ollama_answer(question: str, context: dict) -> str | None:
    payload = json.dumps({
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        "stream": False,
        "system": "You are ARACHNID Marine Academy Copilot. Use only the supplied context. Teach clearly, never accuse a vessel, and say when data is simulated or missing.",
        "prompt": f"Question: {question}\nContext: {json.dumps(context)}",
    }).encode()
    try:
        request = Request(os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"), data=payload, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode()).get("response")
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


@app.post("/api/copilot")
async def copilot(payload: CopilotRequest) -> dict:
    vessels = await sync_to_async(live_vessels, thread_sensitive=True)()
    spills = await sync_to_async(database_spills, thread_sensitive=True)()
    context = {"vessels": vessels, "spills": spills}
    answer = await asyncio.to_thread(ollama_answer, payload.question, context)
    source = "ollama-grounded" if answer else "grounded-local-fallback"
    return {"answer": answer or grounded_copilot_answer(payload.question, vessels, spills), "source": source, "data_timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/spills/screen")
def screen_spill_candidate(payload: SpillScreenRequest) -> dict:
    result = screen_candidate(**payload.model_dump())
    real_checkpoint = BASE_DIR / "models" / "oil_spill_unet_real.pt"
    return {
        "classification": result.classification,
        "confidence": result.confidence,
        "reason": result.reason,
        "model": "conservative-sar-screen-v0",
        "segmentation_checkpoint_available": real_checkpoint.exists(),
        "trained_model_loaded": False,
        "note": "The API screen applies conservative pre-inference safeguards; raster segmentation uses the checkpoint pipeline separately.",
    }


@app.get("/api/spills/model-status")
def spill_model_status() -> dict:
    real_checkpoint = BASE_DIR / "models" / "oil_spill_unet_real.pt"
    default_checkpoint = real_checkpoint if real_checkpoint.exists() else BASE_DIR / "models" / "oil_spill_unet_demo.pt"
    checkpoint = os.getenv("OIL_SPILL_MODEL_PATH") or (str(default_checkpoint) if default_checkpoint.exists() else None)
    return {
        "model": "oil-spill-unet",
        "checkpoint_available": bool(checkpoint),
        "checkpoint_path": checkpoint,
        "checkpoint_type": "real-sentinel1" if checkpoint and "real" in checkpoint else "synthetic-development",
        "inference_runtime": "optional requirements-ml.txt",
    }


@app.get("/api/sentinel/status")
def sentinel_status() -> dict:
    return {
        "provider": "Copernicus Data Space Sentinel Hub",
        "configured": sentinel_configured(),
        "catalog_connected": False,
        "message": "Credentials required" if not sentinel_configured() else "Ready to query Sentinel-1 scenes",
    }


@app.get("/api/monitor/status")
def monitor_status() -> dict:
    return {"service": "sentinel-scene-monitor", **scene_monitor.state, "interval_seconds": max(60, int(os.getenv("SENTINEL_MONITOR_INTERVAL_SECONDS", "900"))), "bbox": scene_monitor.bbox()}


@app.post("/api/monitor/scan")
async def monitor_scan() -> dict:
    await scene_monitor.scan_once()
    return scene_monitor.state


@app.post("/api/sentinel/search")
def sentinel_search(payload: SentinelSearchRequest) -> dict:
    try:
        scenes = search_scenes(bbox=payload.bbox, start=payload.start, end=payload.end, limit=payload.limit)
    except SentinelHubError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"provider": "sentinel-1-grd", "count": len(scenes), "scenes": scenes}


@app.post("/api/spills/predict")
async def predict_spill(upload: UploadFile = File(...)) -> dict:
    """Run the trained U-Net on an uploaded SAR/image raster.

    This endpoint detects a supplied scene; it does not create a live satellite
    feed. A provider/scene-index worker must call it for continuous monitoring.
    """
    checkpoint = BASE_DIR / "models" / "oil_spill_unet_real.pt"
    if not checkpoint.exists():
        raise HTTPException(status_code=503, detail="No real oil-spill checkpoint is available")
    try:
        import numpy as np
        import torch
        from PIL import Image
        from io import BytesIO
        from ml.inference import segment_ocean_candidate
        from ml.unet import load_oil_spill_model

        content = await upload.read()
        image = Image.open(BytesIO(content)).convert("F").resize((256, 192))
        channel = np.asarray(image, dtype="float32")
        low, high = np.percentile(channel, [1, 99])
        normalized = np.zeros_like(channel) if high <= low else np.clip((channel - low) / (high - low), 0, 1)
        tensor = torch.from_numpy(np.stack([normalized, normalized])[None]).float()
        ocean_mask = torch.ones(1, 1, 192, 256, dtype=torch.bool)
        model = load_oil_spill_model(str(checkpoint))
        result = segment_ocean_candidate(model, tensor, ocean_mask)
        mask = np.asarray(result["mask"], dtype=bool)
        return {
            "filename": upload.filename,
            "classification": result["classification"],
            "confidence": result["confidence"],
            "spill_pixels": int(mask.sum()),
            "spill_area_fraction": round(float(mask.mean()), 6),
            "model": "oil-spill-unet-real-sentinel1",
            "warning": "Research detection only. Validate scene georeferencing, land mask, wind, and look-alikes before operational use.",
        }
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"Raster inference failed: {error}") from error


@app.get("/api/spills")
def get_spills() -> list[dict]:
    return database_spills()


@app.get("/api/spills/{spill_id}/correlations")
def get_correlations(spill_id: str, limit: int = Query(default=6, ge=1, le=20)) -> list[dict]:
    spill = next((item for item in database_spills() if item["id"] == spill_id), None)
    if spill is None:
        raise HTTPException(status_code=404, detail=f"Spill {spill_id} was not found")
    return sorted((score_vessel(vessel, spill) for vessel in database_vessels()), key=lambda item: item["overall_score"], reverse=True)[:limit]


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
