from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING
from .visa import Instrument, Channel, is_simulation_mode

if TYPE_CHECKING:
    from labjack import ljm

# Lazy load labjack-ljm only when needed
_ljm = None


def _get_ljm():
    global _ljm
    if _ljm is None:
        from labjack import ljm

        _ljm = ljm
    return _ljm


class LabJackInstrument(Instrument):
    """Base class for LabJack instruments using the LJM library"""

    def __init__(
        self,
        device_type: str = "ANY",
        connection_type: str = "ANY",
        identifier: str = "ANY",
    ):
        """
        Initialize a LabJack instrument.

        Args:
            device_type: Device type ("T7", "T4", "T8", or "ANY")
            connection_type: Connection type ("USB", "ETHERNET", "WIFI", or "ANY")
            identifier: Serial number, IP address, or "ANY"
        """
        super().__init__()
        self.device_type = device_type
        self.connection_type = connection_type
        self.identifier = identifier
        self.handle: Optional[int] = None

    def connect(self):
        """Connect to the LabJack device"""
        if not is_simulation_mode():
            ljm = _get_ljm()
            self.handle = ljm.openS(
                self.device_type, self.connection_type, self.identifier
            )

    def disconnect(self):
        """Disconnect from the LabJack device"""
        if self.handle is not None and not is_simulation_mode():
            ljm = _get_ljm()
            ljm.close(self.handle)
            self.handle = None

    def read(self, name: str) -> float:
        """Read a single value from the device"""
        if is_simulation_mode():
            return 0.0
        ljm = _get_ljm()
        return ljm.eReadName(self.handle, name)

    def write(self, name: str, value: float):
        """Write a single value to the device"""
        if not is_simulation_mode():
            ljm = _get_ljm()
            ljm.eWriteName(self.handle, name, value)

    def read_multiple(self, names: list[str]) -> list[float]:
        """Read multiple values from the device"""
        if is_simulation_mode():
            return [0.0] * len(names)
        ljm = _get_ljm()
        return ljm.eReadNames(self.handle, len(names), names)

    def write_multiple(self, names: list[str], values: list[float]):
        """Write multiple values to the device"""
        if not is_simulation_mode():
            ljm = _get_ljm()
            ljm.eWriteNames(self.handle, len(names), names, values)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
