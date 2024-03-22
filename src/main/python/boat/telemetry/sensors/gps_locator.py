from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord
from api.objects.units.knots import Knots


class GPSLocator:
    def __init__(self):
        self.cur_location = GPSCoord(0, 0)
        self.cur_heading = Angle(0.0)

    def cur_location(self) -> GPSCoord:
        return self.cur_location

    def cur_heading(self) -> Angle:
        return self.cur_heading

    def cur_speed_over_ground(self) -> Knots:
        pass

    def cur_course_over_ground(self) -> Angle:
        pass
