"""On-demand metadata lookup; one short Steam Store request, cached in SQLite."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch_steam_metadata(appid: str, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
    if not str(appid).isdigit():
        return None
    query = urlencode({"appids": str(appid), "l": "spanish"})
    request = Request(
        "https://store.steampowered.com/api/appdetails?" + query,
        headers={"User-Agent": "NIA-Decky/0.2 (game metadata cache)"},
    )
    try:
        with urlopen(request, timeout=max(1.0, min(5.0, float(timeout)))) as response:
            payload = json.loads(response.read(512 * 1024).decode("utf-8", errors="replace"))
        item = payload.get(str(appid), {})
        if not item.get("success"):
            return None
        data = item.get("data", {})
        genres = [str(entry.get("description", "")) for entry in data.get("genres", []) if entry.get("description")]
        return {
            "name": data.get("name", ""),
            "summary": data.get("short_description", ""),
            "genres": genres[:12],
            "source": "Steam Store",
            "url": "https://store.steampowered.com/app/" + str(appid),
        }
    except Exception:
        return None
