"""
ZICORE ZSRI — Link budget engine.

Pure physics for satellite/cislunar radio links. No external dependencies.

Implements the Friis transmission equation, free-space path loss, link
budget with receiver noise, and SNR/bit-rate tradeoffs for the band plans
used by the ZSRI ground networks (UHF/S/X/Ka + optical placeholder).

Usage::

    link_budget(freq_hz=BANDS["X"]["freq_hz"], distance_m=384400e3,
                tx_power_dbm=20, tx_gain_db=30, rx_gain_db=42)
"""

from __future__ import annotations

import math
from typing import Dict, Optional

C_M_S = 299792458.0  # speed of light
K_BOLTZMANN = 1.380649e-23  # J/K

# Standard deep-space/ground bands
BANDS: Dict[str, Dict] = {
    "UHF": {"freq_hz": 400e6,  "name": "UHF"},
    "S":   {"freq_hz": 2200e6, "name": "S-band"},
    "X":   {"freq_hz": 8400e6, "name": "X-band"},
    "K":   {"freq_hz": 22000e6, "name": "K-band"},
    "Ka":  {"freq_hz": 25500e6, "name": "Ka-band"},
    "OPT": {"freq_hz": 281.25e12, "name": "Optical (placeholder)", "optical": True},
}


def band(name: str) -> Dict:
    name = (name or "").upper()
    if name in BANDS:
        return BANDS[name]
    raise ValueError(f"unknown band {name!r}; valid: {list(BANDS)}")


def freespace_loss_db(freq_hz: float, distance_m: float) -> float:
    """Free-space path loss (Friis, isotropic) in dB."""
    if freq_hz <= 0 or distance_m <= 0:
        return 0.0
    return 20.0 * math.log10(4.0 * math.pi * distance_m * freq_hz / C_M_S)


def distance_m_to_km(dist_m: float) -> float:
    return dist_m / 1000.0


def link_budget(
    *,
    freq_hz: float,
    distance_m: float,
    tx_power_dbm: float = 20.0,
    tx_gain_db: float = 30.0,
    rx_gain_db: float = 42.0,
    losses_db: float = 3.0,
    rx_noise_temp_k: float = 200.0,
    data_rate_bps: Optional[float] = None,
    bandwidth_hz: Optional[float] = None,
) -> Dict:
    """Full downlink budget. Returns rx power, SNR and achievable rate.

    - If ``bandwidth_hz`` is given, computes C/N0 and C/N.
    - If ``data_rate_bps`` is given, computes Eb/N0 (energy per bit) and link margin.
    - If both are given, Eb/N0 derives from the data rate.
    """
    fspl_db = freespace_loss_db(freq_hz, distance_m)
    eirp_dbw = tx_power_dbm + tx_gain_db - 30.0
    rx_power_dbm = tx_power_dbm + tx_gain_db - fspl_db - losses_db + rx_gain_db

    ref_bw_hz = bandwidth_hz if bandwidth_hz else (data_rate_bps if data_rate_bps else 1.0)
    noise_power_w = K_BOLTZMANN * rx_noise_temp_k * ref_bw_hz
    noise_power_dbm = 10.0 * math.log10(noise_power_w) + 30.0
    c_n_db = rx_power_dbm - noise_power_dbm

    cn0_db_hz = c_n_db + (10.0 * math.log10(ref_bw_hz) if ref_bw_hz > 0 else 0.0)

    eb_no_db = None
    if data_rate_bps and data_rate_bps > 0:
        eb_no_db = cn0_db_hz - 10.0 * math.log10(data_rate_bps)

    # Shannon capacity as upper bound
    capacity_bps = None
    if bandwidth_hz and bandwidth_hz > 0:
        linear = 10.0 ** (c_n_db / 10.0)
        if linear > 0:
            capacity_bps = bandwidth_hz * math.log2(1.0 + linear)

    return {
        "freq_hz": freq_hz,
        "distance_m": distance_m,
        "distance_km": distance_m_to_km(distance_m),
        "freespace_loss_db": round(fspl_db, 2),
        "eirp_dbm": round(tx_power_dbm + tx_gain_db, 2),
        "tx_power_dbm": tx_power_dbm,
        "tx_gain_db": tx_gain_db,
        "rx_gain_db": rx_gain_db,
        "losses_db": losses_db,
        "rx_noise_temp_k": rx_noise_temp_k,
        "rx_power_dbm": round(rx_power_dbm, 2),
        "noise_power_dbm": round(noise_power_dbm, 2),
        "c_n_db": round(c_n_db, 2),
        "cn0_db_hz": round(cn0_db_hz, 2),
        "eb_no_db": round(eb_no_db, 2) if eb_no_db is not None else None,
        "shannon_capacity_bps": round(capacity_bps) if capacity_bps else None,
        "data_rate_bps": data_rate_bps,
        "bandwidth_hz": bandwidth_hz,
    }


def required_distance_for_rate(
    *,
    freq_hz: float,
    data_rate_bps: float,
    min_eb_no_db: float = 4.0,
    tx_power_dbm: float = 20.0,
    tx_gain_db: float = 30.0,
    rx_gain_db: float = 42.0,
    losses_db: float = 3.0,
    rx_noise_temp_k: float = 200.0,
) -> Optional[float]:
    """Maximum range (m) at which a given rate closes with margin (Eb/N0 >= min)."""
    c = 10.0 ** (min_eb_no_db / 10.0) * data_rate_bps * K_BOLTZMANN * rx_noise_temp_k
    if c <= 0:
        return None
    rx_power_w = (10.0 ** ((tx_power_dbm - 30.0) / 10.0)) * (10.0 ** (tx_gain_db / 10.0)) * (
        10.0 ** (rx_gain_db / 10.0)
    ) / (10.0 ** (losses_db / 10.0))
    if rx_power_w <= c:
        return None
    ratio = rx_power_w / c
    dist = math.sqrt(ratio) * C_M_S / (4.0 * math.pi * freq_hz)
    return dist
