import scipy.optimize
import scipy.interpolate
import numpy as np

class CalculationError(Exception):
    pass

def bandwidth(frequenciesInHertz, frequencyResponse, initialGuess=1e+3):
    """
    Calculate the frequency at which the absolute value of frequency response drops to 1 / sqrt(2) of its value at 1 Hz.

    Frequencies should be given as an 1-D array in Hertz, and frequency response should be given as an array of complex numbers with the same shape.

    Frequency response is first interpolated with linear B-spline and then sent to a root finder.
    """
    amplitudeResponse = np.abs(frequencyResponse)
    amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, amplitudeResponse, kind="linear")
    amplitudeAt1Hz = amplitudeResponseInterpolated(1)
    if np.any(amplitudeResponse <= amplitudeAt1Hz / np.sqrt(2)):
        return scipy.optimize.root(lambda x: amplitudeResponseInterpolated(x) - amplitudeAt1Hz / np.sqrt(2), initialGuess).x[0]
    else:
        raise CalculationError("impossible to calculate bandwidth, because the data contains no amplitude point that is below 1 / sqrt(2) times the amplitude at 1 Hz. Try simulating with wider frequency range, or this circuit does not have a bandwidth at all.")

def unityGainFrequency(frequenciesInHertz, frequencyResponse, initialGuess=1e+3):
    """
    Calculate the frequency at which the absolute value of frequency response drops to 1.

    Frequencies should be given as an 1-D array in Hertz, and frequency response should be given as an array of complex numbers with the same shape.

    Frequency response is first interpolated with linear B-spline and then sent to a root finder.
    """
    amplitudeResponse = np.abs(frequencyResponse)
    if np.any(amplitudeResponse <= 1):
        amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, amplitudeResponse, kind="linear")
        return scipy.optimize.root(lambda x: amplitudeResponseInterpolated(x) - 1, initialGuess).x[0]
    else:
        raise CalculationError("impossible to calculate the unity gain frequency, because the data contains no amplitude point that is less than or equals 1. Try simulating with wider frequency range, or this circuit does not reach unity gain at all.")

def positiveFeedbackFrequency(frequenciesInHertz, frequencyResponse, initialGuess=1e+3):
    """
    Calculate the frequency in Hertz at which the phase drops to -180deg.
    """
    phaseResponse = np.angle(frequencyResponse, deg=True)
    phaseResponse[np.where(phaseResponse > 0)] -= 360
    if np.any(phaseResponse <= -180):
        phaseResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, phaseResponse, kind="linear")
        return scipy.optimize.root(lambda x: phaseResponseInterpolated(x) + 180, initialGuess).x[0]
    else:
        raise CalculationError("impossible to calculate the frequency at which phase drops to -180deg, either because the circuit does not reach -180deg at all, or because simulation frequency range is not wide enough.")

def phaseMargin(frequenciesInHertz, frequencyResponse):
    """
    Calculate the phase margin in degree.

    Frequencies should be gives as an 1-D array in Hertz, and frequency response should be given as an array of complex numbers with the same shape.

    Frequency response is first sent to `unityGainFrequency()` to calculate the unity gain frequency, and then frequency response is interpolated with linear B-spline and substituted with unity gain frequency.
    """
    ugf = unityGainFrequency(frequenciesInHertz, frequencyResponse)
    phaseResponse = np.angle(frequencyResponse, deg=True)
    # Note that `np.angle()` returns angles in (-180deg, 180deg], so any phase response that are below -180deg will be returned as if added 360deg, leaving a gap. However, in real practice, phases within (-180deg, -360deg) is drawn below not above to avoid the gap.
    # Attempt to fix this with naive approach.
    phaseResponse[np.where(phaseResponse > 0)] -= 360
    if np.any(phaseResponse <= -180):
        phaseResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, phaseResponse, kind="linear")
        return 180 - np.abs(phaseResponseInterpolated(ugf))
    else:
        raise CalculationError("impossible to calculate the phase margin, either because this circuit never reaches unity gain (which means PM makes no sense) or your simulation data is insufficient. Try simulating with wider frequency range.")

def gainMargin(frequenciesInHertz, frequencyResponse):
    """
    Calculate the gain margin (not in dB)
    """
    amplitudeResponse = np.abs(frequencyResponse)
    amplitudeResponseInterpolated = scipy.interpolate.interp1d(frequenciesInHertz, amplitudeResponse, kind="linear")
    return 1 - amplitudeResponseInterpolated(positiveFeedbackFrequency(frequenciesInHertz, frequencyResponse))