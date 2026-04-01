from .instruments import VisaInstrument, Channel

class K2400(VisaInstrument):
    """Keithley 2400 SourceMeter"""

    voltage = Channel("Voltage", unit="V")
    current = Channel("Current", unit="A")

    def __init__(self, gpib_address: int, dmm = False):
        self.as_dmm = dmm
        self.reading_voltage = True
        super().__init__(f"GPIB0::{gpib_address}::INSTR")

    @voltage.read
    def _read_voltage(self) -> float:
        if not self.reading_voltage:
            self.reading_voltage = True
            self._set_mode()
        response = self.resource.query("READ?")
        voltage = float(response)
        return voltage

    @voltage.write
    def _set_voltage(self, value: float):
        command = f":SOUR:VOLT {value}"
        self.resource.write(command)

    @current.read
    def _read_current(self) -> float:
        if self.reading_voltage:
            self.reading_voltage = False
            self._set_mode()
        response = self.resource.query("READ?")
        current = float(response)
        if current == 9.91e37:
            return float('nan')
        return current

    @current.write
    def _set_current(self, value: float):
        command = f":SOUR:CURR {value}"
        self.resource.write(command)

    def _set_mode(self):
        if self.reading_voltage:
            self.resource.write(':FORMAT:ELEMENTS VOLT')
            self.resource.write(':SENS:FUNC "VOLT"')
        else:
            self.resource.write(':FORMAT:ELEMENTS CURR')
            self.resource.write(':SENS:FUNC "CURR"')

    def on_load(self):
        print("Loaded K2400")
        self.resource.write('*RST')
        self.resource.write(':SOURCE:FUNCTION VOLT')
        self.resource.write(':SOURCE:VOLTAGE:RANGE 200') # Select range for V-Source (-210 to 210)
        self._set_mode()
        self.resource.write(':SENSE:CURRENT:PROTECTION 1000e-3') #Set current compliance for V-Source (-1.05 to 1.05) 
        self.resource.write(':SENSE:CURRENT:RANGE 100e-3')
        self.resource.write(':OUTPUT ON')
        self.resource.write(':SENSE:CURRENT:NPLCYCLES 0.01') # Current integration rate (0.01 to 10)
        self.resource.write(':SENSE:VOLTAGE:NPLCYCLES 0.01') # Voltage integration rate (0.01 to 10)
