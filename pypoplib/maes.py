import numpy as np

from pypoplib.es import ES


class MAES(ES):
    """Matrix Adaptation Evolution Strategy (MAES).

    .. note:: `MAES` is an interesting *simplified* version of the well-established `CMA-ES` but nearly without
       significant performance loss, designed carefully by `Beyer <https://homepages.fhv.at/hgb/>`_ and `Sendhoff
       <https://tinyurl.com/26szwuaa>`_. One obvious advantage of such a simplification is to help better understand
       the underlying working principles (e.g., **invariance** and **unbias**) of `CMA-ES`, which is often thought to
       be rather complex for newcomers.

       It is **highly recommended** to first attempt other more advanced ES variants (e.g., `LMCMA`, `LMMAES`) for
       large-scale black-box optimization, since `MAES` has a *cubic* time complexity w.r.t. each sampling. Note that
       another improved version called `FMAES` provides a *relatively more efficient* implementation for `MAES` with
       *quadratic* time complexity w.r.t. each sampling.

    Parameters
    ----------
    problem : dict
              problem arguments with the following common settings (`keys`):
                * 'fitness_function' - objective function to be **minimized** (`func`),
                * 'ndim_problem'     - number of dimensionality (`int`),
                * 'upper_boundary'   - upper boundary of search range (`array_like`),
                * 'lower_boundary'   - lower boundary of search range (`array_like`).
    options : dict
              optimizer options with the following common settings (`keys`):
                * 'max_function_evaluations' - maximum of function evaluations (`int`, default: `np.Inf`),
                * 'max_runtime'              - maximal runtime to be allowed (`float`, default: `np.Inf`),
                * 'seed_rng'                 - seed for random number generation needed to be *explicitly* set (`int`);
              and with the following particular settings (`keys`):
                * 'sigma'         - initial global step-size, aka mutation strength (`float`),
                * 'mean'          - initial (starting) point, aka mean of Gaussian search distribution (`array_like`),

                  * if not given, it will draw a random sample from the uniform distribution whose search range is
                    bounded by `problem['lower_boundary']` and `problem['upper_boundary']`.

                * 'n_individuals' - number of offspring, aka offspring population size (`int`, default:
                  `4 + int(3*np.log(self.ndim_problem))`),
                * 'n_parents'     - number of parents, aka parental population size (`int`, default:
                  `int(self.n_individuals/2)`).

    Examples
    --------
    Use the `ES` optimizer `MAES` to minimize the well-known test function
    `Rosenbrock <http://en.wikipedia.org/wiki/Rosenbrock_function>`_:

    .. code-block:: python
       :linenos:

       >>> import numpy
       >>> from pypoplib.base_functions import rosenbrock  # function to be minimized
       >>> from pypoplib.maes import MAES
       >>> problem = {'fitness_function': rosenbrock,  # define problem arguments
       ...            'ndim_problem': 2,
       ...            'lower_boundary': -5*numpy.ones((2,)),
       ...            'upper_boundary': 5*numpy.ones((2,))}
       >>> options = {'max_function_evaluations': 5000,  # set optimizer options
       ...            'seed_rng': 2022,
       ...            'mean': 3*numpy.ones((2,)),
       ...            'sigma': 0.1}  # the global step-size may need to be tuned for better performance
       >>> maes = MAES(problem, options)  # initialize the optimizer class
       >>> results = maes.optimize()  # run the optimization process
       >>> # return the number of function evaluations and best-so-far fitness
       >>> print(f"MAES: {results['n_function_evaluations']}, {results['best_so_far_y']}")
       MAES: 5000, 4.840520170399301e-17

    For its correctness checking of coding, refer to `this code-based repeatability report
    <https://tinyurl.com/3zvve79b>`_ for more details.

    Attributes
    ----------
    mean          : `array_like`
                    initial mean of Gaussian search distribution.
    n_individuals : `int`
                    number of offspring, aka offspring population size.
    n_parents     : `int`
                    number of parents, aka parental population size.
    sigma         : `float`
                    final mutation strength.

    References
    ----------
    Beyer, H.G., 2020, July.
    Design principles for matrix adaptation evolution strategies.
    In Proceedings of Annual Conference on Genetic and Evolutionary Computation Companion (pp. 682-700).
    https://dl.acm.org/doi/abs/10.1145/3377929.3389870

    Loshchilov, I., Glasmachers, T. and Beyer, H.G., 2019.
    Large scale black-box optimization by limited-memory matrix adaptation.
    IEEE Transactions on Evolutionary Computation, 23(2), pp.353-358.
    https://ieeexplore.ieee.org/abstract/document/8410043

    Beyer, H.G. and Sendhoff, B., 2017.
    Simplify your covariance matrix adaptation evolution strategy.
    IEEE Transactions on Evolutionary Computation, 21(5), pp.746-759.
    https://ieeexplore.ieee.org/document/7875115

    See the official Matlab version from Beyer:
    https://homepages.fhv.at/hgb/downloads/ForDistributionFastMAES.tar
    """
    def __init__(self, problem, options):
        ES.__init__(self, problem, options)
        self.options = options
        self.c_s = None  # for M10 in Fig. 3
        self.alpha_cov = 2.0  # for M11 in Fig. 3 (α_cov)
        self.c_1 = None  # for M11 in Fig. 3
        self.c_w = None  # for M11 in Fig. 3 (c_μ)
        self.d_sigma = None  # for M12 in Fig. 3 (d_σ)
        self._s_1 = None  # for M10 in Fig. 3
        self._s_2 = None  # for M10 in Fig. 3
        self._fast_version = options.get('_fast_version', False)
        if not self._fast_version:
            self._diag_one = np.diag(np.ones((self.ndim_problem,)))  # for M11 in Fig. 3

    def _set_c_w(self):
        return np.minimum(1.0 - self.c_1, self.alpha_cov*(self._mu_eff + 1.0/self._mu_eff - 2.0) /
                          (np.power(self.ndim_problem + 2.0, 2) + self.alpha_cov*self._mu_eff/2.0))

    def _set_d_sigma(self):
        return 1.0 + self.c_s + 2.0*np.maximum(0.0, np.sqrt((self._mu_eff - 1.0)/(self.ndim_problem + 1.0)) - 1.0)

    def initialize(self, is_restart=False):  # for M1 in Fig. 3
        self.c_s = self.options.get('c_s', (self._mu_eff + 2.0)/(self._mu_eff + self.ndim_problem + 5.0))
        self.c_1 = self.options.get('c_1', self.alpha_cov/(np.power(self.ndim_problem + 1.3, 2) + self._mu_eff))
        self.c_w = self.options.get('c_w', self._set_c_w())
        self.d_sigma = self.options.get('d_sigma', self._set_d_sigma())
        self._s_1 = 1.0 - self.c_s
        self._s_2 = np.sqrt(self._mu_eff*self.c_s*(2.0 - self.c_s))
        z = np.empty((self.n_individuals, self.ndim_problem))  # Gaussian noise for mutation
        d = np.empty((self.n_individuals, self.ndim_problem))  # search directions
        mean = self._initialize_mean(is_restart)  # mean of Gaussian search distribution
        s = np.zeros((self.ndim_problem,))  # evolution path
        tm = np.diag(np.ones((self.ndim_problem,)))  # transformation matrix M
        y = np.empty((self.n_individuals,))  # fitness (no evaluation)
        return z, d, mean, s, tm, y

    def iterate(self, z=None, d=None, mean=None, tm=None, y=None, args=None):
        for k in range(self.n_individuals):  # for M3 in Fig. 3 (sample offspring population)
            if self._check_terminations():
                return z, d, y
            z[k] = self.rng_optimization.standard_normal((self.ndim_problem,))  # for M4 in Fig. 3
            d[k] = np.squeeze(np.dot(tm, z[k][:, np.newaxis]))  # for M5 in Fig. 3
            y[k] = self._evaluate_fitness(mean + self.sigma*d[k], args)  # for M6 in Fig. 3
        return z, d, y

    def _update_distribution(self, z=None, d=None, mean=None, s=None, tm=None, y=None):
        order = np.argsort(y)  # for M8 in Fig. 3
        # set for M9, M10, M11 in Fig. 3
        d_w, z_w, zz_w = np.zeros((self.ndim_problem,)), np.zeros((self.ndim_problem,)), None
        if not self._fast_version:
            zz_w = np.zeros((self.ndim_problem, self.ndim_problem))  # for M11 in Fig. 3
        for k in range(self.n_parents):
            d_w += self._w[k]*d[order[k]]
            z_w += self._w[k]*z[order[k]]
            if not self._fast_version:
                zz_w += self._w[k]*np.dot(z[order[k]][:, np.newaxis], z[order[k]][np.newaxis, :])
        # update distribution mean (for M9 in Fig. 3)
        mean += self.sigma*d_w
        # update evolution path (s) and transformation matrix (M)
        s = self._s_1*s + self._s_2*z_w  # for M10 in Fig. 3
        if not self._fast_version:
            tm_1 = self.c_1*(np.dot(s[:, np.newaxis], s[np.newaxis, :]) - self._diag_one)
            tm_2 = self.c_w*(zz_w - self._diag_one)
            tm += 0.5*np.dot(tm, tm_1 + tm_2)  # for M11 in Fig. 3
        else:
            tm = (1.0 - 0.5*(self.c_1 + self.c_w))*tm + (0.5*self.c_1)*np.dot(
                np.dot(tm, s[:, np.newaxis]), s[np.newaxis, :])
            for k in range(self.n_parents):
                tm += (0.5*self.c_w)*self._w[k]*np.dot(d[order[k]][:, np.newaxis], z[order[k]][np.newaxis, :])
        # update global step-size (for M12 in Fig. 3)
        self.sigma *= np.exp(self.c_s/self.d_sigma*(np.linalg.norm(s)/self._e_chi - 1.0))
        return mean, s, tm

    def restart_reinitialize(self, z=None, d=None, mean=None, s=None, tm=None, y=None):
        if ES.restart_reinitialize(self):
            z, d, mean, s, tm, y = self.initialize(True)
        return z, d, mean, s, tm, y

    def optimize(self, fitness_function=None, args=None):  # for all generations (iterations)
        fitness = ES.optimize(self, fitness_function)
        z, d, mean, s, tm, y = self.initialize()
        while True:
            # sample and evaluate offspring population
            z, d, y = self.iterate(z, d, mean, tm, y, args)
            if self.saving_fitness:
                fitness.extend(y)
            if self._check_terminations():
                break
            mean, s, tm = self._update_distribution(z, d, mean, s, tm, y)
            self._print_verbose_info(y)
            self._n_generations += 1
            if self.is_restart:
                z, d, mean, s, tm, y = self.restart_reinitialize(z, d, mean, s, tm, y)
        results = self._collect_results(fitness, mean)
        results['s'] = s
        return results