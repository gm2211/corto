from api.objects.knots import Knots


class SpeedOverWaterSensor:
    def __init__(self):
        pass

    def cur_speed(self) -> Knots:
        return Knots(0)

