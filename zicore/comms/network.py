"""
ZICORE ZSRI — SpaceNetwork orchestrator.

Single facade over the whole space communication stack:

    Earth LEO network (GSaaS) -> Earth Gateway -> Cislunar relay -> Luna

Loads provider enable/disable flags from ``data/config/comms_providers.json``
(optional; defaults to everything enabled). Credentials are NEVER stored in
this file — they come from environment variables only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from . import light_time as _lt
from .link_budget import BANDS, band, link_budget as _link_budget
from .providers import (
    SEGMENT_CISLUNAR,
    SEGMENT_EARTH,
    SEGMENT_LEO,
    SEGMENT_LUNAR,
    SEGMENT_LABELS,
    get_providers,
    provider_list,
    register_provider,
)

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "config" / "comms_providers.json"


def _load_config() -> Dict:
    try:
        if _CONFIG_PATH.exists():
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _build_registry() -> None:
    """Import every adapter so it registers itself. Non-fatal per module."""
    try:
        from . import providers  # noqa: F401  (self-registering)
    except Exception:
        pass
    try:
        from . import aws_gs  # noqa: F401  (self-registering)
    except Exception:
        pass


class SpaceNetwork:
    """Singleton facade for ZSRI."""

    _instance: Optional["SpaceNetwork"] = None

    def __new__(cls) -> "SpaceNetwork":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        _build_registry()
        cfg = _load_config()
        enabled = cfg.get("enabled", {})
        for p in get_providers():
            if p.id in enabled:
                p.enabled = bool(enabled[p.id])

    # -- introspection ----------------------------------------------------
    def providers(self, segments: Optional[List[str]] = None) -> List[Dict]:
        return provider_list(segments)

    def stations(self, provider_id: Optional[str] = None) -> List[Dict]:
        out = []
        for p in get_providers():
            if provider_id and p.id != provider_id:
                continue
            if not p.enabled:
                continue
            try:
                items = p.list_stations()
            except Exception as e:
                items = [{"provider": p.id, "error": str(e)[:200]}]
            out.extend(items)
        return out

    def schedule_contact(self, provider_id: str, **kwargs) -> Dict:
        for p in get_providers():
            if p.id == provider_id and p.enabled:
                try:
                    return p.schedule_contact(**kwargs)
                except Exception as e:
                    return {"provider": provider_id, "status": "error", "error": str(e)[:200]}
        return {"provider": provider_id, "status": "error", "error": f"provider not found or disabled"}

    # -- layered network map ----------------------------------------------
    def network(self) -> Dict:
        layers = []
        for seg in (SEGMENT_LEO, SEGMENT_EARTH, SEGMENT_CISLUNAR, SEGMENT_LUNAR):
            pro = [p for p in get_providers() if p.segment == seg and p.enabled]
            layers.append({
                "segment": seg,
                "label": SEGMENT_LABELS[seg],
                "providers": [p.health() for p in pro],
            })
        return {
            "layers": layers,
            "light_time": self.light_time(),
            "bands": {k: v["name"] for k, v in BANDS.items()},
        }

    # -- physics ----------------------------------------------------------
    def light_time(self, distance_km: Optional[float] = None) -> Dict:
        return _lt.light_time(distance_km)

    def earth_moon_status(self) -> Dict:
        km_now = _lt.earth_moon_distance_estimate()
        return {
            "distance_km_now": round(km_now, 1),
            "perigee_km": _lt.EARTH_MOON_PERIGEE_KM,
            "apogee_km": _lt.EARTH_MOON_APOGEE_KM,
            "now": _lt.light_time(km_now),
            "perigee": _lt.light_time(_lt.EARTH_MOON_PERIGEE_KM),
            "apogee": _lt.light_time(_lt.EARTH_MOON_APOGEE_KM),
        }

    def link_budget(self, **kwargs) -> Dict:
        freq = kwargs.pop("freq_hz", None)
        if freq is None:
            b = band(kwargs.pop("band", "X"))
            freq = b["freq_hz"]
        else:
            freq = float(freq)
        dist_km = kwargs.pop("distance_km", 384400.0)
        distance_m = float(dist_km) * 1000.0
        return _link_budget(freq_hz=freq, distance_m=distance_m, **kwargs)
