# comfoconnect-mqtt-bridge

`comfoconnect-mqtt-bridge` is a bridge for communicating between a Zehnder Comfoair Q350/450/600 ventilation system
and MQTT. You need a ComfoConnect LAN C device to interface with the unit.

It is built upon [aiocomfoconnect](https://github.com/michaelarnauts/aiocomfoconnect) and is compatible with Python 3.8 and higher.

## Installation

## Usage
Supported environment variables with defaults:
```
COMFOCONNECT_HOST=
COMFOCONNECT_BRIDGE_UUID=
COMFOCONNECT_LOCAL_UUID=
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_TOPIC=comfoconnect
MQTT_USER=
MQTT_PASSWORD=
MQTT_CLIENT_ID=
```
```shell
$ python main.py
```
