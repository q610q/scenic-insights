"""AMap Web API client (async)."""

from __future__ import annotations

import httpx

AMAP_URL = "https://restapi.amap.com/v3/geocode/geo"


async def amap_geocode(address: str, api_key: str) -> dict:
    """高德地理编码 (async)。

    Returns: { lon, lat, formatted, status }
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(
            AMAP_URL,
            params={"address": address, "key": api_key, "output": "json"},
        )
        r.raise_for_status()
        data = r.json()

    if data.get("status") != "1" or int(data.get("count", 0)) < 1:
        return {"status": "fail", "lon": None, "lat": None, "formatted": None}

    geo = data["geocodes"][0]
    lon, lat = geo["location"].split(",")
    return {
        "status": "ok",
        "lon": float(lon),
        "lat": float(lat),
        "formatted": geo.get("formatted_address"),
        "province": geo.get("province"),
        "city": geo.get("city"),
        "district": geo.get("district"),
    }
