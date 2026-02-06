import asyncio

import aiomqtt
import logging

logger = logging.getLogger(__name__)


def to_mqtt_format(value):
    return str(value).lower() if isinstance(value, bool) else value


class Mqtt:
    def __init__(self, sensor_topic, host, port, client_id, username, password, retain):
        self.sensor_topic = sensor_topic
        self.retain = retain
        self.host = host
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.is_connected = False
        logger.info("Connecting to MQTT broker (host=%s, port=%d, client_id=%s, username=%s)", host, port, client_id,
                    username)
        self.client = aiomqtt.Client(hostname=host, port=port, identifier=client_id, username=username,
                                     password=password)

    async def _publish_with_retry(self, topic, payload, retain=False, max_retries=3):
        """Publish with automatic retry and reconnection handling"""
        for attempt in range(max_retries):
            try:
                if not self.is_connected:
                    logger.warning("MQTT client not connected, attempting to reconnect...")
                    await self._reconnect()
                
                await self.client.publish(topic, payload, retain=retain)
                return
            except (aiomqtt.MqttCodeError, aiomqtt.MqttError) as e:
                logger.error("MQTT publish failed (attempt %d/%d): %s", attempt + 1, max_retries, e)
                self.is_connected = False
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("Failed to publish after %d attempts: topic=%s", max_retries, topic)
            except Exception as e:
                logger.exception("Unexpected error during MQTT publish: %s", e)
                break

    async def _reconnect(self):
        """Attempt to reconnect to MQTT broker"""
        try:
            logger.info("Reconnecting to MQTT broker...")
            # Close existing connection if any
            try:
                await self.client.__aexit__(None, None, None)
            except Exception:
                pass
            
            # Create new client and connect
            self.client = aiomqtt.Client(
                hostname=self.host, 
                port=self.port, 
                identifier=self.client_id, 
                username=self.username,
                password=self.password
            )
            await self.client.__aenter__()
            self.is_connected = True
            logger.info("Successfully reconnected to MQTT broker")
        except Exception as e:
            logger.error("Failed to reconnect to MQTT broker: %s", e)
            self.is_connected = False
            raise

    def sensor_publish(self, sensor, value):
        logger.debug("Publishing %s = %s to MQTT broker", sensor.name, value)
        asyncio.create_task(
            self._publish_with_retry(
                self.sensor_topic + "/" + sensor.name.replace(" ", ""), 
                to_mqtt_format(value), 
                retain=self.retain
            )
        )

    def publish(self, topic, value):
        logger.debug("Publishing %s = %s to MQTT broker", topic, value)
        asyncio.create_task(self._publish_with_retry(topic, value))

    async def __aenter__(self):
        await self.client.__aenter__()
        self.is_connected = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.is_connected = False
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
