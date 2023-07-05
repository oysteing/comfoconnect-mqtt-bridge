import asyncio

import aiomqtt


def to_mqtt_format(value):
    return str(value).lower() if isinstance(value, bool) else value


class Mqtt:
    def __init__(self, topic, host, port, client_id, username, password):
        self.topic = topic
        self.client = aiomqtt.Client(hostname=host, port=port, client_id=client_id, username=username,
                                     password=password)

    def publish(self, sensor, value):
        # print(f"{sensor.name} = {value}")
        asyncio.create_task(self.client.publish(self.topic + "/" + sensor.name.replace(" ", ""), to_mqtt_format(value)))

    async def connect(self):
        await self.client.connect()

    async def disconnect(self):
        await self.client.disconnect()
