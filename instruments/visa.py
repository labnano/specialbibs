from __future__ import annotations
from typing import Any, Callable, Optional, TYPE_CHECKING
import weakref

if TYPE_CHECKING:
    from pyvisa.resources import Resource

# Global simulation mode flag
_simulation_mode = False


def set_simulation_mode(enabled: bool = True):
    """Enable or disable simulation mode globally"""
    global _simulation_mode
    _simulation_mode = enabled


def is_simulation_mode() -> bool:
    """Check if simulation mode is enabled"""
    return _simulation_mode


# Lazy load pyvisa only when needed
_rm = None


def _get_resource_manager():
    global _rm
    if _rm is None:
        from pyvisa import ResourceManager

        _rm = ResourceManager()
    return _rm


class Instrument:
    def on_load(self):
        raise NotImplementedError

    def before_measure(self):
        raise NotImplementedError


class VisaInstrument(Instrument):
    def __init__(self, address: str):
        super().__init__()
        self.address: str = address
        self.resource: Optional["Resource"] = None

    def connect(self):
        if not _simulation_mode:
            self.resource = _get_resource_manager().open_resource(self.address)


class Channel:
    def __init__(self, name: str, unit: Optional[str] = None):
        self.name = name
        self.unit = unit or name[0].upper()
        self._cache = weakref.WeakKeyDictionary()
        self._reader: Optional[Callable] = None
        self._writer: Optional[Callable] = None

    def __get__(self, instance: Optional[Any], owner: Optional[type] = None):
        if instance is None:
            return self

        if instance not in self._cache:
            self._cache[instance] = _InstrumentChannel(self, instance)

        return self._cache[instance]

    def read(self, func: Callable):
        self._reader = func
        return func

    def write(self, func: Callable):
        self._writer = func
        return func


class _InstrumentChannel:
    def __init__(self, channel: Channel, instance: Any):
        self.channel: Channel = channel
        self._instance: Any = instance

    def get(self):
        if self.channel._reader is None:
            raise AttributeError(
                "No getter defined for channel {} in instrument {}".format(
                    self.channel.name, self._instance.__class__.__name__
                )
            )
        return self.channel._reader(self._instance)

    def set(self, *args, **kwargs):
        if self.channel._writer is None:
            raise AttributeError(
                "No setter defined for channel {} in instrument {}".format(
                    self.channel.name, self._instance.__class__.__name__
                )
            )
        return self.channel._writer(self._instance, *args, **kwargs)

    def __call__(self, *args):
        if args:
            return self.set(*args)
        return self.get()

    @property
    def value(self):
        return self.get()

    @value.setter
    def value(self, val):
        self.set(val)


## Example usage:
# class MyInstrument(VisaInstrument):
#     voltage = Channel("Voltage", unit="V")

#     @voltage.read
#     def _read_voltage(self):
#         return self.resource.query("MEAS:VOLT?")
#
#     @voltage.write
#     def _set_voltage(self, value):
#         self.resource.write(f"VOLT {value}")
#
#
# instrument = MyInstrument("GPIB::1")
# instrument.connect()
# instrument.voltage.set(5)
# print(instrument.voltage.get())
