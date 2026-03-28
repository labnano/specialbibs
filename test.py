from specialbibs import SpecialBibs
from specialbibs.instruments import K2400, PressureSystem

k2400_a = K2400(19)
k2400_b = K2400(20)
pressure_system = PressureSystem()

def loop(meas):
    meas.set_once(k2400_b.voltage, 0.1)
    if meas.time < 20:
        v = meas.map(0, 1, until=20)
        #meas.set_once(pressure_system.sa, 1)
    else:
        v = meas.map(1, 0, since=20, until=40)
        #meas.set_once(pressure_system.sa, 0)

    k2400_a.voltage.set(v)

    meas.save_and_plot(v, k2400_a.voltage)
    meas.save_and_plot(k2400_b.voltage)


experiment = SpecialBibs(
    loop,
    duration=40.0,
    sample_rate=20,
    file="simulated_measurement.txt",
    plot=True,
)

# Wait for measurement to complete
experiment.wait()