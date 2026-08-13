from .instruments import VisaInstrument, Channel

class K2400(VisaInstrument):
    """Keithley 2400 SourceMeter"""

    voltage = Channel("Voltage", unit="V")
    current = Channel("Current", unit="A")

    def __init__(self, gpib_address: int, current_protection: float = 100e-6, is_currentmeter=False):
        self.reading_voltage = True
        self.current_protection = current_protection
        self.range = 200
        self.is_current_meter = is_currentmeter

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
        if not self.reading_voltage:
            self.resource.write(':FORMAT:ELEMENTS CURR')
            self.resource.write(':SENS:FUNC "CURR"')
        else:
            if self.is_current_meter:
                print("Warning: Trying to read voltage while in current meter mode")
                self.resource.write(':FORMAT:ELEMENTS VOLT')
                self.resource.write(':SENS:FUNC "VOLT"')
            

    def on_load(self):
        print("Loaded K2400")
        #self.resource.write('*RST')
        if self.is_current_meter:
            self.resource.write(':SOURCE:FUNCTION VOLT')
            self.resource.write(':SOURCE:VOLTAGE:MODE FIXED')
            self.resource.write(':SENS:FUNC "CURR"')
            self.resource.write(':SOURCE:VOLTAGE:RANGE MIN')
            self.resource.write(':SOURCE:VOLTAGE:LEV 0')
            self.resource.write(':SENSE:CURRENT:PROTECTION 1.05') #Always use 1A as prot and range just to be safe 
            self.resource.write(':SENSE:CURRENT:RANG 1')
            self.resource.write(':FORMAT:ELEMENTS CURR')
            self.resource.write(':OUTPUT ON')
        else:
            self.resource.write(':SOURCE:FUNCTION VOLT')
            self.resource.write(f':SOURCE:VOLTAGE:RANGE {self.range}') # Select range for V-Source (-210 to 210)
            self._set_mode()
            self.resource.write(f':SENSE:CURRENT:PROTECTION {self.current_protection}') #Set current compliance for V-Source (-1.05 to 1.05) 
            self.resource.write(':FORMAT:ELEMENTS VOLT')
            #self.resource.write(':SENSE:CURRENT:RANGE 1e-6')
            self.resource.write(':OUTPUT ON')
            #self.resource.write(':SENSE:CURRENT:NPLCYCLES 0.01') # Current integration rate (0.01 to 10)
            #self.resource.write(':SENSE:VOLTAGE:NPLCYCLES 0.01') # Voltage integration rate (0.01 to 10)



    def reset(self):
        self.resource.write('*RST')
        self.on_load()


class K2000(VisaInstrument):
    """DMM K2000"""

    voltage = Channel("Voltage", unit="V")

    def __init__(self, gpib_address: int,):
        super().__init__(f"GPIB0::{gpib_address}::INSTR")

    @voltage.read
    def _read_voltage(self) -> float:
        response = self.resource.query("DATA?")
        voltage = float(response)
        return voltage

