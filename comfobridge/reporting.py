from aiocomfoconnect.sensors import UNIT_CELCIUS

from comfobridge.measurement import Measurement


class Reporting:
    def __init__(self, min_interval, max_interval, min_change):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.min_change = min_change
        self.last_measurement = {}

    def max_interval_exceeded(self, measurement: Measurement, last_measurement: Measurement):
        return (measurement.timestamp - last_measurement.timestamp).total_seconds() > self.max_interval

    def changed(self, measurement: Measurement, last_measurement: Measurement):
        if (isinstance(last_measurement.value, float)
                and isinstance(measurement.value, float)
                and measurement.sensor.unit == UNIT_CELCIUS):
            value_difference = (measurement.value - last_measurement.value) * 10
        elif isinstance(last_measurement.value, int) and isinstance(measurement.value, int):
            value_difference = measurement.value - last_measurement.value
        else:
            value_difference = self.min_change

        time_difference = (measurement.timestamp - last_measurement.timestamp).total_seconds()

        return time_difference >= self.min_interval and value_difference >= self.min_change

    def should_report(self, measurement: Measurement):
        last_measurement = self.last_measurement.get(measurement.sensor.id)

        if last_measurement is None or self.max_interval_exceeded(measurement, last_measurement) or self.changed(
                measurement, last_measurement):
            self.last_measurement[measurement.sensor.id] = measurement
            return True
        else:
            return False
