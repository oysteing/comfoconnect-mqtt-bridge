import asyncio
import datetime
import logging
import os

from comfobridge.mqtt import Mqtt
from comfobridge.reporting import Reporting
from comfobridge.ventilation import Ventilation

KEEPALIVE_TIMEOUT = datetime.timedelta(seconds=60)


class Config:
    def __init__(self):
        self.comfoconnect_host = os.getenv("COMFOCONNECT_HOST")
        self.comfoconnect_uuid = os.getenv("COMFOCONNECT_BRIDGE_UUID")
        self.comfoconnect_local_uuid = os.getenv("COMFOCONNECT_LOCAL_UUID")
        self.mqtt_host = os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.mqtt_topic = os.getenv("MQTT_TOPIC", "comfoconnect")
        self.mqtt_user = os.getenv("MQTT_USER", "")
        self.mqtt_password = os.getenv("MQTT_PASSWORD", "")
        self.mqtt_client_id = os.getenv("MQTT_CLIENT_ID", "")
        self.sensors = os.getenv("COMFOCONNECT_SENSORS")
        self.min_reporting_interval = os.getenv("COMFOBRIDGE_MIN_REPORTING_INTERVAL", 60)
        self.max_reporting_interval = os.getenv("COMFOBRIDGE_MAX_REPORTING_INTERVAL", 3600)
        self.min_reporting_change = os.getenv("COMFOBRIDGE_MIN_REPORTING_CHANGE", 2)
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()


class Engine:
    def __init__(self, config: Config):
        self.config: Config = config
        self.mqtt = Mqtt(config.mqtt_topic, config.mqtt_host, config.mqtt_port, config.mqtt_client_id, config.mqtt_user,
                         config.mqtt_password)
        reporting = Reporting(config.min_reporting_interval, config.max_reporting_interval, config.min_reporting_change)
        self.ventilation = Ventilation(config.comfoconnect_host, config.comfoconnect_uuid,
                                       config.comfoconnect_local_uuid, self.mqtt.publish, reporting)

    async def start(self):
        await self.mqtt.connect()
        await self.ventilation.connect()
        if self.config.sensors is None:
            await self.ventilation.register_all_sensors()
        else:
            await self.ventilation.register_sensors([int(sensor) for sensor in self.config.sensors.split(",")])

    async def run(self):
        while True:
            await asyncio.sleep(KEEPALIVE_TIMEOUT.seconds)
            await self.ventilation.keepalive()

    async def stop(self):
        await self.ventilation.disconnect()


async def main():
    config = Config()
    logging.basicConfig(level=config.log_level)
    engine = Engine(config)
    await engine.start()
    await engine.run()
    await engine.stop()


if __name__ == '__main__':
    asyncio.run(main())
