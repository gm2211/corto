from boat.comms.commands.command_receiver import CommandReceiver
from boat.controls.boat_attitude_controller import BoatAttitudeController
from boat.navigation.navigator import CourseCal
from boat.objects.boat_attitude import BoatAttitude
from boat.objects.gps_coord import GPSCoord


class Corto:
    def __init__(
            self,
            boat_attitude_controller: BoatAttitudeController,
            course_plotter: CourseCal,
            command_receiver: CommandReceiver):
        self.boat_attitude_controller = boat_attitude_controller
        self.course_plotter = course_plotter
        self.command_receiver = command_receiver

    def runLoop(self) -> None:
        dest: GPSCoord = self.command_receiver.get_cur_destination()
        boat_attitude: BoatAttitude = self.course_plotter.compute_boat_attitude(dest)
        self.boat_attitude_controller.set_attitude(boat_attitude)
        pass


if __name__ == "__main__":
    corto = Corto(None)

    while True:
        corto.runLoop()
        pass
