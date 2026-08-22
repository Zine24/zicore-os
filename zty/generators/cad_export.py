from . import AircraftConfig, StageConfig, PropulsionConfig

def generate_missile_wing(config: AircraftConfig) -> dict:
    """Genera geometría alar tipo flying wing / missile body"""
    return {
        "type": "delta",
        "span_m": config.wingspan_m or config.length_m * 0.5,
        "root_chord_m": config.length_m * 0.4,
        "area_m2": (config.wingspan_m or config.length_m * 0.5) * config.length_m * 0.2,
        "sweep_deg": 60,
        "aspect_ratio": ((config.wingspan_m or config.length_m * 0.5) ** 2) / ((config.wingspan_m or config.length_m * 0.5) * config.length_m * 0.2),
    }

def export_step(config: AircraftConfig, path: str):
    """Exporta geometría básica a STEP (placeholder para CadQuery)"""
    with open(path, 'w') as f:
        f.write(f"STEP FILE - {config.name}\n")
        for i, s in enumerate(config.stages):
            f.write(f"STAGE {i}: {s.length_m}m x {s.diameter_m}m cylinder\n")
