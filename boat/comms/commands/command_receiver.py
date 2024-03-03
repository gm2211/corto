from boat.objects.gps_coord import GPSCoord


class CommandReceiver:
    def __init__(self):
        pass

    def get_cur_destination(self) -> GPSCoord:
        return GPSCoord(0, 0)
