from specialbibs import SpecialBibs, MeasurementContext
from specialbibs.instruments import K2400, PressureSystem

k2400_a = K2400(19)
k2400_b = K2400(20)
pressure = PressureSystem()

def loop(meas: MeasurementContext):
    meas.once(k2400_b.voltage, 0.1)
    if meas.time < 20:
        v = meas.map(0, 1, until=20)
        meas.once(pressure.sa, 1)
    else:
        v = meas.map(1, 0, since=20, until=40)
        meas.once(pressure.sa, 0)

    k2400_a.voltage.set(v)

    meas.plot(('Set Voltage (v)', v), k2400_a.voltage)
    meas.plot(k2400_b.voltage)


SpecialBibs(loop,
    duration=40.0,
    sample_rate=20,
    folder="simulated_measurement",
    plot=True,
) # This will drop you into a IPython shell where you can interact with the experiment while and after it's running. 
