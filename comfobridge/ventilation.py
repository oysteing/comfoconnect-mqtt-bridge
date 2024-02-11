import logging
from datetime import datetime

import aiocomfoconnect.sensors
from aiocomfoconnect import ComfoConnect

from comfobridge.measurement import Measurement
from comfobridge.reporting import Reporting

logger = logging.getLogger(__name__)


class Ventilation:
    def __init__(self, comfoconnect_host, uuid, local_uuid, sensor_callback, reporting: Reporting):
        self.comfoconnect = ComfoConnect(comfoconnect_host, uuid, sensor_callback=self.filter)
        self.local_uuid = local_uuid
        self.sensor_callback_fn = sensor_callback
        self.reporting = reporting

    async def connect(self):
        logger.info("Connecting to ComfoConnect...")
        await self.comfoconnect.connect(self.local_uuid)

    async def register_all_sensors(self):
        for key in aiocomfoconnect.sensors.SENSORS:
            logger.info("Registering sensor %s", key)
            await self.comfoconnect.register_sensor(aiocomfoconnect.sensors.SENSORS[key])

    async def register_sensors(self, sensors):
        for sensor in sensors:
            logger.info("Registering sensor %s", sensor)
            await self.comfoconnect.register_sensor(aiocomfoconnect.sensors.SENSORS[sensor])

    async def keepalive(self):
        logger.debug("Keeping alive...")
        await self.comfoconnect.cmd_keepalive()

    async def disconnect(self):
        logger.debug("Disconnecting from ComfoConnect...")
        await self.comfoconnect.disconnect()

    def filter(self, sensor, value):
        if self.reporting.should_report(Measurement(timestamp=datetime.now(), sensor=sensor, value=value)):
            self.sensor_callback_fn(sensor, value)
