Python interface for communicating with VISA instruments and LabJack.

## Example
```python
from specialbibs import SpecialBibs
from specialbibs.instruments import K2400, PressureSystem

k2400_a = K2400(16)
k2400_b = K2400(8)
pressure_system = PressureSystem(10)

def run(meas):
    if meas.time < 5:
        v = meas.map(0, 10, to = 5)
        meas.set_once(pressure_system.valve, 1)
    else:
        v = meas.map(10, 0, from = 5, to = 10)
        meas.set_once(pressure_system.valve, 0)
    k2400_a.voltage.set(v)
    meas.save_and_plot(v, k2400_b.voltage)


SpecialBibs(run,
    duration = 10.0,
    sample_rate = 20,
    file = "medida_1.txt",
)

```
