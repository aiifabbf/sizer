import unittest

import sys
sys.path.append(".")

import sizer.calculators

import numpy as np
import scipy.signal
import time

import matplotlib.pyplot as plt

plt.rcParams["axes.grid"] = True

frequencies = np.logspace(0, 9, 1000)
H = scipy.signal.lti([], [- 1e+3 * 2 * np.pi, - 1e+5 * 2 * np.pi, - 1e+8 * 2 * np.pi], 1e+3 * 1e+3 * 1e+5 * 1e+8 * (2 * np.pi) ** 3)

frequencyResponse = H.freqresp(frequencies * 2 * np.pi)[1]

class PerformanceTest(unittest.TestCase):
    def testBandwidth(self):
        times = 1000
        start = time.time()
        for i in range(times):
            print(sizer.calculators.bandwidth(frequencies, frequencyResponse), end="\r")

        end = time.time()
        print("Calculated", times, "bandwidth for", end - start, "with", (end - start) / times, "each.")

    def testUnityGainFrequency(self):
        times = 1000
        start = time.time()
        for i in range(times):
            print(sizer.calculators.unityGainFrequency(frequencies, frequencyResponse), end="\r")

        end = time.time()
        print("Calculated", times, "unity gain frequencies for", end - start, "with", (end - start) / times, "each.")

    def testPhaseMargin(self):
        times = 1000
        start = time.time()
        for i in range(times):
            print(sizer.calculators.phaseMargin(frequencies, frequencyResponse), end="\r")
        end = time.time()
        print("Calculated", times, "phase margin for", end - start, "with", (end - start) / times, "each.")

class ValidnessTest(unittest.TestCase):
    def testBandwidth(self):
        print("Theoretical bandwidth is", 1e+3)
        print("Calculated bandwidth is", sizer.calculators.bandwidth(frequencies, frequencyResponse))
        plt.plot(frequencies, np.abs(frequencyResponse))
        plt.xscale("log")
        plt.yscale("log")
        plt.show()

    def testUnityGainFrequency(self):
        # print("Theoretical UGF is", 1e+3)
        print("Calculated UGF is", sizer.calculators.unityGainFrequency(frequencies, frequencyResponse))
        plt.plot(frequencies, np.abs(frequencyResponse))
        plt.xscale("log")
        plt.yscale("log")
        plt.show()

    def testPhaseMargin(self):
        print("Calculated PM is", sizer.calculators.phaseMargin(frequencies, frequencyResponse))
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

    def testGainMargin(self):
        print("Calculated GM is", sizer.calculators.gainMargin(frequencies, frequencyResponse))
        plt.subplot(211)
        plt.plot(frequencies, np.abs(frequencyResponse))
        plt.xscale("log")
        plt.yscale("log")
        plt.vlines(sizer.calculators.positiveFeedbackFrequency(frequencies, frequencyResponse), 0, 1e+3)

        plt.subplot(212)
        phaseResponse = np.angle(frequencyResponse, deg=True)
        phaseResponse[np.where(phaseResponse > 0)] -= 360
        plt.plot(frequencies, phaseResponse)
        plt.xscale("log")
        plt.vlines(sizer.calculators.positiveFeedbackFrequency(frequencies, frequencyResponse), -180, 0)
        plt.show()

    def testSlewRate(self):
        time = np.linspace(0, 1e-3, 1000)
        response = scipy.signal.step(H, T=time)
        print("Calculated slew rate is", sizer.calculators.slewRate(time, response))
        plt.plot(*response)
        plt.show()