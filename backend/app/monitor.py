from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from .sentinel import SentinelHubError, configured, search_scenes


class SceneMonitor:
    def __init__(self, publish) -> None:
        self.publish = publish
        self.task: asyncio.Task | None = None
        self.seen_ids: set[str] = set()
        self.state = {
            "running": False,
            "configured": configured(),
            "last_run": None,
            "last_success": None,
            "last_error": None,
            "new_scenes": 0,
            "total_scenes_seen": 0,
        }

    def bbox(self) -> list[float]:
        raw = os.getenv("SENTINEL_MONITOR_BBOX", "54,24,56,26")
        return [float(value.strip()) for value in raw.split(",")]

    async def scan_once(self) -> None:
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        if not configured():
            self.state["configured"] = False
            self.state["last_error"] = "Set SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET"
            return
        now = datetime.now(timezone.utc)
        start = os.getenv("SENTINEL_MONITOR_START", now.strftime("%Y-%m-%dT00:00:00Z"))
        try:
            scenes = await asyncio.to_thread(search_scenes, bbox=self.bbox(), start=start, end=now.strftime("%Y-%m-%dT%H:%M:%SZ"), limit=100)
            new_scenes = [scene for scene in scenes if scene["id"] not in self.seen_ids]
            self.seen_ids.update(scene["id"] for scene in scenes if scene.get("id"))
            self.state.update({"configured": True, "last_success": self.state["last_run"], "last_error": None, "new_scenes": len(new_scenes), "total_scenes_seen": len(self.seen_ids)})
            for scene in new_scenes:
                await self.publish({"type": "sentinel_scene", "scene": scene, "timestamp": self.state["last_success"]})
        except SentinelHubError as error:
            self.state["last_error"] = str(error)

    async def loop(self) -> None:
        self.state["running"] = True
        interval = max(60, int(os.getenv("SENTINEL_MONITOR_INTERVAL_SECONDS", "900")))
        try:
            while True:
                await self.scan_once()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.state["running"] = False
            raise

    def start(self) -> None:
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.loop())

    async def stop(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
            await self.task
