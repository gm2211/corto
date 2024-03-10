from api.objects.commands.SendTelemetry import SendTelemetry
from api.objects.commands.SetSail import SetSail
from api.objects.commands.TurnRudder import TurnRudder
from boat.comms.lora.boat_radio import BoatRadio
from boat.controls.boat_attitude_controller import BoatAttitudeController
from api.objects.units.angle import Angle
from api.objects.units.gps_coord import GPSCoord


class CommandReceiver:
    def __init__(self, radio: BoatRadio, boat_controller: BoatAttitudeController):
        self.radio: BoatRadio = radio
        self.cur_dest: GPSCoord = GPSCoord(0, 0)
        self.boat_controller: BoatAttitudeController = boat_controller

        radio.register_callback(self.parse_command)

    def get_cur_destination(self) -> GPSCoord:
        return self.cur_dest

    @staticmethod
    def parse_command(command: str) -> SetSail | TurnRudder | SendTelemetry | None:
        if SetSail.can_parse_lora_data(command):
            return SetSail.deserialize_from_lora(command)
        if TurnRudder.can_parse_lora_data(command):
            return TurnRudder.deserialize_from_lora(command)
        if SendTelemetry.can_parse_lora_data(command):
            return SendTelemetry()
        return None
