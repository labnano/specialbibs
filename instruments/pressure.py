from typing import Optional
from .visa import VisaInstrument, Channel, is_simulation_mode
import random


class PressureSystem(VisaInstrument):
    """Pressure control system with valve and pressure sensor"""

    valve = Channel("Valve", unit="")
    pressure = Channel("Pressure", unit="Pa")

    def __init__(self, gpib_address: int):
        super().__init__(f"GPIB0::{gpib_address}::INSTR")
        self._sim_valve_state: int = 0
        self._sim_pressure: float = 101325.0  # Atmospheric pressure in Pa

    @valve.read
    def _read_valve(self) -> int:
        if is_simulation_mode():
            return self._sim_valve_state
        return int(self.resource.query("VALVE?"))

    @valve.write
    def _set_valve(self, state: int):
        if is_simulation_mode():
            self._sim_valve_state = state
            # Simulate pressure change based on valve state
            if state == 1:
                self._sim_pressure = 50000.0 + random.gauss(0, 100)
            else:
                self._sim_pressure = 101325.0 + random.gauss(0, 50)
            return
        self.resource.write(f"VALVE {state}")

    @pressure.read
    def _read_pressure(self) -> float:
        if is_simulation_mode():
            return self._sim_pressure + random.gauss(0, 10)
        return float(self.resource.query("PRES?"))
