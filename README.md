# ARACHNID

> **A marine traffic atlas, oil-spill research lab, and learning companion for exploring the world's oceans.**

ARACHNID is an open-source geospatial platform for live vessel exploration, Sentinel-1 oil-spill research, and grounded marine education. The browser experience is vessel-first: users can search vessels, inspect routes, follow WebSocket position updates, explore a sea-focused map, and ask the read-only Copilot questions about the current operational context.

The current release combines FastAPI, Django, Leaflet, WebSockets, a real Sentinel-1-derived training checkpoint, and an optional Ollama Copilot. Global live traffic still requires an AIS provider adapter and credentials; the default dataset is clearly marked as simulation.

## Current Status

### Working now

- ARACHNID red-black maritime operations interface with traffic-first navigation.
- Live vessel WebSocket stream with multi-client fan-out on one FastAPI instance.
- AIS ingestion contract at `POST /api/v1/fast/ingest/ais` for normalized provider fixes.
- Vessel search by name, MMSI, and flag; route-history visualization; map and satellite layers.
- Sea globe mode for broad ocean exploration and a marine-learning panel with grounded Copilot answers.
- Django control plane, admin, SQLite persistence, Nginx routing, Docker Compose, and health checks.
- PyTorch U-Net trained on the public CC BY 4.0 Garcia-INPE Sentinel-1-derived dataset: 173 tiles, validation IoU peak 0.6494, held-out test IoU 0.5398.
- Spill Lab raster inference at `POST /api/spills/predict`; accepts TIFF/PNG/JPEG scene uploads and returns classification, confidence, and detected-pixel fraction.
- Sentinel Hub Catalog adapter at `POST /api/sentinel/search` for authenticated Sentinel-1 scene discovery.
- Continuous Sentinel-1 monitor with `GET /api/monitor/status` and manual `POST /api/monitor/scan`; automatic scans run at `SENTINEL_MONITOR_INTERVAL_SECONDS`.

### Provider-dependent

- Worldwide live vessel names, positions, IMO/cargo/draught, and historical routes require a licensed AIS provider and an adapter that posts normalized fixes to the ingestion endpoint.
- Sentinel Hub scene discovery requires a Copernicus Data Space OAuth client. Set `SENTINEL_HUB_CLIENT_ID` and `SENTINEL_HUB_CLIENT_SECRET` before calling `/api/sentinel/search`.
- Ollama answers require an Ollama runtime and pulled model; without it, ARACHNID uses a grounded local fallback.
- Operational oil-spill confidence requires regional Sentinel-1 validation, a land/ocean mask pipeline, and real deployment monitoring. The included checkpoint is a research baseline, not legal attribution.

### Planned

- Redis Pub/Sub for horizontally scaled WebSocket workers.
- PostGIS route history and global spatial search.
- Sentinel-1 scene acquisition, raster preprocessing, polygonization, and regional retraining.
- Authenticated organizations, missions, alerts, geofences, reports, and observability.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-Control%20Plane-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Real--Time-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![CesiumJS](https://img.shields.io/badge/CesiumJS-3D%20Globe-000000?logo=cesium&logoColor=white)](https://cesium.com/platform/cesiumjs/)
[![PostGIS](https://img.shields.io/badge/PostGIS-Geospatial-4169E1?logo=postgresql&logoColor=white)](https://postgis.net/)
[![Redis](https://img.shields.io/badge/Redis-Streams%20%2F%20PubSub-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![PyTorch](https://img.shields.io/badge/PyTorch-ML%20Inference-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0%20%2F%20MIT-blue.svg)](LICENSE)

---

## 📌 Table of Contents

- [Vision](#-vision)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
  - [Control Plane vs. Data Plane](#-control-plane-vs-data-plane)
  - [System Architecture Diagram](#-system-architecture-diagram)
- [Data Pipelines](#-data-pipelines)
  - [1. Real-Time Vessel Telemetry Pipeline](#1-real-time-vessel-telemetry-pipeline)
  - [2. Satellite Oil-Spill Pipeline](#2-satellite-oil-spill-pipeline)
  - [3. Vessel–Spill Spatial-Temporal Correlation Engine](#3-vesselspill-spatial-temporal-correlation-engine)
- [🤖 ARACHNID Copilot](#-ocean-eye-copilot)
- [🧰 Tech Stack](#-tech-stack)
- [🗄️ Spatial Data Model](#️-spatial-data-model)
- [🔌 API Overview](#-api-overview)
- [📁 Project Structure](#-project-structure)
- [🐳 Local Development & Setup](#-local-development--setup)
- [🚀 Production Deployment & Topology](#-production-deployment--topology)
- [🔁 CI/CD & Security](#-cicd--security)
- [📊 Observability](#-observability)
- [🛣️ Roadmap](#️-roadmap)
- [📐 Architectural Rules](#-architectural-rules)
- [⚠️ Detection & Attribution Disclaimer](#️-detection--attribution-disclaimer)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)
- [👨‍💻 Author & Attribution](#-author--attribution)

---

## 🌍 Vision

ARACHNID is designed as a **browser-based, always-on marine traffic atlas and intelligence platform**.

Operators can explore a live interactive globe containing:
- 🚢 **Live vessel tracks** from high-frequency AIS streams (speed, heading, MMSI, IMO, cargo, draught).
- 🛰️ **Satellite oil-spill detections** derived automatically from Sentinel-1 SAR imagery.
- 📐 **Vectorized slick polygons** with associated surface area ($km^2$) and confidence metrics.
- 🔎 **Vessel–spill correlation scores**, linking potential culprit vessels based on spatio-temporal dynamics.
- 🌊 **Environmental context layers**: ocean currents, sea surface temperature, and weather overlays.
- 🚨 **Geofences, alerts, and anomaly indicators** (e.g., sudden AIS gaps, unannounced course changes).
- 🤖 **An AI Copilot** providing natural-language maritime intelligence and automated incident reporting.

### Natural-Language Intelligence Examples
> *"Which tankers were within 30 km of the detected slick off the Strait of Hormuz during the last 12 hours?"*
>
> *"Summarize unusual maritime activity and AIS dropouts in the South China Sea today."*

---

## ✨ Key Features

### 🚢 Real-Time Vessel Tracking
- Ingestion of high-concurrency AIS data via FastAPI endpoints and stream buffers.
- Position caching using Redis Pub/Sub for sub-second client map updates.
- Historical route reconstruction, track downsampling, and dead-reckoning support in CesiumJS.
- Multi-dimensional filtering by MMSI, IMO, flag, vessel classification, and geographic bounding boxes.

### 🛰️ Satellite Oil-Spill Intelligence (SAR & ML)
- Automated Sentinel-1 Synthetic Aperture Radar (SAR) scene indexing and GeoTIFF tile fetching.
- Preprocessing pipeline: speckle filtering, land/shoreline masking, and ocean raster slicing.
- PyTorch segmentation models (U-Net / ResNet backbones) trained to identify dark spots/slicks.
- Vectorization of binary masks into GeoJSON polygons with area ($km^2$) calculation and classification (`OIL_SPILL`, `LOOK_ALIKE`, `UNVERIFIED`).

### 🔎 Vessel–Spill Correlation Engine
When an oil slick is detected, Ocean Eye queries candidate vessels within a defined spatial-temporal envelope. A multi-factor weighted correlation algorithm evaluates potential responsibility:

$$	ext{Score} = (w_{	ext{dist}} 	imes S_{	ext{dist}}) + (w_{	ext{time}} 	imes S_{	ext{time}}) + (w_{	ext{traj}} 	imes S_{	ext{traj}}) + (w_{	ext{env}} 	imes S_{	ext{env}})$$

- **Distance ($S_{	ext{dist}}$):** Proximity of vessel path to the spill polygon centroid.
- **Time ($S_{	ext{time}}$):** Alignment between vessel passage time and SAR acquisition timestamp.
- **Trajectory ($S_{	ext{traj}}$):** Course vectors matching oil drift directions.
- **Environment ($S_{	ext{env}}$):** Wind and ocean current drift correction.

---

## 🏗 System Architecture

ARACHNID utilizes a **hybrid Control Plane / Data Plane architecture**:
- **Django** handles administrative workflows, authentication, organization/missions management, RBAC, domain models, migrations, DRF endpoints, and audit logging.
- **FastAPI** manages the high-throughput data plane: asynchronous AIS ingestion, WebSocket fan-out, high-frequency spatial endpoints, and ML inference proxying.

### Control Plane vs. Data Plane

| Subsystem | Technology | Primary Responsibility |
|---|---|---|
| **Control Plane** | Django + GeoDjango | User Auth, RBAC, Mission configurations, DRF REST APIs, Auditing, Admin Panel |
| **Data Plane** | FastAPI + WebSockets | High-frequency AIS ingestion, Live geospatial queries, Real-time push, Inference proxy |
| **Spatial History** | PostgreSQL + PostGIS | Authoritative vector spatial storage, historical tracks, spill geometries, spatial indexing |
| **Transient Buffer** | Redis (Streams & Pub/Sub) | Ingestion buffering, rate limiting, pub/sub event fan-out, tool caching |
| **Async Processing** | Celery + Celery Beat | SAR pipeline preprocessing, ML batch inference, correlation jobs, PDF export generation |
| **Object Store** | MinIO (S3-compatible) | Heavy GeoTIFF rasters, ML model checkpoints, generated PDF/CSV reports |
| **Spatial Globe** | React + CesiumJS | Interactive 3D WebGL rendering, entity tracks, slick overlays, spatial measurement |
| **AI Copilot** | Ollama / Local LLMs | Read-only natural-language reasoning, tool calling, automated report drafting |

### System Architecture Diagram

```text
                                 OCEAN EYE DASHBOARD
                       React + TypeScript + CesiumJS + WebGL
                                         │
                                         ▼
                                  Nginx / Traefik
                          Edge Routing / SSL / Rate Limit
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
                 ▼                                               ▼
       ┌───────────────────┐                           ┌───────────────────┐
       │   Django App      │                           │  FastAPI Engine   │
       │     (ASGI)        │                           │   (Data Plane)    │
       │                   │                           │                   │
       │ • Control Plane   │                           │ • Ingestion API   │
       │ • Auth / RBAC     │                           │ • Live WebSockets │
       │ • DRF CRUD APIs   │                           │ • GeoJSON Streams │
       │ • Missions / Admin│                           │ • Async ML Proxy  │
       └─────────┬─────────┘                           └─────────┬─────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │
            ┌────────────────────────────┼────────────────────────────┐
            ▼                            ▼                            ▼
   ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
   │ PostgreSQL      │          │     Redis       │          │  MinIO / S3     │
   │ + PostGIS       │          │ Stream / PubSub │          │ Object Storage  │
   │ + pgvector      │          │ Transient State │          │ SAR Rasters/PDF │
   └────────┬────────┘          └────────┬────────┘          └────────┬────────┘
            ▲                            ▲                            ▲
            └────────────────────────────┼────────────────────────────┘
                                         │
                               ┌─────────┴─────────┐
                               │  Celery Workers   │
                               │   + PyTorch / ML  │
                               │                   │
                               │ • Ingestion ETL   │
                               │ • SAR Pipeline    │
                               │ • Correlation Job │
                               │ • Report Gen      │
                               └─────────┬─────────┘
                                         │
                                         ▼
                               ┌───────────────────┐
                               │    LLM Engine     │
                               │  Ollama Runtime   │
                               └───────────────────┘
```

---

## 🔄 Data Pipelines

### 1. Real-Time Vessel Telemetry Pipeline

```text
External AIS Feed / Provider
             │
             ▼
FastAPI Ingestion Endpoint (/api/v1/fast/ingest/ais)
             │
             ▼
Pydantic Validation & Schema Normalization
             │
             ▼
Redis Stream (Buffer & Decouple)
             │
      ┌──────┴───────────────────────┐
      ▼                              ▼
Celery Batch Inserter         FastAPI WebSocket Manager
      │                              │
      ▼                              ▼
PostGIS (vessel_positions)    Browser (CesiumJS 3D Scene)
```

### 2. Satellite Oil-Spill Pipeline

```text
Sentinel-1 SAR GeoTIFF Ingestion
             │
             ▼
MinIO Object Storage (Raw Scene Data)
             │
             ▼
Celery ML Worker Processing:
  ├── Shoreline & Land Masking (OSM / Natural Earth)
  ├── Speckle Filtering (Lee / Frost Filters)
  └── Sub-tile Tiling Matrix
             │
             ▼
PyTorch Inference (U-Net / ResNet-50 Segmentation)
             │
             ▼
Post-Processing & Polygonization (GDAL / Rasterio)
             │
             ▼
PostGIS Storage (spill_detections table with ST_Polygon)
             │
             ▼
Event Trigger ──► Vessel Correlation Engine
```

### 3. Vessel–Spill Spatial-Temporal Correlation Engine

```text
Detected Spill Feature (Polygon, Location, Timestamp)
             │
             ▼
PostGIS Spatial Index Query:
  ST_DWithin(vessel_geom, spill_geom, search_radius)
  WHERE vessel_timestamp BETWEEN (SAR_time - Δt) AND SAR_time
             │
             ▼
Candidate Vessel Selection
             │
             ▼
Calculated Weighted Score Matrix (Distance, Time, Trajectory, Currents)
             │
             ▼
Persisted Correlation Result (SpillVesselCorrelation)
             │
             ▼
Alert Notification Push via WebSockets & Copilot Context
```

---

## 🤖 ARACHNID Copilot and Marine Academy

ARACHNID embeds a dedicated, read-only AI Copilot designed for grounded natural-language queries, marine education, and decision support. The UI includes a Marine Academy with starter questions about AIS, routes, vessel classes, SAR, and ocean science.

### Copilot Architecture & Tooling

```text
User Natural-Language Query
             │
             ▼
LLM Microservice Router
             │
             ├── Tool Calling Interface (Read-Only)
             │     ├── get_vessels_near(lat, lon, radius)
             │     ├── get_active_spills(bbox, confidence)
             │     ├── get_spill_vessel_correlations(spill_id)
             │     └── fetch_weather_context(location)
             │
             ▼
Local Ollama Runtime (Llama 3 / Mistral / Qwen models)
             │
             ▼
Validated Response Generation with Inline Citations
             │
             ▼
Streamed Response to React Copilot Interface
```

### Copilot Guardrails
1. **Zero Write Privileges:** The LLM cannot execute database mutations or alter operational states.
2. **Fact Grounding:** The model must pull live data strictly via defined API tools. If data is absent, it must state so explicitly.
3. **Probabilistic Guardrail:** Correlation scores must always be described as *investigative indicators*, never definitive accusations.
4. **Audit Trail:** All queries, sessions, and tool invocations are logged in `copilot_sessions`.

---

## 🧰 Tech Stack

| Domain | Technologies |
|---|---|
| **Frontend Framework** | React 18, TypeScript, Vite, TailwindCSS |
| **3D Geospatial Engine** | CesiumJS, Resium, WebGL |
| **State & Cache Management** | Zustand, TanStack Query |
| **Control Plane Framework** | Django 5.x, GeoDjango, Django REST Framework |
| **Data Plane Framework** | FastAPI 0.110+, Uvicorn, Pydantic v2 |
| **Database & GIS** | PostgreSQL 16+, PostGIS 3.4+, pgvector, GDAL/GEOS/PROJ |
| **Message Broker & Streams** | Redis 7.x (Streams, Pub/Sub, Cache) |
| **Async Tasks & Queues** | Celery 5.x, Celery Beat |
| **ML & Image Processing** | PyTorch 2.x, TorchVision, OpenCV, Rasterio, Albumentations |
| **LLM Infrastructure** | Ollama (Local Llama 3 / Qwen / Mistral) |
| **Object Storage** | MinIO (S3-compatible) |
| **Deployment & Ops** | Docker, Docker Compose, Nginx / Traefik, Terraform |
| **Observability** | Prometheus, Grafana, Loki, Sentry |

---

## 🗄️ Spatial Data Model

Ocean Eye relies on **PostGIS** for high-performance spatial geometry queries and indexed time-series management.

```text
                    +-------------------+
                    |      vessels      |
                    +-------------------+
                    | mmsi (PK)         |
                    | imo               |
                    | name              |
                    | vessel_type       |
                    | flag              |
                    +---------+---------+
                              |
                              | 1:N
                              v
                    +-------------------+
                    |  vessel_positions |
                    +-------------------+
                    | id (PK)           |
                    | mmsi (FK)         |
                    | timestamp         |
                    | position (Point)  | <--- GiST Index
                    | speed             |
                    | course            |
                    +-------------------+

                    +-------------------+
                    |  spill_detections |
                    +-------------------+
                    | id (PK)           |
                    | scene_id          |
                    | timestamp         |
                    | polygon (Polygon) | <--- GiST Index
                    | area_km2          |
                    | confidence        |
                    +---------+---------+
                              |
                              | 1:N
                              v
                    +-------------------+
                    | spill_correlations|
                    +-------------------+
                    | id (PK)           |
                    | spill_id (FK)     |
                    | mmsi (FK)         |
                    | overall_score     |
                    | distance_score    |
                    | time_score        |
                    +-------------------+
```

### Essential PostGIS Operations
- Spatial distance check: `ST_DWithin(vessel_geom, spill_geom, distance)`
- Surface area computation: `ST_Area(geography(spill_polygon)) / 1000000.0`
- Geographic intersection: `ST_Intersects(vessel_track, spill_polygon)`

---

## 🔌 API Overview

### Django REST Framework (Control Plane)

```http
POST /api/v1/auth/token/        # Obtain JWT bearer token
GET  /api/v1/vessels/           # Query stored vessel registry & metadata
GET  /api/v1/spills/            # Fetch historical spill records & polygons
GET  /api/v1/missions/          # Manage active operational surveillance missions
POST /api/v1/reports/export     # Trigger asynchronous PDF/CSV report generation
```

### FastAPI (Real-Time Plane & Interactive)

```http
POST /api/v1/fast/ingest/ais    # High-concurrency AIS ingestion target
POST /api/v1/fast/detect        # Synchronous/Async SAR tile ML detection trigger
GET  /realtime/vessels          # High-speed spatial spatial query endpoint
WS   /ws/live                   # Global real-time WebSocket for vessel fixes & alerts
```

The MVP now exposes `WS /ws/live` for live vessel position frames and `GET /api/vessels/live` as an HTTP fallback. Oil-spill candidates can be screened through `POST /api/spills/screen`; the conservative screen rejects land and shoreline artifacts before the PyTorch U-Net in `ml/` is loaded with a trained checkpoint. The included real-data checkpoint is trained on the public CC BY 4.0 Garcia-INPE Sentinel-1-derived dataset; its validation/test metrics are research indicators and not operational certification.

---

## 📁 Project Structure

```text
ocean-eye/
├── LICENSE
├── README.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
│
├── backend/
│   ├── django/
│   │   ├── manage.py
│   │   ├── config/              # ASGI, WSGI, Settings (base/local/prod)
│   │   └── apps/
│   │       ├── accounts/        # Auth, User, RBAC
│   │       ├── vessels/         # Django models & DRF ViewSets
│   │       ├── spills/          # Satellite detection records
│   │       ├── missions/        # Mission boundaries & parameters
│   │       ├── correlation/     # Correlation calculation records
│   │       └── copilot_sessions/# Audit trail for AI chat
│   │
│   ├── fastapi/
│   │   ├── app/
│   │   │   ├── main.py          # Entrypoint ASGI application
│   │   │   ├── api/             # High-throughput endpoints
│   │   │   ├── websockets/      # Live WebSocket connection manager
│   │   │   └── services/        # Async PostGIS & Redis queries
│   │   └── Dockerfile
│   │
│   └── llm/
│       ├── app/                 # LLM tool definitions & Ollama client
│       └── Dockerfile
│
├── ml/
│   ├── models/                  # PyTorch U-Net & ResNet definitions
│   ├── preprocessing/           # Speckle filtering & shoreline masks
│   └── inference/               # Pipeline execution scripts
│
├── workers/
│   ├── celery_app.py
│   └── tasks/                   # Ingestion, ML tasks, correlation, PDF export
│
├── frontend/
│   ├── src/
│   │   ├── cesium/              # Globe setup, layers, and camera controls
│   │   ├── components/          # React UI, side panels, tables
│   │   ├── features/            # Feature-specific state machines
│   │   ├── stores/              # Zustand global state
│   │   └── services/            # API & WebSocket client connections
│   ├── package.json
│   └── Dockerfile
│
└── infra/
    ├── nginx/                   # Reverse proxy routing rules
    ├── postgres/                # Init scripts & PostGIS configurations
    ├── monitoring/              # Prometheus & Grafana definitions
    └── terraform/               # IaC scripts for cloud deployment
```

---

## 🐳 Local Development & Setup

### Prerequisites
- **Docker** and **Docker Compose**
- **Node.js** (v18+) & **Python** (3.12+)
- Optional: **NVIDIA Container Toolkit** for GPU-accelerated local inference (PyTorch & Ollama)

### Quickstart

The current runnable MVP uses FastAPI, Django, SQLite, and a browser dashboard. Docker, React, PostGIS, Redis, and the ML pipeline remain planned production upgrades.

1. **Create and activate the virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

The Compose stack now includes Nginx as the public edge. Visit `http://127.0.0.1` for the dashboard; Nginx routes `/ws/` to FastAPI, `/api/v1/` and `/admin/` to Django, and all dashboard/API routes share one origin. For a public deployment, put HTTPS in front of Nginx and configure `DJANGO_ALLOWED_HOSTS` for the real domain.

### Copilot and Live Provider Feeds

The dashboard Copilot calls `POST /api/copilot` and is read-only. It uses current vessel/spill context and an optional Ollama server (`OLLAMA_URL`, `OLLAMA_MODEL`); without Ollama it returns a grounded local answer instead of inventing data.

To enable the local LLM container:

```powershell
docker compose --profile copilot up --build
docker compose exec ollama ollama pull qwen2.5:3b
```

Normalized AIS providers can push fixes to `POST /api/v1/fast/ingest/ais`. Each accepted fix is broadcast to all connected `/ws/live` clients. The current in-process fan-out supports multiple users on one FastAPI worker; production horizontal scaling should place Redis Streams/PubSub between provider ingestion and workers, as described in the architecture above.
2. **Initialize Django and load demo data:**
   ```powershell
   cd backend\django
   python manage.py migrate
   python manage.py seed_demo
   python manage.py createsuperuser
   ```

3. **Start Django in one terminal:**
   ```powershell
   python manage.py runserver 127.0.0.1:8001
   ```

4. **Start FastAPI from the project root in another terminal:**
   ```powershell
   cd ..\..
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

5. **Open the interfaces:**
   - **Dashboard:** `http://127.0.0.1:8000`
   - **FastAPI Swagger:** `http://127.0.0.1:8000/docs`
   - **Django Admin:** `http://127.0.0.1:8001/admin/`
   - **Django Vessel API:** `http://127.0.0.1:8001/api/v1/vessels/`
   - **Django Spill API:** `http://127.0.0.1:8001/api/v1/spills/`

   You can also run `powershell -ExecutionPolicy Bypass -File .\run-dev.ps1` from the project root after initialization.

### Local Production Profile

For a production-style local run, set a real secret and start both services with ASGI workers:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-secret"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
powershell -ExecutionPolicy Bypass -File .\run-prod.ps1
```

This profile assumes HTTPS is terminated by a reverse proxy such as Nginx, Caddy, or a cloud load balancer. For direct local browser access, use `run-dev.ps1`; production mode enables HTTPS redirects and secure cookies. Use `http://127.0.0.1:8000/api/health` for FastAPI health and the proxied HTTPS admin URL for Django. The Django server intentionally does not expose the FastAPI `/api/health` route.

### Planned Container Quickstart

The current container setup is available in `Dockerfile` and `docker-compose.yml`. Start Docker Desktop first, then run:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-secret"
docker compose up --build
```

The dashboard is served at `http://127.0.0.1:8000`, Django admin at `http://127.0.0.1:8001/admin/`, and the SQLite database is persisted in the `ocean_eye_data` Docker volume. The container stack currently packages the Django/FastAPI MVP; PyTorch and SAR inference are not included until an actual trained model and inference contract are added.

1. **Clone Repository:**
   ```bash
   git clone https://github.com/esxhh/OCEAN-EYE.git
   cd OCEAN-EYE
   ```

2. **Set Up Environment Variables:**
   ```bash
   cp .env.example .env
   ```

3. **Spin Up Environment via Docker Compose:**
   ```bash
   docker compose up --build
   ```

4. **Run Spatial Migrations & Create Admin:**
   ```bash
   docker compose exec django python manage.py migrate
   docker compose exec django python manage.py createsuperuser
   ```

5. **Access Endpoint Interfaces:**
   - **Frontend Dashboard:** `http://localhost:3000`
   - **Django Control Panel & Admin:** `http://localhost:8000/admin/`
   - **FastAPI Real-Time Swagger Specs:** `http://localhost:8000/api/v1/fast/docs`
   - **WebSocket Stream:** `ws://localhost:8000/ws/live`

---

## 🚀 Production Deployment & Topology

Ocean Eye can be deployed on a single self-hosted Virtual Private Server (VPS) or scaled across multi-node Kubernetes clusters.

```text
               Public Internet Request
                         │
                         ▼
                    Cloudflare
         (DNS / WAF / DDoS Protection)
                         │
                         ▼
               Nginx Reverse Proxy
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
 Django Control Plane            FastAPI Data Plane
 (Auth / Admin / DRF)            (WebSockets / Ingestion)
        │                                 │
        └────────────────┬────────────────┘
                         ▼
            PostgreSQL / PostGIS / Redis
```

---

## 🔁 CI/CD & Security

### Continuous Integration Pipeline (`.github/workflows/ci.yml`)
- **Frontend:** `npm run lint` ──► `npm run typecheck` ──► `npm test`
- **Django:** `python manage.py check` ──► `pytest`
- **FastAPI:** `pytest`
- **Security Scans:** Container scanning with Trivy and secret leaks prevention with Gitleaks.

### Security Directives
- Standardized JWT authentication with short-lived tokens.
- Strict Role-Based Access Control (RBAC) enforced at Django level.
- Environment variables isolation for database and provider credentials.
- All spatial query endpoints bound to parameterized PostGIS prepared statements to prevent SQL injection.

---

## 📊 Observability

Ocean Eye features out-of-the-box observability:
- **Prometheus:** Collects AIS ingestion rates, WebSocket socket counts, Redis stream lags, and ML model inference durations.
- **Grafana:** Pre-configured dashboards for operational health monitoring.
- **Sentry & Loki:** Centralized exception logging and container log aggregation.

---

## 🛣️ Roadmap

- [x] **Phase 1: Skeleton Core** — GeoDjango, FastAPI ASGI application layer, PostgreSQL/PostGIS stack initialization.
- [x] **Phase 2: Live Maritime Pipeline** — High-concurrency AIS ingestion, Redis Streams integration, WebSocket fan-out, and basic CesiumJS 3D rendering.
- [ ] **Phase 3: Satellite SAR Pipeline** — Automated Sentinel-1 tile download, PyTorch U-Net inference, land masking, polygonization.
- [ ] **Phase 4: Correlation Engine** — Spatial-temporal candidate search, trajectory intersection algorithms, weighted scoring UI.
- [ ] **Phase 5: Copilot Integration** — Local Ollama LLM integration, read-only tools implementation, RAG with pgvector.
- [ ] **Phase 6: Multi-Constellation Support** — Integration of additional SAR constellations (TerraSAR-X, ICEYE) and optical feeds.

---

## 📐 Architectural Rules

1. **Django owns Control & State:** Control plane operations, user management, and transactional entities belong exclusively to Django.
2. **FastAPI owns Telemetry Stream:** High-frequency, async ingestion or WebSockets must be handled by FastAPI.
3. **Redis is Non-Authoritative:** Redis manages transient streams, caching, and state distribution; PostGIS is the sole system of record.
4. **Deterministic Models:** ML tasks execute asynchronously in background Celery workers and never block the ASGI web process.
5. **Copilot is Strictly Read-Only:** The LLM Copilot has zero write privileges on operational database tables.

---

## ⚠️ Detection & Attribution Disclaimer

Ocean Eye is designed strictly as an **investigative decision-support system**.

A satellite SAR dark spot detection can result from multiple natural phenomema (e.g., low-wind areas, algal blooms, internal waves). Spatio-temporal correlation between a vessel track and a slick **does not constitute legal proof of fault or responsibility**. Operational users must verify environmental factors, satellite resolution limitations, and AIS reliability prior to drawing conclusions.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'feat: add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

Please see [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for detailed guidelines.

---

## 📜 License

This project is dual-licensed under the **Apache License 2.0** and **MIT License** terms. See the [`LICENSE`](LICENSE) file for details.

---

## 👨‍💻 Author & Attribution

### **Eshan Mahey**
*Architect & Lead Developer*
- GitHub: [@esxhh](https://github.com/esxhh)

---

> **Ocean Eye**
>
> *See the ocean. Track the movement. Detect the anomaly. Investigate the source.*
