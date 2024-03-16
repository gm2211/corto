from api import SetDestination

from api.objects.commands.send_telemetry import SendTelemetry
from api.objects.commands.set_sail import SetSail
from api.objects.commands.turn_rudder import TurnRudder
from api.objects.units.gps_coord import GPSCoord
from boat.comms.lora.boat_radio import BoatRadio
from boat.controls.boat_attitude_controller import BoatAttitudeController
from boat.telemetry.nav_params_recorder import NavParamsRecorder


class CommandReceiver:
    def __init__(
            self,
            radio: BoatRadio,
            boat_controller: BoatAttitudeController,
            nav_params_recorder: NavParamsRecorder):
        self.radio: BoatRadio = radio
        self.cur_dest: GPSCoord = GPSCoord(0, 0)
        self.boat_controller: BoatAttitudeController = boat_controller
        self.nav_params_recorder = nav_params_recorder

        radio.register_callback(self.receive_command)

    def get_cur_destination(self) -> GPSCoord:
        return self.cur_dest

    def receive_command(self, command: str) -> None:
        if SetSail.can_parse_lora_data(command):
            set_sail = SetSail.deserialize_from_lora(command)
            self.boat_controller.set_sail_trim(set_sail.angle)
        elif TurnRudder.can_parse_lora_data(command):
            set_rudder = TurnRudder.deserialize_from_lora(command)
            self.boat_controller.set_rudder_angle(set_rudder.angle)
        elif SendTelemetry.can_parse_lora_data(command):
            serialized_telemetry = self.nav_params_recorder.get_cur_nav_params().serialize_for_lora()
            self.radio.send(serialized_telemetry)
            SendTelemetry()
        elif SetDestination.can_parse_lora_data(command):
            set_dest = SetDestination.deserialize_from_lora(command)
            self.cur_dest = set_dest.position
        return None
