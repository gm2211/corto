from api.objects.units.knots import Knots


class SpeedOverWaterSensor:
    def __init__(self):
        self.cur_speed = Knots(0)

    def cur_speed(self) -> Knots:
        return self.cur_speed

