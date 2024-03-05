class RudderController:
    def __init__(self):
        self.angle = 0

    def set_rudder_angle(self, angle):
        print("Setting rudder angle to", angle)
        self.angle = angle
