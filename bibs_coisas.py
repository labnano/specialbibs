
from typing import Optional
import numpy as np
from specialbibs.instruments import PressureSystem

sistema = PressureSystem()


old_target: Optional[float] = None
ramp_direction = 0
def setPressao(target: float):
    global old_target, ramp_direction
    if old_target is None:
        old_target = sistema.sensor()
    updated = target != old_target
    if updated:
        ramp_direction = np.sign(target - old_target)
        old_target = target
        print(target)

    margem_up = 0.03
    margem_down = 0.05
    if ramp_direction > 0: # Subir pressao
        if updated:
            sistema.sv(0) # Desliga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(1) # Liga gas
        if sistema.sensor() > target - margem_up:
            sistema.sv(0) # Desliga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(0) # Desliga gas
            ramp_direction = 0


    if ramp_direction < 0: # Descer pressao
        if updated:
            sistema.sv(1) # Liga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(0) # Desliga gas
        if sistema.sensor() < target + margem_down:
            sistema.sv(0) # Desliga vacuo
            sistema.sa(0) # Desliga alivio
            sistema.sg(0) # Desliga gas
            ramp_direction = 0

    return ramp_direction == 0


from specialbibs.plotting import PlotData
def plot_same_graph(dados: list[PlotData], folder: str):
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
    canvas.print_figure(folder+'/pressao_e_tensao.svg')


