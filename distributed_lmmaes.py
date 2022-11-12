"""
This is a simple version of the outer-es part of our D-LMMAES algorithm
"""
import numpy as np

from pypoplib.es import ES


class DistributedES(ES):
    """Distributed (Meta-) Evolution Strategies (DES).
    """
    def __init__(self, problem, options):
        ES.__init__(self, problem, options)
        self._customized_class = None  # set by the wrapper
        self.n_islands = options.get('n_islands')  # number of inner ESs
        self.island_max_runtime = options.get('island_max_runtime', 3 * 60)  # for inner ESs
        self.n_better_islands = int(np.maximum(5, self.n_islands / 5))  # for outer ES
        w_base, w = np.log((self.n_better_islands * 2 + 1) / 2), np.log(np.arange(self.n_better_islands) + 1)
        self._dw = (w_base - w) / (self.n_better_islands * w_base - np.sum(w))
        self.max_runtime = options.get('max_runtime', 3600 * 2)
        # to ensure that actual runtime does not exceed 'max_runtime' as much as possible
        self.max_runtime -= (self.island_max_runtime + 60)
        # for outer ES (or for online hyper-parameter optimization)
        self.sigma_scale = [0.5, 1, 1.5, 2, 5, 10, 20]
        self.learning_ratios = np.linspace(0, 1, 11)
        self.sl = []
        for i in self.sigma_scale:
            for j in self.learning_ratios:
                self.sl.append([i, j])
        self.is_first_generation = True
        self.x = self.rng_initialization.uniform(self.initial_lower_boundary,
                                            self.initial_upper_boundary,
                                            size=(self.n_islands, self.ndim_problem))
        self.best_x, self.best_y = np.zeros((self.n_islands, self.ndim_problem)), np.zeros((self.n_islands,))
        self.n_evolution_paths = 4 + int(3 * np.log(self.ndim_problem))
        self.s = np.zeros((self.n_islands, self.ndim_problem))  # for mutation strengths of all inner ESs
        self.tm = np.zeros((self.n_islands, self.n_evolution_paths, self.ndim_problem))  # transform matrices of all inner ESs
        self.c_s = (2 * self.n_individuals / self.ndim_problem) * np.ones((self.n_islands,))
        self.sigmas = 0.3 * np.ones((self.n_islands,))  # mutation strengths of all inner ESs
        self.n_low_dim = 4 * len(self.sigma_scale) + 2 * len(self.learning_ratios)

    def get_options(self):
        """
        Return some options of the outer-es algorithm
        """
        results = []
        for p in range(self.n_islands):
            option = {'x': self.best_x[p],
                      's': self.s[p],
                      'tm': self.tm[p],
                      'c_s': self.c_s[p],
                      'sigma': self.sigmas[p]
                      }
            results.append(option)
        return results

    def iterate(self, args=None):
        """
        Iteration to renew the parameters of the ouyer-es
        """
        order = np.argsort(self.best_y)
        index_1, index_2, index_3, index_4, index_5, index_6 = 0, 0, 0, 0, 0, 0
        w_x = np.zeros((self.ndim_problem,))
        w_s = np.zeros((self.ndim_problem,))
        w_tm = np.zeros((self.n_evolution_paths, self.ndim_problem))
        w_c_s = 0
        w_sigma = 0
        for k in range(self.n_better_islands):
            w_x += self._dw[k] * self.best_x[order[k]]
            w_s += self._dw[k] * self.s[order[k]]
            w_tm += self._dw[k] * self.tm[order[k]]
            w_c_s += self._dw[k] * self.c_s[order[k]]
            w_sigma += self._dw[k] * self.sigmas[order[k]]
        for p in range(self.n_islands):
            index = order[-(p + 1)]
            self.best_x[index], self.s[index], self.tm[index], self.c_s[index], self.sigmas[index] = w_x, w_s, w_tm, w_c_s, w_sigma
            if p < len(self.sigma_scale):
                index_1 += 1
                self.sigmas[index] = w_sigma * self.sigma_scale[index_1 - 1]
            elif p < 2 * len(self.sigma_scale):
                index_2 += 1
                self.sigmas[index] = w_sigma * self.sigma_scale[index_2 - 1]
            elif p < 3 * len(self.sigma_scale):
                index_3 += 1
                self.tm[index] = np.zeros((self.n_evolution_paths, self.ndim_problem))
                self.sigmas[index] = w_sigma * self.sigma_scale[index_3 - 1]
            elif p < 4 * len(self.sigma_scale):
                index_4 += 1
                self.tm[index] = np.zeros((self.n_evolution_paths, self.ndim_problem))
                self.sigmas[index] = w_sigma * self.sigma_scale[index_4 - 1]
            elif p < 4 * len(self.sigma_scale) + len(self.learning_ratios):
                index_5 += 1
                self.c_s[index] = self.learning_ratios[index_5 - 1]
            elif p < 4 * len(self.sigma_scale) + 2 * len(self.learning_ratios):
                index_6 += 1
                self.c_s[index] = self.learning_ratios[index_6 - 1]
            elif p < self.n_low_dim + len(self.sl):
                pp = p - self.n_low_dim
                self.sigmas[index] = w_sigma * self.sl[pp][0]
                self.c_s[index] = self.sl[pp][1]
            if self.is_first_generation:  # only for the first generation
                self.best_x[p] = self.x[p]  # each island is initialized randomly
        results = []
        for p in range(self.n_islands):
            option = {'x': self.best_x[p],
                       's': self.s[p],
                       'tm': self.tm[p],
                       'c_s': self.c_s[p],
                       'sigma': self.sigmas[p]
                       }
            results.append(option)
        return results

    def renew_factors(self, factor_options):
        """
        Renew the facter of outer-ES part
        """
        for i in range(len(factor_options)):
            self.best_y[i] = factor_options[i].y
            self.best_x[i] = factor_options[i].x
            self.s[i] = factor_options[i].s
            self.tm[i] = factor_options[i].tm
            self.c_s[i] = factor_options[i].c_s
            self.sigmas[i] = factor_options[i].sigma

