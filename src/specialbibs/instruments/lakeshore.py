from .instruments import VisaInstrument, Channel
from enum import Enum

class L330(VisaInstrument):
    """LakeShore 330"""

    class Ranges(Enum):
        OFF = 0
        LOW = 1
        MEDIUM = 2
        HIGH = 3

    temperature = Channel("Temperature", unit="℃")
    setpoint = Channel("Setpoint", unit="℃")
    range = Channel("Range", unit="")

    def __init__(self, gpib_address: int,):
        super().__init__(f"GPIB0::{gpib_address}::INSTR")

    
    @temperature.read
    def _read_temperature(self) -> float:
        response = self.resource.query("KRDG?").strip()
        temp = float(response)
        return temp
    
    @setpoint.read
    def _read_setpoint(self) -> float:
        response = self.resource.query("SETP?").strip()
        setp = float(response)
        return setp
    
    @setpoint.write
    def _set_setpoint(self, value: float):
        command = f":SETP {value}"
        self.resource.write(command)

    @range.read
    def _read_range(self) -> int:
        response = self.resource.query("RANG?").strip()
        rng = int(response)
        return rng
    
    @range.write
    def _set_range(self, range: Ranges):
        command = f":RANG {range.value}"
        self.resource.write(command)