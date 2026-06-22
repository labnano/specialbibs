from specialbibs import SpecialBibs
from specialbibs.instruments import K2400, HP_DMM, SR810

# Instrumentos
k2400 = K2400(24)
#dmm = HP_DMM(22)
lockin = SR810(8)

# Canais

# K2400
Vg = k2400.voltage
Vg.rate = 1 # V/s
Isd = k2400.current
#vg = 
#Vg.set(vg)

# Lock-In
Vsd = lockin.aux_out1
Vsd.rate = 0.01 
vsd = 0.0
Vsd.set(vsd)


sample_rate = 5 # Hz
SpecialBibs()