from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import K2400, PressureSystem, HP_DMM
import numpy as np

# Definindo os equipamentos
#k2400_a = K2400(19)
k2400_b = K2400(20)
dmm = HP_DMM(22)
sistema = PressureSystem()
 
# Definindo os canais
Vsd = k2400_b.voltage
Isd = dmm.voltage
P = sistema.sensor


old_target: float = None
ramp_direction = 0
def setPressao(target: float):
    global old_target, ramp_direction
    if old_target is None:
        old_target = P()
    updated = target != old_target
    if updated:
        ramp_direction = np.sign(target - old_target)
        old_target = target

    margem_up = 0.03
    margem_down = 0.05
    if ramp_direction > 0: # Subir pressao
        if updated:
            sistema.sv(0) # Desliga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(1) # Liga gas
        if P() > target - margem_up:
            sistema.sv(0) # Desliga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(0) # Desliga gas
            ramp_direction = 0


    if ramp_direction < 0: # Descer pressao
        if updated:
            sistema.sv(1) # Liga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(0) # Desliga gas
        if P() < target + margem_down:
            sistema.sv(0) # Desliga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(0) # Desliga gas
            ramp_direction = 0

    return ramp_direction == 0


start = -0.8
end = 0.8
intervalo = 10
step = 0.2

n_passos = (end-start)//step
duracao = ((n_passos+1) * 2 - 1) * intervalo

multiplicador_preamp = 1


def loop(meas: MeasurementContext):
    i = meas.time // intervalo
    
    j = abs(( (i+n_passos) % (2*n_passos)) - n_passos) #Nao mecha nisso
    setPressao(start + j * step)

    meas.plot(("Voltage (V)", Isd()*multiplicador_preamp))
    meas.plot(P)


def _start():
    Vsd(1) # Setar tensao em 1v apenas no comeco
    sistema.sv(0)  # Desliga vacuo
    sistema.sa(0)  # Desliga alivio
    sistema.sg(0) # Desliga gas
    
    # while not setPressao(start - 0.05):
    #     continue


from specialbibs.plotting import PlotData
def _stop(dados: list[PlotData], folder: str):
    Vsd(0) # Resetar tensao no fim da medida
    sistema.sv(0)
    sistema.sa(0)
    sistema.sg(0)

    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    fig = Figure()
    canvas = FigureCanvas(fig)
    ax1 = fig.add_subplot(111)
    ax1.plot(dados[0].x_data, dados[0].y_data[:,0], color="black")
    ax1.set_ylabel(dados[0].y_labels[0])
    ax1.set_xlabel(dados[0].x_label)
    ax1.tick_params(axis='y', labelcolor="black")
    ax2 = ax1.twinx()
    ax2.plot(dados[0].x_data, dados[1].y_data[:,0], color="r")
    ax2.set_ylabel(dados[1].y_labels[0])
    ax2.tick_params(axis='y', labelcolor="r")
    fig.tight_layout() 
    canvas.print_figure(folder+'/minhafigura.svg')

SpecialBibs(loop,
    duration=duracao,
    sample_rate=20, # 20 medidas por segundo
    folder=f"medidas/amostra1",
    on_start=_start,
    on_complete=_stop,
    on_stop=_stop
) # This will drop you into a IPython shell where you can interact with the experiment while and after it's running. 
