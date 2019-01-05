import scipy.optimize
import numpy as np
import sizer
# print(dir())
# from . import Circuit
import time
import traceback

class BaseOptimizer:
    def __init__(self, circuitTemplate, loss, bounds, earlyStopLoss=None):
        self.circuitTemplate = circuitTemplate
        self.loss = loss
        self.bounds = bounds
        self.earlyStopLoss = earlyStopLoss

        self._bounds = np.array([self.bounds[i] for i in self.circuitTemplate.parameters])

    def _loss(self, parameters):
        start = time.time()
        circuit = sizer.Circuit(self.circuitTemplate, parameters)
        loss = self.loss(circuit)
        end = time.time()
        print("\r total loss:", loss, ",", end - start, "s per seed", end=" ")
        return loss

class ScipyDifferentialEvolutionOptimizer(BaseOptimizer):

    def _checkpoint(self):
        pass

    def run(self):
        try:
            sol = scipy.optimize.differential_evolution(self._loss, self._bounds, disp=True)
        except:
            traceback.print_exc()
        result = dict(zip(self.circuitTemplate.parameters, sol.x))
        return sizer.Circuit(self.circuitTemplate, sol.x)

class ScipyMinimizeOptimizer(BaseOptimizer):

    def run(self):
        sol = scipy.optimize.minimize(self._loss, x0=self._bounds[..., 0], bounds=self._bounds)
        result = dict(zip(self.circuitTemplate.parameters, sol.x))
        return sizer.Circuit(self.circuitTemplate, sol.x)

Optimizer = ScipyDifferentialEvolutionOptimizer