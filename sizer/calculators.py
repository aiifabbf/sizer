import scipy.optimize
import scipy.interpolate
import numpy as np

import functools

class CalculationError(Exception):
    pass

def bandwidth(frequenciesInHertz, frequencyResponse, initialGuess=1e+3):
    """Calculate the frequency at which the absolute value of frequency response drops to 1 / sqrt(2) of its value at 1 Hz.

    Attributes
    ----------

    frequenciesInHertz : 1-D ndarray
        Frequency points in Hz
    frequencyResponse : 1-D ndarray
        Frequency response points, given as an array of complex numbers
    initialGuess : float or int
        Initial guess `x0` for the root finder. Providing reasonable and highly likely initial guess can speed up root finding.

    Frequency response is first interpolated with linear B-spline and then sent to a root finder.
    """
    amplitudeResponse = np.abs(frequencyResponse)
    amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, amplitudeResponse, bounds_error=False) # interpolate amplitude response with linear b-spline
    amplitudeAt1Hz = amplitudeResponseInterpolated(1) # get amplitude response at 1 Hz
    amplitudeAtBandwidth = amplitudeAt1Hz / np.sqrt(2)
    # todo
    try:
        firstOutsideBandwidthFrequency = np.min(np.where(amplitudeResponse < amplitudeAtBandwidth))
        amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz[firstOutsideBandwidthFrequency - 1: firstOutsideBandwidthFrequency + 1], amplitudeResponse[firstOutsideBandwidthFrequency - 1: firstOutsideBandwidthFrequency + 1], bounds_error=False) # interpolate amplitude response with linear b-spline
    # if np.any(amplitudeResponse <= amplitudeAt1Hz / np.sqrt(2)): # check if there exists a point below -3dB
        return scipy.optimize.root(lambda x: amplitudeResponseInterpolated(x) - amplitudeAtBandwidth, frequenciesInHertz[firstOutsideBandwidthFrequency - 1]).x[0]
    # else: # if there is no amplitude below -3dB, then no need to compute
    except:
        raise CalculationError("impossible to calculate bandwidth, because the data contains no amplitude point that is below 1 / sqrt(2) times the amplitude at 1 Hz. Try simulating with wider frequency range, or this circuit does not have a bandwidth at all. Amplitude at 1 Hz is {}. Amplitude at {} Hz is {}".format(amplitudeAt1Hz, frequenciesInHertz[-1], amplitudeResponse[-1]))

def unityGainFrequency(frequenciesInHertz, frequencyResponse, initialGuess=1e+3): # 1 ms, special thanks to @HereDrlv
    """Calculate the frequency at which the absolute value of frequency response drops to 1.

    Attributes
    ----------

    frequenciesInHertz : 1-D ndarray
        Frequency points in Hz
    frequencyResponse : 1-D ndarray
        Frequency response points, given as an array of complex numbers
    initialGuess : float or int
        Initial guess `x0` for the root finder. Providing reasonable and highly likely initial guess can speed up root finding.

    Frequency response is first interpolated with linear B-spline and then sent to a root finder.
    """
    amplitudeResponse = np.abs(frequencyResponse)
    try:
        firstBelowUnityIndex = np.min(np.where(amplitudeResponse < 1))
        amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz[firstBelowUnityIndex - 1: firstBelowUnityIndex + 1], amplitudeResponse[firstBelowUnityIndex - 1: firstBelowUnityIndex + 1], bounds_error=False)
        # amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, amplitudeResponse, bounds_error=False)
        return scipy.optimize.root(lambda x: amplitudeResponseInterpolated(x) - 1, frequenciesInHertz[firstBelowUnityIndex - 1]).x[0]
    except:
        raise CalculationError("impossible to calculate the unity gain frequency, because the data contains no amplitude point that is less than or equals 1. Try simulating with wider frequency range, or this circuit does not reach unity gain at all.")

def positiveFeedbackFrequency(frequenciesInHertz, frequencyResponse, initialGuess=1e+3):
    """Calculate the frequency in Hertz at which the phase drops to -180deg.

    Attributes
    ----------

    frequenciesInHertz : 1-D ndarray
        Frequency points in Hz
    frequencyResponse : 1-D ndarray
        Frequency response points, given as an array of complex numbers
    initialGuess : float or int
        Initial guess `x0` for the root finder. Providing reasonable and highly likely initial guess can speed up root finding.
    """
    phaseResponse = np.angle(frequencyResponse, deg=True)
    phaseResponse[np.where(phaseResponse > 0)] -= 360
    try:
        firstBelowNegative180degIndex = np.min(np.where(phaseResponse < -180))
        # todo
        phaseResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz[firstBelowNegative180degIndex - 1: firstBelowNegative180degIndex + 1], phaseResponse[firstBelowNegative180degIndex - 1: firstBelowNegative180degIndex + 1], bounds_error=False)
        return scipy.optimize.root(lambda x: phaseResponseInterpolated(x) + 180, frequenciesInHertz[firstBelowNegative180degIndex - 1]).x[0]
    except:
        raise CalculationError("impossible to calculate the frequency at which phase drops to -180deg, either because the circuit does not reach -180deg at all, or because simulation frequency range is not wide enough.")

def phaseMargin(frequenciesInHertz, frequencyResponse):
    """Calculate the phase margin in degree.

    Attributes
    ----------

    frequenciesInHertz : 1-D ndarray
        Frequency points in Hz
    frequencyResponse : 1-D ndarray
        Frequency response points, given as an array of complex numbers

    Frequency response is first sent to `unityGainFrequency()` to calculate the unity gain frequency, and then frequency response is interpolated with linear B-spline and substituted with unity gain frequency.
    """
    ugf = unityGainFrequency(frequenciesInHertz, frequencyResponse)
    phaseResponse = np.angle(frequencyResponse, deg=True)
    # Note that `np.angle()` returns angles in (-180deg, 180deg], so any phase response that are below -180deg will be returned as if added 360deg, leaving a gap. However, in real practice, phases within (-180deg, -360deg) is drawn below not above to avoid the gap.
    # Attempt to fix this with naive approach.
    phaseResponse[np.where(phaseResponse > 0)] -= 360
    if np.any(phaseResponse <= -180):
        # todo
    # try:
        # _ = np.min(np.where(phaseResponse < -180))
        phaseResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, phaseResponse, bounds_error=False)
        return 180 - np.abs(phaseResponseInterpolated(ugf))
    else:
    # except:
        raise CalculationError("impossible to calculate the phase margin, either because this circuit never reaches unity gain (which means PM makes no sense) or your simulation data is insufficient. Try simulating with wider frequency range.")

def gainMargin(frequenciesInHertz, frequencyResponse):
    """Calculate the gain margin (not in dB)

    Attributes
    ----------

    frequenciesInHertz : 1-D ndarray
        Frequency points in Hz
    frequencyResponse : 1-D ndarray
        Frequency response points, given as an array of complex numbers
    """
    amplitudeResponse = np.abs(frequencyResponse)
    amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, amplitudeResponse, bounds_error=False)
    return 1 - amplitudeResponseInterpolated(positiveFeedbackFrequency(frequenciesInHertz, frequencyResponse))

def gain(frequenciesInHertz, frequencyResponse):
    """Calculate the gain at 1 Hz, return as a complex number
    """
    try:
        return scipy.interpolate.interp1d(frequenciesInHertz, frequencyResponse)(1)
    except:
        raise CalculationError("impossible to calculate the DC gain because the data does not contain gain at 1 Hz.")

def slewRate(time, response):
    return np.max(np.abs(np.diff(response) / np.diff(time)))