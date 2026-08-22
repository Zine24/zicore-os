from .. import AircraftConfig, StageConfig, PropulsionConfig, MATERIALS

class AircraftFactory:
    """Genera configuraciones de aeronaves predefinidas"""
    
    @staticmethod
    def blackvanta() -> AircraftConfig:
        return AircraftConfig(
            name="BlackVanta2K",
            vehicle_type="drone",
            crew=1,
            length_m=4.5,
            wingspan_m=6.2,
            payload_kg=120,
            stages=[
                StageConfig("main", 4.5, 1.8, 350, 80, "cfrp_standard", 8, True),
            ],
            propulsion=PropulsionConfig("gas-generator", "methalox", 0.4, 280, 300, 50),
        )
    
    @staticmethod
    def ziron_sigma() -> AircraftConfig:
        return AircraftConfig(
            name="ZiRØN-Σ",
            vehicle_type="spaceplane",
            crew=4,
            length_m=82.0,
            wingspan_m=None,
            payload_kg=5000,
            stages=[
                StageConfig("booster", 45, 9.0, 45000, 340000, "cfrp_aerospace", 6, True),
                StageConfig("core", 37, 9.0, 28000, 180000, "cfrp_aerospace", 3, True),
            ],
            propulsion=PropulsionConfig("ffsc", "methalox", 2200, 330, 375, 250),
        )
    
    @staticmethod
    def zi_voyager() -> AircraftConfig:
        return AircraftConfig(
            name="Zi-Voyager",
            vehicle_type="launcher",
            payload_kg=1500,
            length_m=38.0,
            stages=[
                StageConfig("stage1", 24, 3.7, 12000, 95000, "al_li_2195", 4, True),
                StageConfig("stage2", 12, 3.7, 2500, 22000, "al_li_2195", 1, False),
            ],
            propulsion=PropulsionConfig("staged", "methalox", 350, 320, 365, 180),
        )
    
    @staticmethod
    def obsidiana() -> AircraftConfig:
        return AircraftConfig(
            name="Obsidiana",
            vehicle_type="capsule",
            crew=1,
            length_m=3.0,
            payload_kg=150,
            stages=[
                StageConfig("capsule", 3.0, 2.4, 800, 50, "cfrp_standard", 0, True),
            ],
            propulsion=PropulsionConfig("gas-generator", "hydrazine", 1.5, 220, 230, 15),
        )
