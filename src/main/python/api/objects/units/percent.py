class Percent:
    def __init__(self, value: int):
        assert 0 <= value <= 100, f"Percent must be between 0 and 100, not {value}"
        self.value = value

    def __str__(self):
        return f"{self.value}%"
