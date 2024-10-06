import asyncio
import datetime
import logging
import os
import json
from asyncio import create_task

from attr.converters import to_bool

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
            except ValueError:
                logger.error("Invalid payload '%s' for topic '%s'", payload, message.topic)

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

        # Some functions offer explicit setting of timeouts, so check if payload contains one, otherwise set 1h as default
        # JSON payload can be extended by a unit for the timeout. Valid values are (default is h):
        # minute, min, m
        # hour, h
        # day, d
        stateToSet = ''
        timeoutInHours = 1.0        # timeout[h]
        unit = 'h'
        isJsonPayload = True
        stateToSet = payload

        if payload != 'true' and payload != 'false':
            try:
                jsonPayload = json.loads(payload)
            except ValueError:
                isJsonPayload = False
        else:
            isJsonPayload = False

        if isJsonPayload:

            # ensure case-insensitivity
            jsonPayloadTmp = jsonPayload.copy()

            for key in jsonPayload:
                value = jsonPayloadTmp[key]
                if type(value) is str:
                    if key != key.lower():
                        jsonPayloadTmp[key.lower()] = value
                        jsonPayloadTmp.pop(key)
                if type(value) is str:
                    jsonPayloadTmp[key.lower()] = jsonPayloadTmp[key.lower()].lower()

            jsonPayload = jsonPayloadTmp.copy()

            if 'state' in jsonPayload:
                stateToSet = jsonPayload['state']
            else:
                logger.error(f'Payload: {jsonPayload} does not contain a state which is mandatory.')

            if 'duration' in jsonPayload:
                value = jsonPayload['duration']
                try:
                    timeoutInHours = float(value)
                except ValueError:
                    logger.error(f'Duration-Value: {value} is not castable to int.')
            elif 'timeout' in jsonPayload:
                value = jsonPayload['timeout']
                try:
                    timeoutInHours = float(value)
                except ValueError:
                    logger.error(f'Timeout-Value: {value} is not castable to int.')

            if 'unit' in jsonPayload:
                unitMinute = ('minute', 'min', 'm')
                unitHour = ('hour', 'h')
                unitDay = ('day', 'd')
                unit = jsonPayload['unit']
                if unit in unitMinute:
                    timeoutInHours = timeoutInHours/60
                elif unit in unitHour:
                    timeoutInHours = timeoutInHours
                elif unit in unitDay:
                    timeoutInHours = timeoutInHours*24
                else:
                    logger.error(f'Duration/Timout unit: {unit} is not a valid value.')


        match function:
            case "mode":
                await self.ventilation.comfoconnect.set_mode(stateToSet)
            case "speed":
                await self.ventilation.comfoconnect.set_speed(stateToSet)
            case "bypass":
                await self.ventilation.comfoconnect.set_bypass(stateToSet, int(timeoutInHours))
            case "balancemode":
                await self.ventilation.comfoconnect.set_balance_mode(stateToSet, int(timeoutInHours))
            case "boost":
                await self.ventilation.comfoconnect.set_boost(to_bool(stateToSet), int(timeoutInHours*3600))
            case "away":
                await self.ventilation.comfoconnect.set_away(to_bool(stateToSet), int(timeoutInHours*3600))
            case "comfocoolmode":
                await self.ventilation.comfoconnect.set_comfocool_mode(stateToSet, int(timeoutInHours))
            case "temperatureprofile":
                await self.ventilation.comfoconnect.set_temperature_profile(stateToSet, int(timeoutInHours))
            case "temperaturepassive":
                await self.ventilation.comfoconnect.set_sensor_ventmode_temperature_passive(stateToSet)
            case "humiditycomfort":
                await self.ventilation.comfoconnect.set_sensor_ventmode_humidity_comfort(stateToSet)
            case "humidityprotection":
                await self.ventilation.comfoconnect.set_sensor_ventmode_humidity_protection(stateToSet)
            case _:
                raise TopicNotSupportedError(function)

    async def run(self):
        while True:
            await asyncio.sleep(KEEPALIVE_TIMEOUT.seconds)
            await self.ventilation.keepalive()


class TopicNotSupportedError(Exception):
    pass


async def main():
    config = Config()
    logging.basicConfig(level=config.log_level)
    async with Engine(config) as engine:
        create_task(engine.subscribe_topics())
        await engine.run()


if __name__ == '__main__':
    asyncio.run(main())
