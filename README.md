Python interface for communicating with VISA instruments and LabJack.

## Example
```python
from specialbibs import SpecialBibs, set_simulation_mode
from specialbibs.instruments import K2400, PressureSystem

# Enable simulation mode for testing without real instruments
set_simulation_mode(True)

k2400_a = K2400(16)
k2400_b = K2400(8)
pressure_system = PressureSystem(10)

def run(meas):
    if meas.time < 5:
        v = meas.map(0, 10, to=5)
        meas.set_once(pressure_system.valve, 1)
    else:
        v = meas.map(10, 0, from_time=5, to=10)
        meas.set_once(pressure_system.valve, 0)
    k2400_a.voltage.set(v)
    meas.save_and_plot(v, k2400_b.voltage)


# Measurement runs in background thread, plots in another thread
# Main thread remains free for IPython interaction
experiment = SpecialBibs(run,
    duration=10.0,
    sample_rate=20,
    file="medida_1.txt",
)

# Optional: wait for completion
# experiment.wait()

# Or control the experiment interactively:
# experiment.pause()
# experiment.resume()
# experiment.stop()
# experiment.is_running
# experiment.current_time
```

## Features

- **Simulation Mode**: Test your measurement code without physical instruments
- **Threaded Execution**: Measurement loop and plotting run in separate threads
- **Real-time Plotting**: Data is plotted as it's collected using matplotlib animation
- **Automatic Plot Identification**: Multiple `save_and_plot()` calls create separate plots automatically
- **IPython Compatible**: Main thread stays free for interactive session
