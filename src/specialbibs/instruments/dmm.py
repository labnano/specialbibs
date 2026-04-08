from .instruments import VisaInstrument, Channel

class HP_DMM(VisaInstrument):
    """DMM HP34401A"""

    voltage = Channel("Voltage", unit="V")

    def __init__(self, gpib_address: int,):
        super().__init__(f"GPIB0::{gpib_address}::INSTR")

    @voltage.read
    def _read_voltage(self) -> float:
        response = self.resource.query("READ?")
        voltage = float(response)
        return voltage

    def on_load(self):
        self.resource.write("VOLTage:DC:NPLCycles 0.2")
        print("Loaded DMM")
