import scipy.optimize
import numpy as np
import sizer
# print(dir())
# from . import Circuit
import time
import traceback

class EarlyStopLossReached(Exception):
    def __init__(self, *args, circuit, **kwds):
        super().__init__(*args, **kwds)
        self.circuit = circuit

class BaseOptimizer:
    def __init__(self, circuitTemplate, loss, bounds, earlyStopLoss=-np.inf):
        self.circuitTemplate = circuitTemplate
        self.loss = loss
        self.bounds = bounds
        self.earlyStopLoss = earlyStopLoss

        self._bounds = np.array([self.bounds[i] for i in self.circuitTemplate.parameters])

    def _loss(self, parameters):
        start = time.time() # 0.1 us
        circuit = sizer.Circuit(self.circuitTemplate, parameters)
        loss = self.loss(circuit)
        end = time.time() # 0.1 us
        print("\r total loss:", loss, ",", end - start, "s per seed", end=" ") # 9 us
        if loss <= self.earlyStopLoss:
            raise EarlyStopLossReached("loss {} already reaches early stop loss {}.".format(loss, self.earlyStopLoss), circuit=circuit)
        return loss

    def _run(self):
        raise NotImplementedError("this method should be implemented by a subclass.")

    def run(self):
        try:
            sol = self._run()
            optimalParameters = sol.x
            result = dict(zip(self.circuitTemplate.parameters, optimalParameters))
            return sizer.Circuit(self.circuitTemplate, sol.x)
        except EarlyStopLossReached as e:
            traceback.print_exc()
            return e.circuit

class ScipyDifferentialEvolutionOptimizer(BaseOptimizer):

    def _checkpoint(self):
        pass

    def _run(self):
        return scipy.optimize.differential_evolution(self._loss, self._bounds, disp=True)

class ScipyMinimizeOptimizer(BaseOptimizer):

    def _run(self):
        return scipy.optimize.minimize(self._loss, x0=self._bounds[..., 0], bounds=self._bounds)

Optimizer = ScipyDifferentialEvolutionOptimizer