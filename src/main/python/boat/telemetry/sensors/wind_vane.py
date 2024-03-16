from pyformance.meters import Histogram

from api.objects.units.angle import Angle


class WindVane:
    def __init__(self):
        self.wind_vane_data: Histogram = Histogram(size=10)
        self.wind_vane_data.add(self.wind_vane.get_true_wind().degrees)

    def get_true_wind(self) -> Angle:
        # TODO: Add sensor reading to histogram
        return Angle(self.wind_vane_data.get_snapshot().get_median())
