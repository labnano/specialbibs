from .instruments import VisaInstrument, Channel

class K2400(VisaInstrument):
    """Keithley 2400 SourceMeter"""

    voltage = Channel("Voltage", unit="V")
    current = Channel("Current", unit="A")

    def __init__(self, gpib_address: int, dmm = False):
        super().__init__(f"GPIB0::{gpib_address}::INSTR")
        self.dmm = dmm

    @voltage.read
    def _read_voltage(self) -> float:
        response = self.resource.query("READ?")
        voltage = float(response.split(',')[0])
        return voltage

    @voltage.write
    def _set_voltage(self, value: float):
        command = f":SOUR:VOLT {value}"
        self.resource.write(command)

    @current.read
    def _read_current(self) -> float:
        response = self.resource.query("READ?")
        current = float(response.split(',')[1])
        return current

    @current.write
    def _set_current(self, value: float):
        command = f":SOUR:CURR {value}"
        self.resource.write(command)

    def on_load(self):
        print("Loaded K2400")
        self.resource.write('*RST')
        self.resource.write(':sour:func volt')
        self.resource.write(':sour:volt:rang 200')
        self.resource.write(':sens:curr:prot 1000e-3')
        self.resource.write(':sens:curr:rang 1000e-3')
        self.resource.write(':outp on')
