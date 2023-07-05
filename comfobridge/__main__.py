import asyncio
import datetime
import os

from comfobridge.mqtt import Mqtt
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


class Engine:
    def __init__(self, config: Config):
        self.config: Config = config
        self.mqtt = Mqtt(config.mqtt_topic, config.mqtt_host, config.mqtt_port, config.mqtt_client_id, config.mqtt_user,
                         config.mqtt_password)
        self.ventilation = Ventilation(config.comfoconnect_host, config.comfoconnect_uuid,
                                       config.comfoconnect_local_uuid, self.mqtt.publish)

    async def start(self):
        await self.mqtt.connect()
        await self.ventilation.connect()
        await self.ventilation.register_all_sensors()

    async def run(self):
        while True:
            await asyncio.sleep(KEEPALIVE_TIMEOUT.seconds)
            await self.ventilation.keepalive()

    async def stop(self):
        await self.ventilation.disconnect()


async def main():
    engine = Engine(Config())
    await engine.start()
    await engine.run()
    await engine.stop()


if __name__ == '__main__':
    asyncio.run(main())
