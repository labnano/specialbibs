from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import K2400, PressureSystem
import numpy as np

# Definindo os equipamentos
k2400_a = K2400(19)
k2400_b = K2400(20)
sistema = PressureSystem()
 
# Definindo os canais
Vsd = k2400_a.voltage
V = k2400_b.voltage
P = sistema.sensor
# temperatura = sistema.temperatura

# temperatura(100) # Setando a temperatura para 100 graus
Vsd(1) # Setando a tensão do K2400 A para 1V



old_target: float = 0
ramp_direction = 0
def setPressao(target: float):
    global old_target, ramp_direction
    updated = target != old_target
    if updated:
        ramp_direction = np.sign(target - old_target)
        old_target = target

    margem = 0.2
    if ramp_direction > 0: # Subir pressao
        if updated:
            sistema.sg(1) # Liga gas
            sistema.sv(0) # Desliga vacuo
        if P() > target - margem:
            sistema.sg(0)
            ramp_direction = 0


    if ramp_direction < 0: # Descer pressao
        if updated:
            sistema.sg(0) # Desliga gas
            sistema.sv(1) # Liga vacuo
        if P() < target + margem:
            sistema.sv(0)
            ramp_direction = 0



def loop(meas: MeasurementContext):
    if meas.time < 20:
        setPressao(meas.time//10 * 5) # Sobe a pressão 5 unidades a cada 10 segundos
    else:
        setPressao(meas.time//10 * 5 - 10) # Desce a pressão 5 unidades a cada 10 segundos, depois de 20 segundos


    meas.plot(k2400_b.voltage)
    meas.plot(sistema.sensor)


SpecialBibs(loop,
    duration=40.0,
    sample_rate=20,
    folder=f"medidas",
    plot=True,
) # This will drop you into a IPython shell where you can interact with the experiment while and after it's running. 
