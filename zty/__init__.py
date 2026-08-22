from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Material:
    name: str
    density_kgm3: float
    yield_strength_mpa: float
    young_modulus_gpa: float
    max_temp_c: float
    cost_per_kg: float

MATERIALS = {
    "cfrp_standard": Material("CFRP Standard", 1600, 600, 70, 180, 80),
    "cfrp_aerospace": Material("CFRP Aerospace", 1550, 800, 85, 200, 250),
    "al_li_2195": Material("Al-Li 2195", 2710, 550, 76, 150, 45),
    "ti_6al4v": Material("Ti-6Al-4V", 4430, 880, 114, 400, 120),
    "inconel_718": Material("Inconel 718", 8190, 1030, 200, 700, 200),
    "pica_x": Material("PICA-X", 300, 5, 1, 1900, 500),
    "cmc_sic": Material("CMC SiC/SiC", 2500, 300, 200, 1400, 800),
    "hdfe": Material("HDPE (Blindaje)", 970, 25, 1, 80, 10),
}

@dataclass
class PropulsionConfig:
    cycle: str = "ffsc"  # ffsc, staged, gas-generator
    fuel: str = "methalox"
    thrust_kN: float = 350.0
    isp_sea: float = 330.0
    isp_vac: float = 370.0
    chamber_pressure_bar: float = 250.0
    throttle_range: tuple = (0.4, 1.0)

@dataclass
class StageConfig:
    name: str
    length_m: float
    diameter_m: float
    dry_mass_kg: float
    propellant_mass_kg: float
    material: str = "cfrp_aerospace"
    engines: int = 1
    reusable: bool = True

@dataclass  
class AircraftConfig:
    name: str
    vehicle_type: str  # "launcher", "spaceplane", "drone", "capsule"
    stages: list = field(default_factory=list)
    payload_kg: float = 0.0
    length_m: float = 0.0
    wingspan_m: Optional[float] = None
    crew: int = 0
    propulsion: PropulsionConfig = field(default_factory=PropulsionConfig)
    
    def total_mass_kg(self) -> float:
        return sum(s.dry_mass_kg + s.propellant_mass_kg for s in self.stages) + self.payload_kg
    
    def mass_ratio(self) -> float:
        dry = sum(s.dry_mass_kg for s in self.stages)
        wet = self.total_mass_kg()
        return wet / (wet - sum(s.propellant_mass_kg for s in self.stages)) if wet > 0 else 0
    
    def delta_v(self) -> float:
        total = 0
        for s in self.stages:
            mr = (s.dry_mass_kg + s.propellant_mass_kg) / s.dry_mass_kg if s.dry_mass_kg > 0 else 1
            total += 9.81 * self.propulsion.isp_vac * (mr ** 0.5 - 1) / (mr ** 0.5)
        return total
