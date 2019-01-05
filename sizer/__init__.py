from PySpice.Spice.Parser import SpiceParser

import sizer.calculators
import sizer.optimizers
import numpy as np

import string
import logging
import traceback
import functools

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

class Circuit:
    def __init__(self, circuitTemplate, parameters):
        """A determined circuit with parameters all specified

        Attributes
        ----------

        circuitTemplate : CircuitTemplate object
            the template from which the circuit is instantiated
        parameters : list or 1-D ndarray
            numeric parameters that will be substituted for those undetermined parameters in the circuit template
        """

        self.circuitTemplate = circuitTemplate
        self.parameters = parameters

        try:
            mapping = dict(zip(self.circuitTemplate.parameters, parameters))
            self.netlist = self.circuitTemplate.netlist.format(**mapping)
        except:
            traceback.print_exc()
            raise ValueError("insufficient number of parameters")

        self._circuit = SpiceParser(source=self.netlist).build_circuit()
        self._circuit.raw_spice += self.circuitTemplate.rawSpice
        self._simulator = self._circuit.simulator(simulator="ngspice-subprocess")

        # self._cached = {}

    @functools.lru_cache() # This boosts performance...
    def frequencyResponse(self, start=1, end=1e+9, points=10, variation="dec"):
        analysis = self._simulator.ac(start_frequency=start, stop_frequency=end, number_of_points=points, variation=variation)
        frequencies = np.array(analysis.frequency)

        if "Vout" in analysis.nodes:
            vout = analysis.nodes["Vout"]
        elif "vout" in analysis.nodes:
            vout = analysis.nodes["vout"]
        elif "Vo" in analysis.nodes:
            vout = analysis.nodes["Vo"]
        elif "vo" in analysis.nodes:
            vout = analysis.nodes["vo"]
        else:
            raise KeyError("no V_o node found. Tried `Vout`, `vout`, `Vo`, `vo`.")

        vout = np.array(vout)
        
        if "Vin+" in analysis.nodes:
            vin = analysis.nodes["Vin+"] - analysis.nodes["Vin-"]
        elif "vin+" in analysis.nodes:
            vin = analysis.nodes["vin+"] - analysis.nodes["vin-"]
        elif "Vi+" in analysis.nodes:
            vin = analysis.nodes["Vi+"] - analysis.nodes["Vi-"]
        elif "vi+" in analysis.nodes:
            vin = analysis.nodes["vi+"] - analysis.nodes["vi-"]
        elif "Vin" in analysis.nodes:
            vin = analysis.nodes["Vin"]
        elif "vin" in analysis.nodes:
            vin = analysis.nodes["vin"]
        elif "Vi" in analysis.nodes:
            vin = analysis.nodes["Vi"]
        elif "vi" in analysis.nodes:
            vin = analysis.nodes["vi"]
        elif "Vp" in analysis.nodes:
            vin = analysis.nodes["Vp"] - analysis.nodes["Vn"]
        elif "vp" in analysis.nodes:
            vin = analysis.nodes["vp"] - analysis.nodes["vn"]
        else:
            raise KeyError("no V_i node found. Tried `Vin+`, `vin+`, `Vi+`, `vi+`, `Vin`, `vin, `Vi`, `vi`, `Vp`, `vp`.")
        
        vin = np.array(vin)

        return (frequencies, vout / vin)

    @property
    def bandwidth(self):
        frequencyResponse = self.frequencyResponse()
        return sizer.calculators.bandwidth(frequencyResponse[0], frequencyResponse[1])

    @property
    def phaseMargin(self):
        frequencyResponse = self.frequencyResponse()
        return sizer.calculators.phaseMargin(frequencyResponse[0], frequencyResponse[1])

    @property
    def gainMargin(self):
        frequencyResponse = self.frequencyResponse()
        return sizer.calculators.gainMargin(frequencyResponse[0], frequencyResponse[1])

    @property
    def unityGainFrequency(self):
        frequencyResponse = self.frequencyResponse()
        return sizer.calculators.unityGainFrequency(frequencyResponse[0], frequencyResponse[1])

    @property
    def gain(self):
        frequencyResponse = self.frequencyResponse()
        return sizer.calculators.gain(frequencyResponse[0], frequencyResponse[1])