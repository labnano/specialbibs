from .instruments import Channel, LabJackInstrument

class PressureSystem(LabJackInstrument):
    sensor = Channel("Sensor", unit="P") #AIN3 - Pegar valor
    sg = Channel("Solenoide SD", unit="") #FIO1 - 0 or 1
    sa = Channel("Solenoide SA", unit="") #FIO2- 0 or 1
    sv = Channel("Solenoide SV", unit="") #FIO3 + #FIO0 - 0 or 1
    temperatura = Channel("Temperatura", unit="°C")#AIN1(leitura) e DAC1(set)
    def __init__(
        self
    ):
        super().__init__()

    @sensor.read
    def _read_sensor(self) -> float:
        # Nao precisa de passar o canal GND. O 199 só era usado pra falar que a medida n é diferencial
        v = self.resource.getAIN(positiveChannel=LabJackInstrument.AIN3, resolutionIndex=0, settlingFactor=0, differential=False)
        return 0.5234*v - 1.5492

    @sg.write
    def _set_sg(self, val: int):
        self.resource.setDIOState(LabJackInstrument.FIO1, self.valve_value(val))
    @sa.write
    def _set_sa(self, val: int):
        self.resource.setDIOState(LabJackInstrument.FIO2, self.valve_value(val))
    @sv.write
    def _set_sv(self, val: int):
        self.resource.setDIOState(LabJackInstrument.FIO0, self.valve_value(val))
        self.resource.setDIOState(LabJackInstrument.FIO3, self.valve_value(val))

    def _get_temp_v(self) -> float:
        return self.resource.getAIN(positiveChannel=LabJackInstrument.AIN1, resolutionIndex=0, settlingFactor=0, differential=False)
    def _set_temp_v(self, v: float):
        self.resource.writeRegister(LabJackInstrument.DAC0, v)


    @temperatura.read
    def _get_temperatura(self) -> float:
        v = self._get_temp_v()
        return v*37.62613021705122-89.774944412884
    @temperatura.write
    def _set_temperatura(self, val:float):
        self._set_temp_v(val/41.37307142857143+2.4084074700072335)

    def valve_value(self, val: int):
        if val == 0:
            _val = 1
        elif val == 1:
            _val = 0
        else:
            print("Valor proibido pra valvula")
            _val = 1
        return _val