from api.objects.gps_coord import GPSCoord


class GPSLocator:
    def __init__(self):
        pass

    def get_cur_location(self) -> GPSCoord:
        return GPSCoord(0, 0)
