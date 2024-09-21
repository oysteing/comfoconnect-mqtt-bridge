import asyncio
from ast import literal_eval

import aiomqtt
import logging

from aiocomfoconnect import ComfoConnect

logger = logging.getLogger(__name__)


def to_mqtt_format(value):
    return str(value).lower() if isinstance(value, bool) else value


class Mqtt:
    def __init__(self, sensor_topic, control_topic, host, port, client_id, username, password):
        self.sensor_topic = sensor_topic
        self.control_topic = control_topic
        logger.info("Connecting to MQTT broker (host=%s, port=%d, client_id=%s, username=%s)", host, port, client_id,
                    username)
        self.client = aiomqtt.Client(hostname=host, port=port, identifier=client_id, username=username,
                                     password=password)

    def sensor_publish(self, sensor, value):
        logger.debug("Publishing %s = %s to MQTT broker", sensor.name, value)
        asyncio.create_task(self.client.publish(self.sensor_topic + "/" + sensor.name.replace(" ", ""), to_mqtt_format(value)))

    def publish(self, topic, value):
        logger.debug("Publishing %s = %s to MQTT broker", topic, value)
        asyncio.create_task(self.client.publish(topic, value))

    async def __aenter__(self):
        await self.client.__aenter__()
        await self.client.subscribe(self.control_topic + "/#")
        # async for message in self.client.messages:
        #     logger.info(message.topic)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def listen_control_topic(self, comfoconnect: ComfoConnect):
        async for message in self.client.messages:
            if message.topic.matches(self.control_topic + "/mode/get"):
                self.publish(self.control_topic + "/mode", await comfoconnect.get_mode())
            if message.topic.matches(self.control_topic + "/mode/set"):
                payload = message.payload.decode()
                if str(payload) == "auto":
                    logger.debug("Setting mode to auto")
                    await comfoconnect.set_mode("auto")
                elif str(payload) == "manual":
                    logger.debug("Setting mode to manual")
                    await comfoconnect.set_mode("manual")
                else:
                    logger.info("Invalid payload for %s: %s", message.topic, payload)
            if message.topic.matches(self.control_topic + "/comfocool_mode/get"):
                self.publish(self.control_topic + "/comfocool_mode", await comfoconnect.get_comfocool_mode())
            if message.topic.matches(self.control_topic + "/comfocool_mode/set"):
                payload = message.payload.decode()
                if str(payload) == "auto":
                    logger.debug("Setting Comfocool mode to auto")
                    await comfoconnect.set_comfocool_mode("auto")
                elif str(payload) == "off":
                    logger.debug("Setting Comfocool mode to off")
                    await comfoconnect.set_comfocool_mode("off")
                else:
                    logger.info("Invalid payload for %s: %s", message.topic, payload)
            if message.topic.matches(self.control_topic + "/speed/get"):
                self.publish(self.control_topic + "/speed", await comfoconnect.get_speed())
            if message.topic.matches(self.control_topic + "/speed/set"):
                payload = message.payload.decode()
                if str(payload) == "away":
                    logger.debug("Setting mode to away")
                    await comfoconnect.set_speed("away")
                elif str(payload) == "low":
                    logger.debug("Setting mode to low")
                    await comfoconnect.set_speed("low")
                elif str(payload) == "medium":
                    logger.debug("Setting mode to medium")
                    await comfoconnect.set_speed("medium")
                elif str(payload) == "high":
                    logger.debug("Setting mode to high")
                    await comfoconnect.set_speed("high")
                else:
                    logger.info("Invalid payload for %s: %s", message.topic, payload)