import aiocomfoconnect.sensors
from aiocomfoconnect import ComfoConnect


class Ventilation:
    def __init__(self, comfoconnect_host, uuid, local_uuid, sensor_callback):
        self.comfoconnect = ComfoConnect(comfoconnect_host, uuid, sensor_callback=self.filter_unchanged)
        self.local_uuid = local_uuid
        self.sensor_callback_fn = sensor_callback
        self.last_value = {}

    async def connect(self):
        await self.comfoconnect.connect(self.local_uuid)

    async def register_all_sensors(self):
        for key in aiocomfoconnect.sensors.SENSORS:
            await self.comfoconnect.register_sensor(aiocomfoconnect.sensors.SENSORS[key])

    async def register_sensors(self, sensors):
        for sensor in sensors:
            await self.comfoconnect.register_sensor(aiocomfoconnect.sensors.SENSORS[sensor])

    async def keepalive(self):
        await self.comfoconnect.cmd_keepalive()

    async def disconnect(self):
        await self.comfoconnect.disconnect()

    def filter_unchanged(self, sensor, value):
        last_value = self.last_value.get(sensor.name)

        if type(last_value) != type(value) or abs((last_value - value) / last_value) >= 0.02:
            self.last_value[sensor.name] = value
            self.sensor_callback_fn(sensor, value)
