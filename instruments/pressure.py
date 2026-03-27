import random
from .labjack import LabJackInstrument
from .visa import Channel, is_simulation_mode


class PressureSystem(LabJackInstrument):
    valve = Channel("Valve", unit="")
    pressure = Channel("Pressure", unit="Pa")

    def __init__(
        self,
        device_type: str = "T7",
        connection_type: str = "USB",
        identifier: str = "ANY",
        valve_dio: str = "FIO0",
        pressure_ain: str = "AIN0",
    ):
        """
        Args:
            device_type: LabJack device type (default: "T7")
            connection_type: Connection type (default: "USB")
            identifier: Device identifier (default: "ANY")
            valve_dio: Digital I/O channel for valve control (default: "FIO0")
            pressure_ain: Analog input channel for pressure sensor (default: "AIN0")
        """
        super().__init__(device_type, connection_type, identifier)
        self.valve_dio = valve_dio
        self.pressure_ain = pressure_ain

        # Simulation state
        self._sim_valve_state: int = 0
        self._sim_pressure: float = 101325.0  # Atmospheric pressure in Pa

    @valve.read
    def _read_valve(self) -> int:
        if is_simulation_mode():
            return self._sim_valve_state
        return int(self.read(self.valve_dio))

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
        self.write(self.valve_dio, float(state))

    @pressure.read
    def _read_pressure(self) -> float:
        if is_simulation_mode():
            return self._sim_pressure + random.gauss(0, 10)
        # Read voltage from pressure sensor and convert to Pa
        # Assuming a typical 0-10V sensor with 0-200kPa range
        voltage = self.read(self.pressure_ain)
        return voltage * 20000.0  # Convert V to Pa (adjust scaling as needed)
