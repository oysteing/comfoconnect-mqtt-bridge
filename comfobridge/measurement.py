import datetime
from dataclasses import dataclass

from aiocomfoconnect.sensors import Sensor


@dataclass
class Measurement:
    timestamp: datetime
    sensor: Sensor
    value: any
