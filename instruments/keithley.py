from typing import Optional
from .visa import VisaInstrument, Channel, is_simulation_mode
import random


class K2400(VisaInstrument):
    """Keithley 2400 SourceMeter"""

    voltage = Channel("Voltage", unit="V")
    current = Channel("Current", unit="A")

    def __init__(self, gpib_address: int):
        super().__init__(f"GPIB0::{gpib_address}::INSTR")
        self._sim_voltage: float = 0.0
        self._sim_current: float = 0.0

    @voltage.read
    def _read_voltage(self) -> float:
        if is_simulation_mode():
            # Simulate with small noise
            return self._sim_voltage + random.gauss(0, 0.001)
        return float(self.resource.query(":MEAS:VOLT?"))

    @voltage.write
    def _set_voltage(self, value: float):
        if is_simulation_mode():
            self._sim_voltage = value
            # Simulate current based on a simple resistance model
            self._sim_current = value / 1000.0 + random.gauss(0, 1e-6)
            return
        self.resource.write(f":SOUR:VOLT {value}")

    @current.read
    def _read_current(self) -> float:
        if is_simulation_mode():
            return self._sim_current + random.gauss(0, 1e-7)
        return float(self.resource.query(":MEAS:CURR?"))

    @current.write
    def _set_current(self, value: float):
        if is_simulation_mode():
            self._sim_current = value
            return
        self.resource.write(f":SOUR:CURR {value}")
