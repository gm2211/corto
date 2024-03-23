from api.objects.commands.send_telemetry import SendTelemetry
from api.objects.commands.set_destination import SetDestination
from api.objects.commands.set_sail import SetSail
from api.objects.commands.set_throttle import SetThrottle
from api.objects.commands.turn_rudder import TurnRudder
from api.objects.units.gps_coord import GPSCoord
from lora.radio import Radio
from boat.controls.boat_attitude_controller import BoatAttitudeController
from boat.telemetry.nav_params_recorder import NavParamsRecorder


class CommandReceiver:
    def __init__(
            self,
            radio: Radio,
            boat_controller: BoatAttitudeController,
            nav_params_recorder: NavParamsRecorder):
        self.radio: Radio = radio
        self.cur_dest: GPSCoord = GPSCoord(0, 0)
        self.boat_controller: BoatAttitudeController = boat_controller
        self.nav_params_recorder = nav_params_recorder

    @staticmethod
    def create_and_register(
            radio: Radio,
            boat_controller: BoatAttitudeController,
            nav_params_recorder: NavParamsRecorder):
        receiver = CommandReceiver(radio, boat_controller, nav_params_recorder)
        radio.register_callback(receiver.__receive_command)
        return receiver

    def get_cur_destination(self) -> GPSCoord:
        return self.cur_dest

    def __receive_command(self, command: str) -> None:
        print(f"Received command: {command}")

        if SetSail.can_parse_lora_data(command):
            set_sail = SetSail.deserialize_from_lora(command)
            self.boat_controller.set_sail_trim(set_sail.angle)
            return None
        if TurnRudder.can_parse_lora_data(command):
            set_rudder = TurnRudder.deserialize_from_lora(command)
            self.boat_controller.set_rudder_angle(set_rudder.angle)
            return None
        if SendTelemetry.can_parse_lora_data(command):
            serialized_telemetry = self.nav_params_recorder.get_cur_nav_params().serialize_for_lora()
            self.radio.send(serialized_telemetry)
            SendTelemetry()
            return None
        if SetDestination.can_parse_lora_data(command):
            set_dest = SetDestination.deserialize_from_lora(command)
            self.cur_dest = set_dest.destination
            return None
        if SetThrottle.can_parse_lora_data(command):
            set_throttle = SetThrottle.deserialize_from_lora(command)
            self.boat_controller.set_motor_throttle(set_throttle.throttle / 100.0)
            return None
        print(f"Command was unknown: {command}")
