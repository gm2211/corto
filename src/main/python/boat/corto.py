from api.objects.nav_params.boat_attitude import BoatAttitude
from api.objects.units.gps_coord import GPSCoord
from boat.comms.command_receiver import CommandReceiver
from lora.radio import Radio
from boat.controls.boat_attitude_controller import BoatAttitudeController
from boat.controls.servos_controller import ServosController
from boat.navigation.navigator import Navigator
from boat.telemetry.nav_params_recorder import NavParamsRecorder
from boat.telemetry.sensors.gps_locator import GPSLocator
from boat.telemetry.sensors.wind_vane import WindVane


class Corto:
    def __init__(
            self,
            boat_attitude_controller: BoatAttitudeController,
            navigator: Navigator,
            command_receiver: CommandReceiver):
        self.boat_attitude_controller = boat_attitude_controller
        self.course_plotter = navigator
        self.command_receiver = command_receiver

    def run_loop(self) -> None:
        dest: GPSCoord = self.command_receiver.get_cur_destination()
        boat_attitude: BoatAttitude = self.course_plotter.compute_boat_attitude(dest)
        self.boat_attitude_controller.set_attitude(boat_attitude)
        pass


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
        pass
