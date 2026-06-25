import math

class AeroEngine:
    """Motor de aerodinámica simplificado (placeholder para SU2/OpenVSP)"""
    
    @staticmethod
    def wing_area(mass_kg: float, wing_loading: float = 3500) -> float:
        return mass_kg * 9.81 / wing_loading
    
    @staticmethod
    def drag_coefficient(cd0: float, cl: float, aspect_ratio: float, oswald: float = 0.8) -> float:
        return cd0 + (cl ** 2) / (math.pi * aspect_ratio * oswald)
    
    @staticmethod
    def lift_required(mass_kg: float, velocity_ms: float, rho: float = 1.225) -> float:
        return 2 * mass_kg * 9.81 / (rho * velocity_ms ** 2)
    
    @staticmethod
    def power_required(mass_kg: float, velocity_ms: float, cd: float, area: float, rho: float = 1.225) -> float:
        drag = 0.5 * rho * velocity_ms ** 2 * area * cd
        return drag * velocity_ms
    
    @staticmethod
    def thrust_to_weight(thrust_n: float, mass_kg: float) -> float:
        return thrust_n / (mass_kg * 9.81)

    @staticmethod
    def drag_force(rho: float, velocity_ms: float, area: float, cd: float) -> float:
        return 0.5 * rho * velocity_ms ** 2 * area * cd
