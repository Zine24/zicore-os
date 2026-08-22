import math

class StructuralEngine:
    """Motor estructural simplificado (placeholder para NASTRAN/OpenAeroStruct)"""
    
    @staticmethod
    def beam_stress(moment_nm: float, c_m: float, inertia_m4: float) -> float:
        return moment_nm * c_m / inertia_m4
    
    @staticmethod
    def safety_factor(yield_strength: float, max_stress: float) -> float:
        return yield_strength / max_stress if max_stress > 0 else float('inf')
    
    @staticmethod
    def tank_thickness(pressure_pa: float, radius_m: float, yield_strength: float, sf: float = 2.0) -> float:
        return pressure_pa * radius_m / (yield_strength * 1e6 / sf)
    
    @staticmethod
    def buckling_critical_load(e_gpa: float, length_m: float, radius_m: float, thickness_m: float) -> float:
        e = e_gpa * 1e9
        return 0.6 * e * (thickness_m / radius_m) ** 1.5 * (2 * math.pi * radius_m * thickness_m)
