from __future__ import annotations
from typing import Any, Callable, Optional, Tuple, Union, overload
from pyvisa import ResourceManager
from pyvisa.resources import MessageBasedResource
import weakref
import os
if os.name == 'nt':
    os.add_dll_directory(r"C:\\Program Files\\Keysight\\IO Libraries Suite\\bin")

rm = ResourceManager()
is_simulated = False

class Instrument:
    def on_load(self):
        pass

    def before_measure(self):
        pass


class VisaInstrument(Instrument):
    def __init__(self, address: str):
        super().__init__()
        if is_simulated:
            return
        self.address: str = address
        res = rm.open_resource(self.address)
        assert isinstance(res, MessageBasedResource)
        self.resource: MessageBasedResource = res
        self.on_load()


labjack_resource = None
class LabJackInstrument(Instrument):
    FIO0 = 0
    FIO1 = 1
    FIO2 = 2
    FIO3 = 3
    AIN3 = 3
    AIN1 = 1
    DAC0 = 5000

    def __init__(
        self
    ):
        global labjack_resource
        super().__init__()
        if is_simulated:
            return
        import u6
        if not labjack_resource:
            labjack_resource = u6.U6()
        self.resource = labjack_resource
        self.resource.getCalibrationData()
        self.on_load()

    def disconnect(self):
        if self.resource is not None:
            self.resource.close()

class Channel[G: Callable[..., float], S: Callable[[float], None]]:
    def __init__(self, name: str, unit: Optional[str] = None):
        self.name = name
        self.unit = unit or name[0].upper()
        self._cache = weakref.WeakKeyDictionary()
        self._reader: Optional[Callable[..., float]] = None
        self._writer: Optional[Callable[[float],None]] = None

    def __get__(self, instance: Optional[Any], owner: Optional[type] = None) -> _InstrumentChannel:
        if instance is None:
            raise TypeError("Channel descript should only be accessed via the class instance")

        if instance not in self._cache:
            self._cache[instance] = _InstrumentChannel(self, instance)

        return self._cache[instance]

    def read(self, func: G):
        self._reader = func
        return func

    def write(self, func: S):
        self._writer = func
        return func


class _InstrumentChannel:
    def __init__(self, channel: Channel, instance: Any):
        self.channel: Channel = channel
        self._instance: Any = instance

    def get(self):
        if is_simulated:
            return 42.0
        if self.channel._reader is None:
            raise AttributeError(
                "No getter defined for channel {} in instrument {}".format(
                    self.channel.name, self._instance.__class__.__name__
                )
            )
        return self.channel._reader(self._instance)

    def set(self, *args, **kwargs):
        if is_simulated:
            return
        if self.channel._writer is None:
            raise AttributeError(
                "No setter defined for channel {} in instrument {}".format(
                    self.channel.name, self._instance.__class__.__name__
                )
            )
        return self.channel._writer(self._instance, *args, **kwargs)

    @overload
    def __call__(self, value: float) -> None: ...
    @overload
    def __call__(self) -> float: ...

    def __call__(self, value: Optional[float] = None):
        if value is not None:
            return self.set(value)
        return self.get()

    def __repr__(self):
        try:
            return str(self.get())
        except Exception:
            return "<{} channel '{}'>".format(self._instance.__class__.__name__, self.channel.name)

    @property
    def value(self):
        return self.get()

    @value.setter
    def value(self, val):
        self.set(val)
