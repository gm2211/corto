class Corto:
    def __init__(self, boat_asset_controller):
        self.boat_asset_controller = boat_asset_controller

    def runLoop(self) -> None:
        pass


if __name__ == "__main__":
    corto = Corto(None)
    while True:
        corto.runLoop()
        pass
