"""
ZICORE ZSRI — Provider registry & adapter interface.

Every ground/space network (KSAT, Leaf Space, SSC, AWS Ground Station,
future lunar relays) implements the ``SpaceProvider`` interface and is
registered in ``REGISTRY``. ZICORE treats all of them as one space network.

Segments::
    LEO          — LEO/MEO ground stations (direct-to-satellite)
    EARTH_GATE   — big-aperture Earth gateways (S/X/Ka/optical)
    CISLUNAR     — cislunar relay nodes (L1/L2 relay satellites)
    LUNAR        — lunar surface / lunar orbiter terminals
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

# Network segments
SEGMENT_LEO = "LEO"
SEGMENT_EARTH = "EARTH_GATE"
SEGMENT_CISLUNAR = "CISLUNAR"
SEGMENT_LUNAR = "LUNAR"

SEGMENT_LABELS = {
    SEGMENT_LEO: "LEO Ground Network",
    SEGMENT_EARTH: "Earth Gateway",
    SEGMENT_CISLUNAR: "Cislunar Relay",
    SEGMENT_LUNAR: "Lunar Terminal",
}


class SpaceProvider:
    """Base class for a space communication provider."""

    id: str = "base"
    name: str = "Base Provider"
    segment: str = SEGMENT_LEO
    bands: List[str] = ["S", "X", "Ka"]
    api_base: str = ""
    enabled: bool = True

    def describe(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "segment": self.segment,
            "segment_label": SEGMENT_LABELS.get(self.segment, self.segment),
            "bands": self.bands,
            "api_base": self.api_base,
            "enabled": self.enabled,
            "available": True,
            "reason": None,
        }

    def health(self) -> Dict:
        return {**self.describe(), "status": "ok", "latency_ms": 0}

    def list_stations(self) -> List[Dict]:
        return []

    def schedule_contact(self, **kwargs) -> Dict:
        raise NotImplementedError(f"{self.id} does not support scheduling")

    def stream_contact(self, contact_id: str) -> Dict:
        raise NotImplementedError(f"{self.id} does not support streaming")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SpaceProvider {self.id} ({self.segment})>"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
REGISTRY: Dict[str, SpaceProvider] = {}


def register_provider(provider):
    if isinstance(provider, type):
        provider = provider()
    REGISTRY[provider.id] = provider
    return provider


def get_providers() -> List[SpaceProvider]:
    return list(REGISTRY.values())


def provider_list(segments: Optional[List[str]] = None) -> List[Dict]:
    out = []
    for p in get_providers():
        if segments and p.segment not in segments:
            continue
        try:
            out.append(p.health())
        except Exception as e:  # pragma: no cover
            out.append({**p.describe(), "status": "error", "reason": str(e)})
    return out


# ---------------------------------------------------------------------------
# Mock provider — always available, no credentials, for dev/demo
# ---------------------------------------------------------------------------
_MOCK_STATIONS = [
    {"id": "kval", "name": "KSAT Svalbard", "lat": 78.23, "lon": 15.39, "bands": ["S", "X", "Ka"]},
    {"id": "tts",  "name": "KSAT Troll (Antarctica)", "lat": -72.01, "lon": 2.53, "bands": ["S", "X", "Ka"]},
    {"id": "mtm",  "name": "Canberra DSN 43", "lat": -35.40, "lon": 148.98, "bands": ["S", "X", "Ka"]},
    {"id": "msd",  "name": "Madrid DSN 63", "lat": 40.43, "lon": -4.25, "bands": ["S", "X", "Ka"]},
    {"id": "gds",  "name": "Goldstone DSN 14", "lat": 35.43, "lon": -116.89, "bands": ["S", "X", "Ka"]},
    {"id": "cdmx", "name": "ZiCore Gateway CDMX (planned)", "lat": 19.43, "lon": -99.13, "bands": ["S", "X"], "planned": True},
]


@register_provider
class MockProvider(SpaceProvider):
    id = "mock"
    name = "ZSRI Mock Network"
    segment = SEGMENT_LEO
    bands = ["UHF", "S", "X", "Ka"]
    api_base = "local://mock"

    def health(self) -> Dict:
        return {**self.describe(), "status": "ok", "latency_ms": 1}

    def list_stations(self) -> List[Dict]:
        return _MOCK_STATIONS

    def schedule_contact(self, **kwargs) -> Dict:
        return {
            "provider": self.id,
            "contact_id": f"mock-{int(time.time())}",
            "scheduled": True,
            "params": kwargs,
        }

    def stream_contact(self, contact_id: str) -> Dict:
        return {
            "provider": self.id,
            "contact_id": contact_id,
            "streaming": True,
            "format": "vita49-udp",
            "url": f"mock://stream/{contact_id}",
        }


@register_provider
class MockLunarRelay(SpaceProvider):
    """Placeholder for the future commercial lunar relay segment
    (NASA LCRNS / Intuitive Machines Lunar Data Network). Not operational
    yet — reports available=False until the relay service exists."""

    id = "lunar-relay"
    name = "Lunar Relay (LCRNS / IM)"
    segment = SEGMENT_CISLUNAR
    bands = ["S", "X", "Ka"]
    api_base = ""
    enabled = False

    def describe(self) -> Dict:
        return {
            **super().describe(),
            "available": False,
            "reason": "Commercial lunar relay not yet operational (LCRNS in deployment)",
        }

    def health(self) -> Dict:
        return {**self.describe(), "status": "degraded", "latency_ms": None}
