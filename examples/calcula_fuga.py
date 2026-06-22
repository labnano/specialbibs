from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import K2400
import time

# Instrumentos
k2400 = K2400(24)

# Canais
Vg = k2400.voltage
Vg.rate = 1 # V/s
Isd = k2400.current

start_v = 0.0
end_v = 10.0
n_pontos = 100

offset = -3.9856e-10
r_leaking = 1.2012e+09

measure_offset_duration = 10
measure_leaking_from = 1e-9



res = []
off = []
i_start = None
def loop(meas: MeasurementContext):
    global res
    global off
    global i_start
    v = meas.map(start_v, end_v, since=measure_offset_duration)
    Vg.set(v)
    i_leaking = v/r_leaking
    i = Isd()
    ipa = (i - i_leaking - offset) * 1e12
    r = v/i
    meas.plot(("I (A)", i))
    meas.plot(("Vg (V)", v), ("I (pA)", ipa))
    meas.plot(("R (ohm)", r))
    if meas.time < measure_offset_duration:
        off += [i]
        if i_start is None:
            i_start = i
    if i - i_start > measure_leaking_from:
        res += [r]
   


s_time = 0

def _start():
    global s_time
    pass
    Vg(0)
    s_time = time.perf_counter()

def _stop(dados, folder):
    print(f"R(ohms): {sum(res)/len(res):.5g}")
    print(f"Offset(A): {sum(off)/len(off):.5g}")
    print("Finished in: ", time.perf_counter() - s_time)

sample_rate = 5 # Hz
SpecialBibs(
    loop,
    on_start=_start,
    duration=n_pontos/sample_rate,
    sample_rate=sample_rate,
    folder="medidas/test",
    on_complete=_stop
)
