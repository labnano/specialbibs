"""
Simple test to demonstrate simulation mode with real-time plotting.
Run from the parent directory: python -m specialbibs.test_simulation
Or directly: python specialbibs/test_simulation.py
"""

from specialbibs import MeasurementContext, SpecialBibs, set_simulation_mode
from specialbibs.instruments import K2400, PressureSystem

# Enable simulation mode - no real instruments needed
set_simulation_mode(True)

k2400_a = K2400(16)
k2400_b = K2400(8)
pressure_system = PressureSystem() 


def run(meas: MeasurementContext):
    if meas.time < 5:
        v = meas.map(0, 10, until=5)
        meas.set_once(pressure_system.valve, 1)
    else:
        v = meas.map(10, 0, since=5, until=10)
        meas.set_once(pressure_system.valve, 0)

    k2400_a.voltage.set(v)

    meas.save_and_plot(v, k2400_b.voltage)
    meas.save_and_plot(k2400_a.current)
    meas.save_and_plot(pressure_system.pressure)


if __name__ == "__main__":
    print("Starting simulated measurement...")
    print("- Measurement runs in background thread")
    print("- Plots update in real-time")
    print("- Close the plot window to exit")
    print()

    experiment = SpecialBibs(
        run,
        duration=10.0,
        sample_rate=20,
        file="/tmp/simulated_measurement.txt",
        plot=True,
    )

    # Wait for measurement to complete
    experiment.wait()

    print(f"\nData saved to: /tmp/simulated_measurement.txt")
