# comfoconnect-mqtt-bridge

`comfoconnect-mqtt-bridge` is a bridge for communicating between a Zehnder Comfoair Q350/450/600 ventilation system
and MQTT. You need a ComfoConnect LAN C device to interface with the unit.

It is built upon [aiocomfoconnect](https://github.com/michaelarnauts/aiocomfoconnect) and is compatible with Python 3.8 and higher.

## Installation
```shell
$ pip install git+https://github.com/oysteing/comfoconnect-mqtt-bridge
```

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
$ python -m comfobridge
```

### Docker
Build a Docker container from the Dockerfile (pre-built image currently not published):
```
docker build . -t comfoconnect-mqtt-bridge
```
Example docker-compose:
```
services:
  comfobridge:
    image: comfoconnect-mqtt-bridge
    environment:
      COMFOCONNECT_HOST: 192.168.1.1
      COMFOCONNECT_BRIDGE_UUID: 00000000000000000000000000000000
      COMFOCONNECT_LOCAL_UUID: 00000000000000000000000000000001
      MQTT_HOST: mqtt
      MQTT_CLIENT_ID: comfoconnect
      MQTT_USER: comfoconnect
      MQTT_PASSWORD: mypassword
```