import aiocomfoconnect.sensors
from aiocomfoconnect import ComfoConnect


class Ventilation:
    def __init__(self, comfoconnect_host, uuid, local_uuid, sensor_callback):
        self.comfoconnect = ComfoConnect(comfoconnect_host, uuid, sensor_callback=sensor_callback)
        self.local_uuid = local_uuid

    async def connect(self):
        await self.comfoconnect.connect(self.local_uuid)

    async def register_all_sensors(self):
        for key in aiocomfoconnect.sensors.SENSORS:
            await self.comfoconnect.register_sensor(aiocomfoconnect.sensors.SENSORS[key])

    async def keepalive(self):
        await self.comfoconnect.cmd_keepalive()

    async def disconnect(self):
        await self.comfoconnect.disconnect()
