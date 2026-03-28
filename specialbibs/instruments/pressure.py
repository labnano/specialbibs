import u6
from .instruments import Channel, LabJackInstrument

class PressureSystem(LabJackInstrument):
    sensor = Channel("Sensor", unit="P") #AIN3 - Pegar valor
    sg = Channel("Solenoide SD", unit="") #FIO1 - 0 or 1
    sa = Channel("Solenoide SA", unit="") #FIO2- 0 or 1
    sv = Channel("Solenoide SV", unit="") #FIO3 + #FIO0 - 0 or 1

    def __init__(
        self
    ):
        super().__init__()

    @sensor.read
    def _read_sensor(self) -> int:
        # Nao precisa de passar o canal GND. O 199 só era usado pra falar que a medida n é diferencial
        return self.resource.getAIN(positiveChannel=3, resolutionIndex=12, settlingFactor=0, differential=False)

    @sg.write
    def _set_sg(self, val: int):
        self.resource.setDIOState(LabJackInstrument.FIO1, val)
    @sa.write
    def _set_sa(self, val: int):
        self.resource.setDIOState(LabJackInstrument.FIO2, val)
    @sv.write
    def _set_sv(self, val: int):
        self.resource.setDIOState(LabJackInstrument.FIO0, val)
        self.resource.setDIOState(LabJackInstrument.FIO3, val)
