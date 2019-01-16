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
        circuit = self.circuitTemplate(parameters) # compatible to CircuitTemplateList
        loss = self.loss(circuit)
        end = time.time() # 0.1 us
        print(f"\r total loss: {loss:10.5f}, {end - start:5.4f}s per seed", end=" ") # 9 us
        if loss <= self.earlyStopLoss:
            raise EarlyStopLossReached("loss {} already reaches early stop loss {}.".format(loss, self.earlyStopLoss), circuit=circuit)
        return loss

    def _run(self):
        raise NotImplementedError("this method should be implemented by a subclass.")

    def run(self):
        try:
            # sol = self._run()
            optimalParameters = self._run()
            return self.circuitTemplate(optimalParameters) # compatible to CircuitTemplateList
        except EarlyStopLossReached as e:
            traceback.print_exc()
            return e.circuit

class ScipyDifferentialEvolutionOptimizer(BaseOptimizer):

    def _checkpoint(self):
        pass

    def _run(self):
        return scipy.optimize.differential_evolution(self._loss, self._bounds, disp=True).x

class ScipyNativeBoundedMinimizeOptimizer(BaseOptimizer):

    def _run(self):
        return scipy.optimize.minimize(self._loss, x0=self._bounds[..., 0], bounds=self._bounds).x

ScipyMinimizeOptimizer = ScipyNativeBoundedMinimizeOptimizer

class ScipyFakeBoundedMinimizeOptimizer(BaseOptimizer):

    def _run(self):
        return scipy.optimize.minimize(self._loss, x0=self._bounds[..., 0]).x
    
    def _loss(self, parameters):
        if np.any((parameters > self._bounds[:, 1]) | (parameters < self._bounds[:, 0])):
            return np.inf
        else:
            return super()._loss(parameters)

class ScipySHGOOptimizer(BaseOptimizer):

    def _run(self):
        return scipy.optimize.shgo(self._loss, bounds=self._bounds).x

class ScipyDualAnnealingOptimizer(BaseOptimizer):

    def _run(self):
        return scipy.optimize.dual_annealing(self._loss, bounds=self._bounds).x

class ScipyBasinHoppingOptimizer(BaseOptimizer):

    def _run(self):
        return scipy.optimize.basinhopping(self._loss, x0=self._bounds[..., 0], minimizer_kwargs=dict(bounds=self._bounds)).x

Optimizer = ScipyDifferentialEvolutionOptimizer

class PyswarmParticleSwarmOptimizer(BaseOptimizer):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.pyswarm = __import__("pyswarm")

    def _run(self):
        return self.pyswarm.pso(self._loss, self._bounds[:, 0], self._bounds[:, 1])[0]

# class ScikitOptimizeBayesianOptimizer(BaseOptimizer):
#     def __init__(self, *args, **kwds):
#         super().__init__(*args, **kwds)
#         self.skopt = __import__("skopt")

#     def _run(self):
#         return self.skopt.gp_minimize(self._loss, self._bounds, noise=0).x