from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import K2400
import time

# Instrumentos
k2400 = K2400(24)

# Canais
Vg = k2400.voltage
Vg.rate = 0.01 # V/s
Isd = k2400.current

start_v = 0.0
end_v = 10.0
step_size = 0.01

def loop(meas: MeasurementContext):
    v = meas.map(start_v, end_v)
    Vg.set(v)
    i = Isd()
    r = v/i
    meas.plot(("Vg (V)", v), ("I (pA)", i* 1e12))
    meas.plot(("R (ohm)", r))

def _start():
    Vg(0)
    time.sleep(5)

def _stop(dados, folder):
    Vg(0)


n_pontos = (end_v-start_v)/step_size
sample_rate = 20 # Hz
SpecialBibs(
    loop,
    on_start=_start,
    duration=n_pontos/sample_rate,
    sample_rate=sample_rate,
    folder="medidas/test",
    on_stop=_stop
)
