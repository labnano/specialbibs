"""
Simple test to demonstrate simulation mode with real-time plotting.
Run from the parent directory: python -m specialbibs.test_simulation
Or directly: python specialbibs/test_simulation.py
"""

from specialbibs import SpecialBibs, set_simulation_mode
from specialbibs.instruments import K2400, PressureSystem

# Enable simulation mode - no real instruments needed
set_simulation_mode(True)

# Create simulated instruments
k2400_a = K2400(16)
k2400_b = K2400(8)
pressure_system = PressureSystem(10)


def run(meas):
    # First half: ramp voltage up, valve open
    if meas.time < 5:
        v = meas.map(0, 10, until=5)
        meas.set_once(pressure_system.valve, 1)
    # Second half: ramp voltage down, valve closed
    else:
        v = meas.map(10, 0, since=5, until=10)
        meas.set_once(pressure_system.valve, 0)

    # Set voltage on first Keithley
    k2400_a.voltage.set(v)

    # Plot 1: Voltage setpoint vs measured voltage
    meas.save_and_plot(v, k2400_b.voltage)

    # Plot 2: Current measurement
    meas.save_and_plot(k2400_a.current)

    # Plot 3: Pressure reading
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
