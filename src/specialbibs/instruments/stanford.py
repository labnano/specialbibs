from .instruments import VisaInstrument, Channel


class SR810(VisaInstrument):
    """Stanford Research Systems SR810 Lock-in Amplifier"""

    x = Channel("X", unit="V")
    y = Channel("Y", unit="V")
    r = Channel("R", unit="V")
    theta = Channel("Theta", unit="deg")
    frequency = Channel("Frequency", unit="Hz")
    amplitude = Channel("Amplitude", unit="V")
    phase = Channel("Phase", unit="deg")

    aux_in1 = Channel("Aux Input 1", unit="V")
    aux_in2 = Channel("Aux Input 2", unit="V")
    aux_in3 = Channel("Aux Input 3", unit="V")
    aux_in4 = Channel("Aux Input 4", unit="V")

    aux_out1 = Channel("Aux Output 1", unit="V")
    aux_out2 = Channel("Aux Output 2", unit="V")
    aux_out3 = Channel("Aux Output 3", unit="V")
    aux_out4 = Channel("Aux Output 4", unit="V")

    sensitivity = Channel("Sensitivity", unit="V")
    time_constant = Channel("Time Constant", unit="s")
    sync_filter = Channel("Sync Filter")

    # Sensitivity lookup tables
    _SENS_VALS = (
        [2e-9, 5e-9, 10e-9]
        + [2e-8, 5e-8, 10e-8]
        + [2e-7, 5e-7, 10e-7]
        + [2e-6, 5e-6, 10e-6]
        + [2e-5, 5e-5, 10e-5]
        + [2e-4, 5e-4, 10e-4]
        + [2e-3, 5e-3, 10e-3]
        + [2e-2, 5e-2, 10e-2]
        + [2e-1, 5e-1, 10e-1]
        + [2, 5, 10]
    )

    # Time constant lookup tables
    _TAU_VALS = (
        [10e-6, 30e-6]
        + [100e-6, 300e-6]
        + [1e-3, 3e-3]
        + [10e-3, 30e-3]
        + [100e-3, 300e-3]
        + [1, 3]
        + [10, 30]
        + [100, 300]
        + [1e3, 3e3]
        + [10e3, 30e3]
    )

    def __init__(self, gpib_address: int):
        super().__init__(f"GPIB0::{gpib_address}::INSTR")

    # X
    @x.read
    def _read_x(self) -> float:
        return float(self.resource.query("OUTP? 1"))

    # Y
    @y.read
    def _read_y(self) -> float:
        return float(self.resource.query("OUTP? 2"))

    # R
    @r.read
    def _read_r(self) -> float:
        return float(self.resource.query("OUTP? 3"))

    # Theta
    @theta.read
    def _read_theta(self) -> float:
        return float(self.resource.query("OUTP? 4"))

    # Frequency
    @frequency.read
    def _read_frequency(self) -> float:
        return float(self.resource.query("FREQ?"))

    @frequency.write
    def _set_frequency(self, value: float):
        self.resource.write(f"FREQ {value}")

    # Amplitude
    @amplitude.read
    def _read_amplitude(self) -> float:
        return float(self.resource.query("SLVL?"))

    @amplitude.write
    def _set_amplitude(self, value: float):
        self.resource.write(f"SLVL {value}")

    # Phase
    @phase.read
    def _read_phase(self) -> float:
        return float(self.resource.query("PHAS?"))

    @phase.write
    def _set_phase(self, value: float):
        self.resource.write(f"PHAS {value}")

    # Aux inputs (read-only)
    @aux_in1.read
    def _read_aux_in1(self) -> float:
        return float(self.resource.query("OAUX? 1"))

    @aux_in2.read
    def _read_aux_in2(self) -> float:
        return float(self.resource.query("OAUX? 2"))

    @aux_in3.read
    def _read_aux_in3(self) -> float:
        return float(self.resource.query("OAUX? 3"))

    @aux_in4.read
    def _read_aux_in4(self) -> float:
        return float(self.resource.query("OAUX? 4"))

    # Aux outputs
    @aux_out1.read
    def _read_aux_out1(self) -> float:
        return float(self.resource.query("AUXV? 1"))

    @aux_out1.write
    def _set_aux_out1(self, value: float):
        self.resource.write(f"AUXV 1, {value}")

    @aux_out2.read
    def _read_aux_out2(self) -> float:
        return float(self.resource.query("AUXV? 2"))

    @aux_out2.write
    def _set_aux_out2(self, value: float):
        self.resource.write(f"AUXV 2, {value}")

    @aux_out3.read
    def _read_aux_out3(self) -> float:
        return float(self.resource.query("AUXV? 3"))

    @aux_out3.write
    def _set_aux_out3(self, value: float):
        self.resource.write(f"AUXV 3, {value}")

    @aux_out4.read
    def _read_aux_out4(self) -> float:
        return float(self.resource.query("AUXV? 4"))

    @aux_out4.write
    def _set_aux_out4(self, value: float):
        self.resource.write(f"AUXV 4, {value}")

    # Sensitivity (exposed as value, stored as index)
    @sensitivity.read
    def _read_sensitivity(self) -> float:
        idx = int(self.resource.query("SENS?"))
        return self._SENS_VALS[idx]

    @sensitivity.write
    def _set_sensitivity(self, value: float):
        idx = self._sens_value_to_index(value)
        self.resource.write(f"SENS {idx}")

    # Time constant (exposed as value, stored as index)
    @time_constant.read
    def _read_time_constant(self) -> float:
        idx = int(self.resource.query("OFLT?"))
        return self._TAU_VALS[idx]

    @time_constant.write
    def _set_time_constant(self, value: float):
        idx = self._tau_value_to_index(value)
        self.resource.write(f"OFLT {idx}")

    # Sync filter
    @sync_filter.read
    def _read_sync_filter(self) -> int:
        return int(self.resource.query("SYNC?"))

    @sync_filter.write
    def _set_sync_filter(self, value: int):
        self.resource.write(f"SYNC {value}")

    def _sens_value_to_index(self, value: float) -> int:
        for i, sv in enumerate(self._SENS_VALS):
            if sv >= value:
                return i
        return len(self._SENS_VALS) - 1

    def _tau_value_to_index(self, value: float) -> int:
        for i, tv in enumerate(self._TAU_VALS):
            if tv >= value:
                return i
        return len(self._TAU_VALS) - 1

    def on_load(self):
        print("Loaded SR810")
        #self.resource.write("*RST")
