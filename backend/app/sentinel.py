from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CATALOG_URL = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"
_token: dict | None = None


class SentinelHubError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.getenv("SENTINEL_HUB_CLIENT_ID") and os.getenv("SENTINEL_HUB_CLIENT_SECRET"))


def _request_token() -> str:
    global _token
    if _token and _token["expires_at"] > time.time() + 30:
        return _token["access_token"]
    if not configured():
        raise SentinelHubError("Set SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET")
    form = urlencode({
        "grant_type": "client_credentials",
        "client_id": os.environ["SENTINEL_HUB_CLIENT_ID"],
        "client_secret": os.environ["SENTINEL_HUB_CLIENT_SECRET"],
    }).encode()
    request = Request(TOKEN_URL, data=form, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except (HTTPError, URLError, json.JSONDecodeError) as error:
        raise SentinelHubError(f"Sentinel Hub authentication failed: {error}") from error
    _token = {"access_token": payload["access_token"], "expires_at": time.time() + int(payload.get("expires_in", 300))}
    return _token["access_token"]


def search_scenes(*, bbox: list[float], start: str, end: str, limit: int = 10) -> list[dict]:
    query = json.dumps({
        "bbox": bbox,
        "datetime": f"{start}/{end}",
        "collections": ["sentinel-1-grd"],
        "limit": min(limit, 100),
    }).encode()
    request = Request(CATALOG_URL, data=query, headers={"Authorization": f"Bearer {_request_token()}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except (HTTPError, URLError, json.JSONDecodeError) as error:
        raise SentinelHubError(f"Sentinel Hub Catalog search failed: {error}") from error
    return [
        {
            "id": feature.get("id"),
            "datetime": feature.get("properties", {}).get("datetime"),
            "bbox": feature.get("bbox"),
            "collection": feature.get("collection"),
            "assets": list(feature.get("assets", {}).keys()),
        }
        for feature in payload.get("features", [])
    ]
