import sys
sys.path.append(".")
import logging
logger = logging.getLogger()
# logger.setLevel(0)

import sizer

import numpy as np


with open("./demos/two-stage-amplifier/two-stage-amp.cir") as f:
    circuitTemplate = sizer.CircuitTemplate(f.read(), rawSpice=".lib CMOS_035_Spice_Model.lib tt")

def bandwidthLoss(circuit):
    try:
        return np.maximum(0, (5e+3 - circuit.bandwidth) / 5e+3) ** 2
        # return (1e+6 - circuit.bandwidth) / 1e+6
    except:
        print("bandwidth undefined")
        return 1

def gainLoss(circuit):
    return np.maximum(0, (1e+3 - np.abs(circuit.gain)) / 1e+3) ** 2
    # return (1e+3 - np.abs(circuit.gain)) / 1e+3

def phaseMarginLoss(circuit):
    try:
        return np.maximum(0, (60 - circuit.phaseMargin) / 60) ** 2
    except:
        return 0

def loss(circuit):
    return np.sum([phaseMarginLoss(circuit), gainLoss(circuit), bandwidthLoss(circuit)])

bounds = {
    w: [3.5e-7, 3.5e-4] for w in ["w12", "w34", "w5", "w6", "w7", "w8"]
}

bounds.update({
    l: [3.5e-7, 3.5e-6] for l in ["l12", "l34", "l5", "l6", "l7", "l8"]
})

bounds.update({
    "cm": [1e-12, 10e-12]
})

bounds.update({
    "vdc": [1, 2]
})

# optimizer = sizer.optimizers.Optimizer(circuitTemplate, loss, bounds)
optimizer = sizer.optimizers.ScipyMinimizeOptimizer(circuitTemplate, loss, bounds)
circuit = optimizer.run()
print(circuit.netlist)
print("total loss:", loss(circuit))
print("optimal parameters", dict(zip(circuitTemplate.parameters, circuit.parameters)))
print("bandwidth:", circuit.bandwidth)
print("gain:", circuit.gain)
print("phase margin:", circuit.phaseMargin)

import matplotlib.pyplot as plt

plt.rcParams["axes.grid"] = True

frequencies, frequencyResponse = circuit.frequencyResponse()

plt.subplot(211)
plt.plot(frequencies, np.abs(frequencyResponse))
plt.xscale("log")
plt.yscale("log")
plt.vlines(sizer.calculators.unityGainFrequency(frequencies, frequencyResponse), 0, 1e+3)

plt.subplot(212)
phaseResponse = np.angle(frequencyResponse, deg=True)
phaseResponse[np.where(phaseResponse > 0)] -= 360
plt.plot(frequencies, phaseResponse)
plt.xscale("log")
plt.vlines(sizer.calculators.unityGainFrequency(frequencies, frequencyResponse), -180, 0)
plt.show()