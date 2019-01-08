from PySpice.Spice.Parser import SpiceParser

import sizer.calculators
import sizer.optimizers
import numpy as np

import string
import logging
import traceback
import functools

import os

class CircuitTemplate:
    def __init__(self, netlist, rawSpice=""):
        """An undetermined circuit with placeholders

        Attributes
        ----------

        netlist : str
            SPICE netlist string, may contain template placeholders delimited within `{` and `}` following Python's string formatter conventions.
        """
        self.netlist = netlist
        logging.debug("Circuit template:\n {}".format(self.netlist))

        self.formatter = string.Formatter()
        self.parameters = list(set(i[1] for i in string.Formatter.parse(self.formatter, self.netlist) if i[1]))
        logging.debug("{} parameters found in netlist: {}".format(len(self.parameters), self.parameters))
        
        self.rawSpice = rawSpice

    def __call__(self, parameters):
        return Circuit(self, parameters)

class CircuitTemplates(list):
    def __call__(self, parameters):
        return list(Circuit(i, parameters) for i in self)

class Circuit:
    parser = SpiceParser(source=".title" + os.linesep + ".end") # 1.28 ms -> 65 us
    def __init__(self, circuitTemplate, parameters):
        """A determined circuit with parameters all specified

        Attributes
        ----------

        circuitTemplate : CircuitTemplate object
            the template from which the circuit is instantiated
        parameters : list or 1-D ndarray
            numeric parameters that will be substituted for those undetermined parameters in the circuit template

        Properties
        ----------

        .circuitTemplate : CircuitTemplate object
            the template from which this circuit is instantiated
        .parameters : List
        """

        self.circuitTemplate = circuitTemplate
        self.parameters = parameters

        try:
            mapping = dict(zip(self.circuitTemplate.parameters, parameters))
            self._netlist = self.circuitTemplate.netlist.format(**mapping)
        except:
            traceback.print_exc()
            raise ValueError("insufficient number of parameters")

        self._circuit = self.parser.build_circuit()
        self._circuit.raw_spice += self._netlist
        self._circuit.raw_spice += self.circuitTemplate.rawSpice
        self._simulator = self._circuit.simulator(simulator="ngspice-subprocess")

        self.hints = dict(
            ac = dict(
                start = 1,
                end = 1e+9,
                variation = "dec"
            ),
            tran = dict(
                start = 0,
                end = 1e-3,
                points = 100
            )
        )

        # self._cached = {}

    def getInput(self, nodeList):
        if "vin+" in nodeList:
            vin = nodeList["vin+"] - nodeList["vin-"]
        elif "vi+" in nodeList:
            vin = nodeList["vi+"] - nodeList["vi-"]
        elif "vin" in nodeList:
            vin = nodeList["vin"]
        elif "vi" in nodeList:
            vin = nodeList["vi"]
        elif "vp" in nodeList:
            vin = nodeList["vp"] - nodeList["vn"]
        else:
            raise KeyError("no input voltage node found. Tried `Vin+`, `vin+`, `Vi+`, `vi+`, `Vin`, `vin, `Vi`, `vi`, `Vp`, `vp`.")

        return np.array(vin) # remove units

    def getOutput(self, nodeList):
        if "vout" in nodeList:
            vout = nodeList["vout"]
        elif "vo" in nodeList:
            vout = nodeList["vo"]
        else:
            raise KeyError("no output voltage node found. Tried `Vout`, `vout`, `Vo`, `vo`.")

        return np.array(vout) # remove units

    def getResponse(self, nodeList):
        # Looks like PySpice will turn all node name into their lower case.
        vout = self.getOutput(nodeList)
        vin = self.getInput(nodeList)
        return vout / vin

    @property
    def netlist(self):
        return self._netlist

    # Methods for manual usage. They ignore `self.hints`.
    @functools.lru_cache()
    def getTransientModel(self, start=0, end=1e-6, points=1000):
        return self._simulator.transient(start_time=start, end_time=end, step_time=(end - start) / points)

    @functools.lru_cache()
    def getTransientResponse(self, start=0, end=1e-6, points=1000):
        analysis = self.getTransientModel(start, end, points)
        time = np.array(analysis.time)

        return (time, self.getResponse(analysis.nodes))

    @functools.lru_cache()
    def getSmallSignalModel(self, start=1, end=1e+9, points=10, variation="dec"):
        """Do an AC small-signal simulation

        Attributes
        ----------

        start : real number
            simulation frequency range start
        end : real number
            simulation frequency range end
        points : integer
            - when `variation == "lin"`, number of points in total
            - when `variation == "dec"`, number of points per decade
            - when `variation == "oct"`, number of points per octave
        variation : str
            sampling frequency point arrangement. Use "dec" or "oct" if you plan to draw Bode plot later.

        Returns
        -------

        analysis : PySpice analysis object
        """
        return self._simulator.ac(start_frequency=start, stop_frequency=end, number_of_points=points, variation=variation)

    @functools.lru_cache() # This boosts performance...
    def getFrequencyResponse(self, start=1, end=1e+9, points=10, variation="dec"):
        # analysis = self._simulator.ac(start_frequency=start, stop_frequency=end, number_of_points=points, variation=variation)
        analysis = self.getSmallSignalModel(start, end, points, variation)
        frequencies = np.array(analysis.frequency)

        return (frequencies, self.getResponse(analysis.nodes))

    # High-level, convenient property-styled methods. These are affected by `self.hints`

    @property
    @functools.lru_cache(maxsize=1)
    def operationalPoint(self):
        return self._simulator.operating_point()

    @property
    @functools.lru_cache(maxsize=1)
    def staticPower(self):
        """static power, aka. absolute value of supply voltage multiplies by absolute value of current through supply."""
        op = self.operationalPoint

        if "vdd+" in op.nodes:
            vdd = np.abs(op.nodes["vdd+"] - op.nodes["vdd-"])
        elif "vcc+" in op.nodes:
            vdd = np.abs(op.nodes["vcc+"] - op.nodes["vcc-"])
        elif "vdd" in op.nodes:
            vdd = np.abs(op.nodes["vdd"])
        elif "vcc" in op.nodes:
            vdd = np.abs(op.nodes["vcc"])
        else:
            raise KeyError("no supply found. Tried `VDD+`, `VDD`, `VCC+`, `VCC` and their case-insensitive variants.")
        
        if "vdd" in op.branches:
            idd = np.abs(op.branches["vdd"])
        elif "v0" in op.branches:
            idd = np.abs(op.branches["v0"])
        else:
            raise KeyError("no supply found. Tried `VDD`, `V0` and their case-insensitive variants.")

        return np.float(vdd) * np.float(idd)

    dcPower = staticPower

    @property
    def bandwidth(self):
        frequencyResponse = self.getFrequencyResponse(**self.hints["ac"])
        return sizer.calculators.bandwidth(frequencyResponse[0], frequencyResponse[1])

    @property
    def phaseMargin(self):
        frequencyResponse = self.getFrequencyResponse(**self.hints["ac"])
        return sizer.calculators.phaseMargin(frequencyResponse[0], frequencyResponse[1])

    @property
    def gainMargin(self):
        frequencyResponse = self.getFrequencyResponse(**self.hints["ac"])
        return sizer.calculators.gainMargin(frequencyResponse[0], frequencyResponse[1])

    @property
    def unityGainFrequency(self):
        frequencyResponse = self.getFrequencyResponse(**self.hints["ac"])
        return sizer.calculators.unityGainFrequency(frequencyResponse[0], frequencyResponse[1])

    @property
    def gain(self):
        frequencyResponse = self.getFrequencyResponse(**self.hints["ac"])
        return sizer.calculators.gain(frequencyResponse[0], frequencyResponse[1])

    @property
    def slewRate(self):
        analysis = self.getTransientModel(**self.hints["tran"])
        return sizer.calculators.slewRate(np.array(analysis.time), np.array(self.getOutput(analysis.nodes)))