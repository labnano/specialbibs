from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import K2400, PressureSystem, HP_DMM
from bibs_coisas import setPressao, plot_same_graph

# Definindo os equipamentos
#k2400_a = K2400(19)
k2400_b = K2400(20)
dmm = HP_DMM(22)
sistema = PressureSystem()
 
# Definindo os canais
Vsd = k2400_b.voltage
Isd = dmm.voltage
P = sistema.sensor

start = -0.8
end = 0.8
intervalo = 10 # Tempo entre cada passo (s)
step = 0.2 # Variacao da pressao a cada passo

multiplicador_preamp = 1


n_passos = (end-start)//step
n_escadas = 2
duracao = (1 + n_passos * n_escadas) * intervalo
def loop(meas: MeasurementContext):
    i = meas.time // intervalo
    
    j = abs(( (i+n_passos) % (2*n_passos)) - n_passos) # j varia entre 0,1,2...n_passos,n_passos-1,...,2,1,0 em loop
    setPressao(start + j * step)

    meas.plot(("Voltage (V)", Isd()*multiplicador_preamp))
    meas.plot(P)


def _start():
    Vsd(1) # Setar tensao em 1v apenas no comeco
    sistema.sv(0)  # Desliga vacuo
    sistema.sa(0)  # Desliga alivio
    sistema.sg(0) # Desliga gas
    
    #while not setPressao(start - 0.05):
    #     continue


def _stop(dados, folder):
    Vsd(0) # Resetar tensao no fim da medida
    sistema.sv(0)
    sistema.sa(0)
    sistema.sg(0)
    
    plot_same_graph(dados, folder)


SpecialBibs(loop,
    duration=duracao,
    sample_rate=20, # 20 medidas por segundo
    folder=f"medidas/amostra1",
    on_start=_start,
    on_complete=_stop,
    on_stop=_stop
) 
