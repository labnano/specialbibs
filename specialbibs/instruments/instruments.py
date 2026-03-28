from __future__ import annotations
from typing import Any, Callable, Optional, TypeVar
from pyvisa import ResourceManager
from pyvisa.resources import MessageBasedResource
import weakref

import os
os.add_dll_directory(r"C:\\Program Files\\Keysight\\IO Libraries Suite\\bin")

import u6
rm = ResourceManager()

class Instrument:
    def on_load(self):
        pass

    def before_measure(self):
        pass


class VisaInstrument(Instrument):
    def __init__(self, address: str):
        super().__init__()
        self.address: str = address
        res = rm.open_resource(self.address)
        assert isinstance(res, MessageBasedResource)
        self.resource: MessageBasedResource = res
        self.on_load()


class LabJackInstrument(Instrument):
    FIO0 = 0
    FIO1 = 1
    FIO2 = 2
    FIO3 = 3
    AIN3 = 3

    def __init__(
        self
    ):
        super().__init__()
        self.resource = u6.U6()
        self.resource.getCalibrationData()
        self.on_load()

    def disconnect(self):
        if self.resource is not None:
            self.resource.close()

class Channel:
    def __init__(self, name: str, unit: Optional[str] = None):
        self.name = name
        self.unit = unit or name[0].upper()
        self._cache = weakref.WeakKeyDictionary()
        self._reader: Optional[Callable] = None
        self._writer: Optional[Callable] = None

    def __get__(self, instance: Optional[Any], owner: Optional[type] = None) -> _InstrumentChannel:
        if instance is None:
            raise TypeError("Channel descript should only be accessed via the class instance")

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