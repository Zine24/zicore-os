import math

class PropulsionEngine:
    """Motor de diseno de propulsion (placeholder para PyCycle/RocketPy)"""

    @staticmethod
    def thrust_chamber_pressure(area_ratio: float, isp: float, ambient_pressure: float = 101325) -> float:
        return ambient_pressure * (1 + area_ratio * (isp * 9.81 / (2 * 8314 * 3000)) ** 0.5)

    @staticmethod
    def nozzle_area_ratio(exit_pressure: float, chamber_pressure: float, gamma: float = 1.2) -> float:
        if chamber_pressure <= 0 or exit_pressure <= 0:
            return 0
        pr = exit_pressure / chamber_pressure
        return ((gamma + 1) / 2) ** (1 / (gamma - 1)) * pr ** (1 / gamma) * \
               math.sqrt((gamma + 1) / (gamma - 1) * (1 - pr ** ((gamma - 1) / gamma)))

    @staticmethod
    def mass_flow_rate(thrust_n: float, isp_s: float) -> float:
        return thrust_n / (isp_s * 9.81) if isp_s > 0 else 0

    @staticmethod
    def ideal_delta_v(mass_initial: float, mass_final: float, isp: float) -> float:
        if mass_final <= 0 or mass_initial <= 0 or mass_initial <= mass_final:
            return 0
        return isp * 9.81 * math.log(mass_initial / mass_final)

    @staticmethod
    def delta_v(isp: float, g0: float, mass_ratio: float) -> float:
        if mass_ratio <= 1:
            return 0
        return isp * g0 * math.log(mass_ratio)

    @staticmethod
    def chamber_pressure(thrust_n: float, throat_area_m2: float, c_star: float = 1800.0) -> float:
        return thrust_n / (c_star * throat_area_m2) if throat_area_m2 > 0 else 0
