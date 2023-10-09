from datetime import datetime

import aiocomfoconnect.sensors
from aiocomfoconnect import ComfoConnect

from comfobridge.measurement import Measurement
from comfobridge.reporting import Reporting


class Ventilation:
    def __init__(self, comfoconnect_host, uuid, local_uuid, sensor_callback, reporting: Reporting):
        self.comfoconnect = ComfoConnect(comfoconnect_host, uuid, sensor_callback=self.filter)
        self.local_uuid = local_uuid
        self.sensor_callback_fn = sensor_callback
        self.reporting = reporting

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

    def filter(self, sensor, value):
        if self.reporting.should_report(Measurement(timestamp=datetime.now(), sensor=sensor, value=value)):
            self.sensor_callback_fn(sensor, value)
