from .base import BaseModuleState

class ZIRobotState(BaseModuleState):
    name: str = "zirobot"
    units_active: int = 3
    units_standby: int = 5
    joint_temp_c: float = 38.0
    manipulator_load_kg: float = 12.5
    autonomy_level: str = "semi"
    task: str = "maintenance"

    def _eval(self):
        if self.joint_temp_c > 70:
            self.status = "critical"
        elif self.joint_temp_c > 55:
            self.status = "warning"
        else:
            self.status = "nominal"
