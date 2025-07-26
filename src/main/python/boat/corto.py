from dataclasses import dataclass

from api.objects.nav_params.boat_attitude import BoatAttitude
from api.objects.units.gps_coord import GPSCoord
from comms.command_receiver import CommandReceiver
from controls.boat_attitude_controller import BoatAttitudeController
from controls.servos_controller import ServosController
from navigation.navigator import Navigator
from telemetry.nav_params_recorder import NavParamsRecorder
from telemetry.sensors.gps_locator import GPSLocator
from telemetry.sensors.wind_vane import WindVane
from lora.radio import Radio


@dataclass
class Corto:
    boat_attitude_controller: BoatAttitudeController
    navigator: Navigator
    command_receiver: CommandReceiver
    latest_boat_attitude: BoatAttitude = None

    def run_loop(self) -> None:
        dest: GPSCoord = self.command_receiver.get_cur_destination()
        boat_attitude: BoatAttitude = self.navigator.compute_boat_attitude(dest)
        if boat_attitude != self.latest_boat_attitude:
            print(f"Boat attitude changed, was {self.latest_boat_attitude} and now {boat_attitude}")
            self.boat_attitude_controller.set_attitude(boat_attitude)
            self.latest_boat_attitude = boat_attitude


if __name__ == "__main__":
    nav_params_recorder = NavParamsRecorder()
    servos_controller = ServosController()
    boat_controller = BoatAttitudeController(servos_controller, nav_params_recorder)
    nav = Navigator(WindVane(), GPSLocator(), nav_params_recorder)
    radio = Radio()
    cmd_receiver = CommandReceiver.create_and_register(radio, boat_controller, nav_params_recorder)

    corto = Corto(boat_controller, nav, cmd_receiver)

    while True:
        corto.run_loop()
