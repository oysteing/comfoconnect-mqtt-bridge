# comfoconnect-mqtt-bridge

`comfoconnect-mqtt-bridge` is a bridge for communicating between a Zehnder Comfoair Q350/450/600 ventilation system
and MQTT. You need a ComfoConnect LAN C device to interface with the unit.

It is built upon [aiocomfoconnect](https://github.com/michaelarnauts/aiocomfoconnect) and is compatible with Python 3.8
and higher.

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
COMFOCONNECT_SENSORS=None (all sensors)
COMFOBRIDGE_MIN_REPORTING_INTERVAL=60
COMFOBRIDGE_MAX_REPORTING_INTERVAL=3600
COMFOBRIDGE_MIN_REPORTING_CHANGE=0.2
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_SENSOR_TOPIC=comfoconnect/sensor
MQTT_CONTROL_TOPIC=comfoconnect/control
MQTT_USER=
MQTT_PASSWORD=
MQTT_CLIENT_ID=
MQTT_RETAIN=false
LOG_LEVEL=info
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
      COMFOCONNECT_BRIDGE_UUID: '00000000000000000000000000000000'
      COMFOCONNECT_LOCAL_UUID: '00000000000000000000000000000001'
      COMFOCONNECT_SENSORS: 221,274,275,276,290,291,292,294
      COMFOBRIDGE_MIN_REPORTING_INTERVAL=60
      COMFOBRIDGE_MAX_REPORTING_INTERVAL=3600
      COMFOBRIDGE_MIN_REPORTING_CHANGE=0.2
      MQTT_HOST: mqtt
      MQTT_CLIENT_ID: comfoconnect
      MQTT_USER: comfoconnect
      MQTT_PASSWORD: mypassword
      MQTT_RETAIN: true
      LOG_LEVEL: DEBUG
```

## Supported topics

### Sensor data

Readings from configured sensors will be published on the endpoint defined by MQTT_SENSOR_TOPIC, postfixed by the sensor
name. Example: `comfoconnect/sensor/ExtractAirTemperature 22.5`

### Ventilation control

For each function, the current value can be requested by publishing to the `/get` topic, payload is not required. The
current value will then be written out to the function topic. Changing the control value is done by posting the new
value to the `/set` topic.

Example with `MQTT_CONTROL_TOPIC=comfoconnect/control`:

```
comfoconnect/control/mode/get (null)
comfoconnect/control/mode auto
comfoconnect/control/mode/set manual
comfoconnect/control/mode/get (null)
comfoconnect/control/mode manual
```

#### Available functions

The following functions and values (in parenthesis) are supported:

* `mode`: Set the ventilation mode (auto / manual)
* `speed`: Set the ventilation speed (away / low / medium / high)
* `bypass`: Set the bypass mode (auto / on / off)
* `balancemode`: Set the ventilation balance mode (balance / supply only / exhaust only)
* `boost`: Activate boost mode (true / false)
* `away`: Activate away mode (true / false)
* `comfocoolmode`: Set the comfocool mode (auto / off)
* `temperatureprofile`: Set the temperature profile (warm / normal / cool)
* `temperaturepassive`: Configure sensor based ventilation mode - temperature passive (auto / on / off)
* `humiditycomfort`: Configure sensor based ventilation mode - humidity comfort (auto / on / off)
* `humidityprotection`: Configure sensor based ventilation mode - humidity protection (auto / on / off)

As alternative to just set a raw state, it is possible to send a JSON-payload to the set topic.
This provides the possibility to set a configurable timeout for the functions
`bypass`, `balancemode`, `boost`, `away`, `comfocoolmode`, and `temperatureprofile`.
The payload has the following key and values (in paranthesis):
* `state`: Mandatory - Set the desired value of the used function (any value mentioned above for the corresponding function)
* `timeout`: Optional - set the desired value for the timeout, default is indefinite (any (integer) number)
* `unit`: Optional - set the desired unit for the timeout-value, default is hour ((minutes / minute / min / m) / (hours / hour / h) / (days / day / d)))

Example payload:
```
{
	"state": true,
	"timeout": 1,
	"unit": "day"
}
```
