import sys
sys.path.append(".")
import logging
logger = logging.getLogger()
# logger.setLevel(0)

import sizer

import numpy as np
import time

with open("./demos/slew-rate/ac.cir") as f:
    acTemplate = sizer.CircuitTemplate(f.read()) # read netlist template for ac measurement

with open("./demos/slew-rate/tran.cir") as f:
    tranTemplate = sizer.CircuitTemplate(f.read()) # read netlist template for transient measurement

templates = sizer.CircuitTemplateList([acTemplate, tranTemplate])

def bandwidthLoss(circuit): # receive ac template
    try:
        return np.maximum(0, (5e+3 - circuit.bandwidth) / 5e+3) ** 2
        # return np.maximum(0, (5e+3 - circuit.bandwidth) / 5e+3)
        # return (1e+6 - circuit.bandwidth) / 1e+6
    except:
        print("bandwidth undefined")
        return 1 # an amp whose bandwidth is not defined is likely an ill amp.

def unityGainFrequencyLoss(circuit):
    try:
        return np.maximum(0, (1e+7 - circuit.unityGainFrequency) / 1e+7) ** 2
        # return np.maximum(0, (1e+7 - circuit.unityGainFrequency) / 1e+7)
    except:
        print("ugf undefined", end="\r")
        return 1

def gainLoss(circuit):
    return np.maximum(0, (1e+3 - np.abs(circuit.gain)) / 1e+3) ** 2
    # return np.maximum(0, (1e+3 - np.abs(circuit.gain)) / 1e+3)
    # return (1e+3 - np.abs(circuit.gain)) / 1e+3

def phaseMarginLoss(circuit):
    try:
        return np.maximum(0, (60 - circuit.phaseMargin) / 60) ** 2
        # return np.maximum(0, (60 - circuit.phaseMargin) / 60)
    except:
        return 0 # an amp whose pm is not defined is likely a very stable amp.

# def areaLoss(circuit):
#     mapping = dict(zip(circuit.circuitTemplate.parameters, circuit.parameters))
#     return np.sum(mapping["w" + i] * mapping["l" + i] for i in ["12", "34", "5", "6", "7", "8"])

# def powerLoss(circuit):
#     loss = np.maximum(0, (3.3 * 10e-6 - circuit.staticPower) / (3.3 * 10e-6)) ** 2
#     print(loss, end="\r")
#     return loss

def slewRateLossByDefinition(circuit): # slew rate loss by naive definition
    circuit.hints["tran"]["start"] = 0.4e-6
    circuit.hints["tran"]["end"] = 0.6e-6
    circuit.hints["tran"]["points"] = 50
    # print(output[0], output[-1])
    slewRate = circuit.slewRate
    return np.maximum(0, (10e+6 - slewRate) / 10e+6) ** 2

def slewRateLossByRisingTime(circuit): # slew rate measured with 10% to 90% rising time
    analysis = circuit.getTransientModel(start=0.4e-6, end=0.6e-6, points=50)
    times = np.array(analysis.time)
    output = circuit.getOutput(analysis.nodes)
    try:
        slewRate = (1.74 - 1.66) / sizer.calculators.risingTime(times, output, 1.66, 1.74)
    except:
        print("slew rate undefined:", np.min(output), np.max(output), end="\r")
        return 1 # an amp whose slew rate is not defined is likely an ill amp whose output never increases to 1.75 V.
    return np.maximum(0, (10e+6 - slewRate) / 10e+6) ** 2

def slewRateLossHybrid(circuit): # slew rate measured with the combination of those 2 methods above: take only the slice from 10% to 90% then measure its maximum absolute derivative.
    analysis = circuit.getTransientModel(start=0.4e-6, end=0.6e-6, points=50)
    times = np.array(analysis.time)
    output = circuit.getOutput(analysis.nodes)
    try:
        index1 = sizer.calculators.conditionFirstOccurrenceIndex(times, output > 1.66) # first index above 10%
        index2 = sizer.calculators.conditionFirstOccurrenceIndex(times, output > 1.74) # first index above 90%
        slicedTimes = times[index1 - 1: index2 + 1]
        slicedOutput = output[index1 - 1: index2 + 1]
        slewRate = np.max(np.abs(np.diff(slicedOutput) / np.diff(slicedTimes))) # maximum absolute derivative
        return np.maximum(0, (10e+6 - slewRate) / 10e+6) ** 2
    except:
        print("slew rate undefined")
        return 1

def overshootLoss(circuit): # overshoot no more than 0.1 * delta
    analysis = circuit.getTransientModel(start=0.4e-6, end=0.6e-6, points=50)
    output = circuit.getOutput(analysis.nodes)
    return np.maximum(0, (np.max(output) - 1.76) / 1.76) ** 2

def loss(circuit):
    ac = circuit[0]
    tran = circuit[1]
    return np.sum([phaseMarginLoss(ac), gainLoss(ac), bandwidthLoss(ac), slewRateLossByRisingTime(tran), overshootLoss(tran)])

bounds = {
    w: [0.5e-6, 100e-6] for w in ["w12", "w34", "w5", "w6", "w7", "w8"]
}

bounds.update({
    l: [0.35e-6, 50e-6] for l in ["l12", "l34", "l5", "l6", "l7", "l8"]
})

bounds.update({
    "cm": [1e-12, 10e-12]
})

# optimizer = sizer.optimizers.Optimizer(templates, loss, bounds, earlyStopLoss=0)
optimizer = sizer.optimizers.ScipyMinimizeOptimizer(templates, loss, bounds, earlyStopLoss=0)
# optimizer = sizer.optimizers.PyswarmParticleSwarmOptimizer(templates, loss, bounds, earlyStopLoss=0)
start = time.time()
circuits = optimizer.run() # optimal circuits are returned in a list
end = time.time()
print()
print("finished in", end - start, "s")
print("-" * 25)
ac = circuits[0]
tran = circuits[1]
print(ac.netlist)
print("-" * 25)
print("optimal parameters", dict(zip(templates.parameters, ac.parameters)))
print("-" * 25)
print("total loss:", loss(circuits))
print("bandwidth:", ac.bandwidth)
print("ugf:", ac.unityGainFrequency)
print("gain:", ac.gain)
print("phase margin:", ac.phaseMargin)
# print("slew rate:", tran.slewRate)
analysis = tran.getTransientModel(0.4e-6, 0.6e-6, 100)
transientTime = np.array(analysis.time)
transientInput = tran.getInput(analysis.nodes)
transientOutput = tran.getOutput(analysis.nodes)
print("slew rate by rising time:", (1.74 - 1.66) / sizer.calculators.risingTime(transientTime, transientOutput, 1.66, 1.74))
# exit()

import matplotlib.pyplot as plt

plt.rcParams["axes.grid"] = True

frequencies, frequencyResponse = ac.getFrequencyResponse()

plt.subplot(311)
plt.plot(frequencies, np.abs(frequencyResponse))
plt.xscale("log")
plt.yscale("log")
plt.vlines(sizer.calculators.unityGainFrequency(frequencies, frequencyResponse), 0, 1e+3)

plt.subplot(312)
phaseResponse = np.angle(frequencyResponse, deg=True)
phaseResponse[np.where(phaseResponse > 0)] -= 360
plt.plot(frequencies, phaseResponse)
plt.xscale("log")
plt.vlines(sizer.calculators.unityGainFrequency(frequencies, frequencyResponse), -180, 0)

plt.subplot(313)
plt.plot(transientTime, transientInput)
plt.plot(transientTime, transientOutput)

plt.show()