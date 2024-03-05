from boat.comms.lora.boat_radio import BoatRadio
from boat.controls.boat_attitude_controller import BoatAttitudeController
from api.objects.angle import Angle
from api.objects.gps_coord import GPSCoord


class CommandReceiver:
    def __init__(self, radio: BoatRadio, boat_controller: BoatAttitudeController):
        self.radio: BoatRadio = radio
        self.cur_dest: GPSCoord = GPSCoord(0, 0)
        self.boat_controller: BoatAttitudeController = boat_controller

        radio.register_callback(self.parse_command)

    def get_cur_destination(self) -> GPSCoord:
        return self.cur_dest

    def parse_command(self, command: str) -> None:
        if command.startswith("DEST"):
            lat, lon = command.split(" ")[1].split(",")
            self.cur_dest = GPSCoord(float(lat), float(lon))
        elif command.startswith("RUDDER"):
            angle: Angle = Angle(int(command.split(" ")[1]))
            self.boat_controller.set_rudder_angle(angle)
        else:
            print("Unknown command:", command)
        pass
