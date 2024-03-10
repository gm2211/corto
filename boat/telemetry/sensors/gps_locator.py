from api.objects.angle import Angle
from api.objects.gps_coord import GPSCoord
from api.objects.knots import Knots


class GPSLocator:
    def __init__(self):
        pass

    def cur_location(self) -> GPSCoord:
        return GPSCoord(0, 0)

    def cur_heading(self) -> Angle:
        return Angle(0.0)

    def cur_speed_over_ground(self) -> Knots:
        pass

    def cur_course_over_ground(self) -> Angle:
        pass
