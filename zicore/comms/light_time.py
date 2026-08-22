"""
ZICORE ZSRI — Light-time / signal-delay engine for Earth-Moon links.

Realistic round-trip and one-way propagation delays across the Earth-Moon
distance (perigee 363104 km, mean 384400 km, apogee 405696 km), plus an
optional sinusoidal estimate of the current distance.

Usage::

    earth_moon_light_time()          # mean distance
    light_time(km)                   # custom distance
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict

C_KM_S = 299792.458  # speed of light (km/s)

EARTH_MOON_MEAN_KM = 384400.0
EARTH_MOON_PERIGEE_KM = 363104.0
EARTH_MOON_APOGEE_KM = 405696.0
EARTH_MOON_SIDEREAL_PERIOD_S = 27.321661 * 86400.0


def one_way_delay_seconds(distance_km: float) -> float:
    return distance_km / C_KM_S


def round_trip_delay_seconds(distance_km: float) -> float:
    return 2.0 * distance_km / C_KM_S


def _phase(date: datetime) -> float:
    """Sinusoidal phase estimate of the Earth-Moon distance (0..2pi)."""
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t = (date - epoch).total_seconds()
    return (t / EARTH_MOON_SIDEREAL_PERIOD_S) % (2.0 * math.pi)


def earth_moon_distance_estimate(date: datetime | None = None) -> float:
    """Current Earth-Moon distance in km (sinusoid between perigee/apogee)."""
    date = date or datetime.now(timezone.utc)
    mid = (EARTH_MOON_PERIGEE_KM + EARTH_MOON_APOGEE_KM) / 2.0
    amp = (EARTH_MOON_APOGEE_KM - EARTH_MOON_PERIGEE_KM) / 2.0
    return mid + amp * math.sin(_phase(date))


def light_time(distance_km: float | None = None) -> Dict:
    """One-way and round-trip delays for a given distance (km)."""
    if distance_km is None:
        distance_km = EARTH_MOON_MEAN_KM
    distance_km = float(distance_km)
    if distance_km <= 0:
        distance_km = EARTH_MOON_MEAN_KM
    ow = one_way_delay_seconds(distance_km)
    rt = round_trip_delay_seconds(distance_km)
    return {
        "distance_km": round(distance_km, 1),
        "one_way_seconds": round(ow, 6),
        "one_way_ms": round(ow * 1000.0, 3),
        "round_trip_seconds": round(rt, 6),
        "round_trip_ms": round(rt * 1000.0, 3),
        "band": "cislunar",
    }


def earth_moon_light_time() -> Dict:
    """Current light time using the live distance estimate."""
    km = earth_moon_distance_estimate()
    return light_time(km)
