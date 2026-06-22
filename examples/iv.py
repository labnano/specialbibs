from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import HP_DMM, SR810
import time

# Instrumentos
dmm = HP_DMM(22)
lockin = SR810(8)

# Canais
Vsd = lockin.aux_out1
Isd = dmm.voltage

multiplier = -1e4
start_v = 0.0
end_v = 0.1
n_pontos = 100

def loop(meas: MeasurementContext):
    v = meas.map(start_v, end_v)
    Vsd.set(v)
    i = Isd()*multiplier
    ax = meas.plot( ("Vsd (V)", v), ("Isd (A)", i))
    ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0)) 

def _start():
    pass
    #Vsd(0)
    #time.sleep(2.0)


sample_rate = 20 # 10 Hz
SpecialBibs(
    loop,
    on_start=_start,
    duration=n_pontos/sample_rate,
    sample_rate=sample_rate,
    folder="Fernanda/Au/IxV contatos",
)