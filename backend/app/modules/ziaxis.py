"""ZiAXIS - Gravitational Path Descent (GPD) engine.
Subsistema fisico-estructural de ZiNav para descenso gravitacional navegado.

Jerarquia:  ZiNav > ZiAXIS > GPD
"""
import math

class GPDEngine:
    """Gravitational Path Descent - motor de descenso gravitacional"""

    G = 6.67430e-11

    @staticmethod
    def gravitational_gradient(mass_planet_kg: float, altitude_m: float) -> float:
        r = 6371000 + altitude_m
        return -GPDEngine.G * mass_planet_kg / (r ** 3)

    @staticmethod
    def tidal_force(mass_vehicle_kg: float, length_m: float, gradient: float) -> float:
        return mass_vehicle_kg * length_m * gradient

    @staticmethod
    def descent_angle(axial_alignment_deg: float, local_gradient: float) -> float:
        rad = math.radians(axial_alignment_deg)
        return math.degrees(math.atan2(local_gradient * math.cos(rad), 9.81))

    @staticmethod
    def energy_distribution(altitude_km: float, velocity_kms: float, mass_kg: float) -> dict:
        ep = mass_kg * 9.81 * altitude_km * 1000
        ek = 0.5 * mass_kg * (velocity_kms * 1000) ** 2
        total = ep + ek
        return {
            "potential_j": round(ep, 1),
            "kinetic_j": round(ek, 1),
            "total_j": round(total, 1),
            "distributed": total > 0,
        }

    @staticmethod
    def path_stability(alignment_deg: float, mass_distribution: float) -> float:
        ideal = abs(alignment_deg) * 0.3 + abs(50 - mass_distribution) * 0.7
        return max(0, 100 - ideal)
