from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import K2400, K2000
from bibs_coisas import plot_same_graph

# Equipamentos
k2400_b = K2400(20)
dmm = K2000(16)

# Canais
Vsd = k2400_b.voltage
Isd = dmm.voltage


duracao = 10 # segundos

def loop(meas: MeasurementContext):
    tempo = meas.time  # tempo em segundos

    corrente = Isd()

    corrente_uA = corrente * 1e6

    meas.plot(("Voltage (V)", corrente))
    meas.plot(("Isd (uA)", corrente_uA))

    if corrente != 0:
        resistencia = 1 / corrente_uA
        meas.plot(("R (Mohm)", resistencia))

def _start():
    Vsd(1)  # aplica 1V no início

def _stop(dados, folder):
    Vsd(0)  # desliga no final
    plot_same_graph(dados, folder)

SpecialBibs(
    loop,
    duration=duracao,
    sample_rate=20,  # 20 Hz
    folder="medidas/teste",
    on_start=_start,
    # on_complete=_stop,
    on_stop=_stop,
    exit_on_finish=False
)