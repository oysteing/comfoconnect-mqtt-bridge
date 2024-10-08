import asyncio
import datetime
import logging
import os
import json
from asyncio import create_task
from enum import Enum

from comfobridge.mqtt import Mqtt
from comfobridge.reporting import Reporting
from comfobridge.ventilation import Ventilation

KEEPALIVE_TIMEOUT = datetime.timedelta(seconds=60)

logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self.comfoconnect_host = os.getenv("COMFOCONNECT_HOST")
        self.comfoconnect_uuid = os.getenv("COMFOCONNECT_BRIDGE_UUID")
        self.comfoconnect_local_uuid = os.getenv("COMFOCONNECT_LOCAL_UUID")
        self.mqtt_host = os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.mqtt_sensor_topic = os.getenv("MQTT_SENSOR_TOPIC", "comfoconnect/sensor")
        self.mqtt_control_topic = os.getenv("MQTT_CONTROL_TOPIC", "comfoconnect/control")
        self.mqtt_user = os.getenv("MQTT_USER", "")
        self.mqtt_password = os.getenv("MQTT_PASSWORD", "")
        self.mqtt_client_id = os.getenv("MQTT_CLIENT_ID", "")
        self.sensors = os.getenv("COMFOCONNECT_SENSORS")
        self.min_reporting_interval = int(os.getenv("COMFOBRIDGE_MIN_REPORTING_INTERVAL", 60))
        self.max_reporting_interval = int(os.getenv("COMFOBRIDGE_MAX_REPORTING_INTERVAL", 3600))
        self.min_reporting_change = float(os.getenv("COMFOBRIDGE_MIN_REPORTING_CHANGE", 2))
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()


class Engine:
    def __init__(self, config: Config):
        self.config: Config = config
        self.mqtt = Mqtt(config.mqtt_sensor_topic, config.mqtt_host, config.mqtt_port, config.mqtt_client_id,
                         config.mqtt_user, config.mqtt_password)
        reporting = Reporting(config.min_reporting_interval, config.max_reporting_interval, config.min_reporting_change)
        self.ventilation = Ventilation(config.comfoconnect_host, config.comfoconnect_uuid,
                                       config.comfoconnect_local_uuid, self.mqtt.sensor_publish, reporting)

    async def __aenter__(self):
        await self.mqtt.__aenter__()
        await self.ventilation.connect()
        if self.config.sensors is None:
            await self.ventilation.register_all_sensors()
        else:
            await self.ventilation.register_sensors([int(sensor) for sensor in self.config.sensors.split(",")])
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.mqtt.__aexit__(exc_type, exc_val, exc_tb)
        await self.ventilation.disconnect()

    async def subscribe_topics(self):
        topic_base = self.config.mqtt_control_topic + "/"
        topic_wildcard_get = topic_base + "+/get"
        topic_wildcard_set = topic_base + "+/set"
        await self.mqtt.client.subscribe(topic_wildcard_get)
        await self.mqtt.client.subscribe(topic_wildcard_set)
        async for message in self.mqtt.client.messages:
            function = message.topic.value[len(topic_base):-len("/get")]
            payload = message.payload.decode()
            try:
                if message.topic.matches(topic_wildcard_get):
                    value = await self.get_value(function)
                    self.mqtt.publish(topic_base + function, value)
                elif message.topic.matches(topic_wildcard_set):
                    await self.set_value(function, payload)
                else:
                    raise TopicNotSupportedError(function)
            except TopicNotSupportedError:
                logger.error("Topic %s is not supported", message.topic)
            except (KeyError, ValueError):
                logger.exception("Invalid payload '%s' for topic '%s'", payload, message.topic)

    async def get_value(self, function):
        match function:
            case "mode":
                return await self.ventilation.comfoconnect.get_mode()
            case "speed":
                return await self.ventilation.comfoconnect.get_speed()
            case "bypass":
                return await self.ventilation.comfoconnect.get_bypass()
            case "balancemode":
                return await self.ventilation.comfoconnect.get_balance_mode()
            case "boost":
                return await self.ventilation.comfoconnect.get_boost()
            case "away":
                return await self.ventilation.comfoconnect.get_away()
            case "comfocoolmode":
                return await self.ventilation.comfoconnect.get_comfocool_mode()
            case "temperatureprofile":
                return await self.ventilation.comfoconnect.get_temperature_profile()
            case "temperaturepassive":
                return await self.ventilation.comfoconnect.get_sensor_ventmode_temperature_passive()
            case "humiditycomfort":
                return await self.ventilation.comfoconnect.get_sensor_ventmode_humidity_comfort()
            case "humidityprotection":
                return await self.ventilation.comfoconnect.get_sensor_ventmode_humidity_protection()
            case _:
                raise TopicNotSupportedError(function)

    async def set_value(self, function, payload):
        state = payload
        timeout = None
        unit = None

        if '{' in payload:
            logger.debug("Payload looks like JSON")
            state, timeout, unit = parse_json(payload)

        match function:
            case "mode":
                await self.ventilation.comfoconnect.set_mode(state)
            case "speed":
                await self.ventilation.comfoconnect.set_speed(state)
            case "bypass":
                await self.ventilation.comfoconnect.set_bypass(state, to_seconds(timeout, unit))
            case "balancemode":
                await self.ventilation.comfoconnect.set_balance_mode(state, to_seconds(timeout, unit))
            case "boost":
                await self.ventilation.comfoconnect.set_boost(state, to_seconds(timeout, unit))
            case "away":
                await self.ventilation.comfoconnect.set_away(state, to_seconds(timeout, unit))
            case "comfocoolmode":
                await self.ventilation.comfoconnect.set_comfocool_mode(state, to_seconds(timeout, unit))
            case "temperatureprofile":
                await self.ventilation.comfoconnect.set_temperature_profile(state, to_seconds(timeout, unit))
            case "temperaturepassive":
                await self.ventilation.comfoconnect.set_sensor_ventmode_temperature_passive(state)
            case "humiditycomfort":
                await self.ventilation.comfoconnect.set_sensor_ventmode_humidity_comfort(state)
            case "humidityprotection":
                await self.ventilation.comfoconnect.set_sensor_ventmode_humidity_protection(state)
            case _:
                raise TopicNotSupportedError(function)

    async def run(self):
        while True:
            await asyncio.sleep(KEEPALIVE_TIMEOUT.seconds)
            await self.ventilation.keepalive()

def parse_json(payload):
    payload_object = json.loads(payload)
    timeout = None
    unit = None

    if "state" in payload_object:
        state = payload_object["state"]
    else:
        raise KeyError("JSON payload is missing mandatory key 'state'")

    if "timeout" in payload_object:
        timeout = int(payload_object["timeout"])

    if "unit" in payload_object:
        unit = str.lower(payload_object["unit"])
        if unit in ("minutes", "minute", "min", "m"):
            unit = Unit.MINUTE
        elif unit in ("hours", "hour", "h"):
            unit = Unit.HOUR
        elif unit in ("days", "day", "d"):
            unit = Unit.DAY
        else:
            raise ValueError("Unsupported unit: %s", unit)

    return state, timeout, unit

def to_seconds(timeout, unit):
    if timeout is None:
        return -1

    match unit:
        case Unit.MINUTE:
            return timeout * 60
        case Unit.HOUR:
            return timeout * 60 * 60
        case Unit.DAY:
            return timeout * 60 * 60 * 24
        case None:
            return timeout * 60 * 60

async def main():
    config = Config()
    logging.basicConfig(level=config.log_level)
    async with Engine(config) as engine:
        create_task(engine.subscribe_topics())
        await engine.run()

class TopicNotSupportedError(Exception):
    pass

class Unit(Enum):
    MINUTE = "minute"
    DAY = "day"
    HOUR = "hour"

if __name__ == '__main__':
    asyncio.run(main())
