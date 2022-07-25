import numpy as np

from .function import OptFunction


class OptFunctionList(OptFunction):
    """
    A list of functions.

    The main point of this class is to manage the
    variables and components of the added functions.

    Add functions to the list via the `append` function,
    and don't forget to initialize.

    Parameters
    ----------
    problem: iwopy.Problem
        The underlying optimization problem
    name: str
        The function name

    Attributes
    ----------
    func_vars_int : list of lists of int
        For each added function, the subset of
        integer variables
    func_vars_float : list of lists of int
        For each added function, the subset of
        float variables
    sizes : list of int
        The components of each added function

    """

    def __init__(self, problem, name):
        super().__init__(problem, name)

        self._functions = []
        self._cnames = []
        self.func_vars_int = []
        self.func_vars_float = []
        self.sizes = []

    def append(self, function):
        """
        Adds a function to the list.

        Parameters
        ----------
        function : iwopy.core.OptFunction
            The function

        """
        if self.initialized:
            raise ValueError(
                f"FunctionList '{self.name}': Attempt to add function '{function.name}' after initialization"
            )

        if function.problem is not self.problem:
            raise ValueError(
                f"FunctionList '{self.name}': Cannot add function '{function.name}' since problems don't match. Expected '{self.problem.name}', found '{function.problem.name}'"
            )
        self._functions.append(function)
        self._cnames += list(function.component_names)

    @property
    def functions(self):
        """
        The list of added funtions

        Returns
        -------
        funcs : list of iwopy.core.OptFunction
            The list of added functions

        """
        return self._functions

    @property
    def n_functions(self):
        """
        The number of added functions

        Returns
        -------
        n : int
            The total number of added functions

        """
        return len(self.functions)

    def initialize(self, verbosity=0):
        """
        Initialize the object.

        Parameters
        ----------
        verbosity : int
            The verbosity level, 0 = silent

        """
        self._vnamesi = []
        self._vnamesf = []
        self.sizes = []
        for f in self.functions:
            if not f.initialized:
                f.initialize(verbosity)
            self._vnamesi += f.var_names_int
            self._vnamesf += f.var_names_float
            self.sizes.append(f.n_components())
        self._vnamesi = list(dict.fromkeys(self._vnamesi))
        self._vnamesf = list(dict.fromkeys(self._vnamesf))

        def getv(vnames, fvnames):
            if not len(fvnames):
                return []
            l = [vnames.index(v) for v in fvnames]
            return np.s_[l[0] : l[-1]] if list(range(l[0], l[-1])) == l else l

        self.func_vars_int = [
            getv(self._vnamesi, f.var_names_int) for f in self.functions
        ]
        self.func_vars_float = [
            getv(self._vnamesf, f.var_names_float) for f in self.functions
        ]

        super().initialize(verbosity)

    def n_components(self):
        """
        Returns the number of components of the
        function.

        Returns
        -------
        int:
            The number of components.

        """
        return sum(self.sizes)

    def split_individual(self, data):
        """
        Splits result values or other data into
        individual function data.

        Parameters
        ----------
        data : numpy.ndarray
            The data, shape: (n_components,)

        Returns
        -------
        fdata : list of numpy.ndarray
            The data for each function, list entry
            shapes: (n_func_components,)

        """
        out = []
        i0 = 0
        for fi in range(self.n_functions):
            i1 = i0 + self.sizes[fi]
            out.append(data[i0:i1])
            i0 = i1
        return out

    def split_population(self, data):
        """
        Splits result values or other data into
        individual function data.

        Parameters
        ----------
        data : numpy.ndarray
            The data, shape: (n_pop, n_components)

        Returns
        -------
        fdata : list of numpy.ndarray
            The data for each function, list entry
            shapes: (n_pop, n_func_components)

        """
        out = []
        i0 = 0
        for fi in range(self.n_functions):
            i1 = i0 + self.sizes[fi]
            out.append(data[:, i0:i1])
            i0 = i1
        return out

    def calc_individual(self, vars_int, vars_float, problem_results):
        """
        Calculate values for a single individual of the
        underlying problem.

        Parameters
        ----------
        vars_int : np.array
            The integer variable values, shape: (n_vars_int,)
        vars_float : np.array
            The float variable values, shape: (n_vars_float,)
        problem_results : Any
            The results of the variable application
            to the problem

        Returns
        -------
        values : np.array
            The component values, shape: (n_components,)

        """
        values = np.full(self.n_components(), np.nan, dtype=np.float64)

        i0 = 0
        for fi, f in enumerate(self.functions):
            i1 = i0 + self.sizes[fi]
            varsi = vars_int[self.func_vars_int[fi]]
            varsf = vars_float[self.func_vars_float[fi]]
            values[i0:i1] = f.calc_individual(varsi, varsf, problem_results)
            i0 = i1

        return values

    def calc_population(self, vars_int, vars_float, problem_results):
        """
        Calculate values for all individuals of a population.

        Parameters
        ----------
        vars_int : np.array
            The integer variable values, shape: (n_pop, n_vars_int)
        vars_float : np.array
            The float variable values, shape: (n_pop, n_vars_float)
        problem_results : Any
            The results of the variable application
            to the problem

        Returns
        -------
        values : np.array
            The component values, shape: (n_pop, n_components,)

        """
        n_pop = vars_float.shape[0]
        values = np.full((n_pop, self.n_components()), np.nan, dtype=np.float64)

        i0 = 0
        for fi, f in enumerate(self.functions):
            i1 = i0 + self.sizes[fi]
            varsi = vars_int[:, self.func_vars_int[fi]]
            varsf = vars_float[:, self.func_vars_float[fi]]
            values[:, i0:i1] = f.calc_population(varsi, varsf, problem_results)
            i0 = i1

        return values

    def finalize_individual(self, vars_int, vars_float, problem_results, verbosity=1):
        """
        Finalization, given the champion data.

        Parameters
        ----------
        vars_int : np.array
            The optimal integer variable values, shape: (n_vars_int,)
        vars_float : np.array
            The optimal float variable values, shape: (n_vars_float,)
        problem_results : Any
            The results of the variable application
            to the problem
        verbosity : int
            The verbosity level, 0 = silent

        Returns
        -------
        values : np.array
            The component values, shape: (n_components,)

        """
        values = np.full(self.n_components(), np.nan, dtype=np.float64)

        i0 = 0
        for fi, f in enumerate(self.functions):
            i1 = i0 + self.sizes[fi]
            varsi = vars_int[self.func_vars_int[fi]]
            varsf = vars_float[self.func_vars_float[fi]]
            values[i0:i1] = f.finalize_individual(
                varsi, varsf, problem_results, verbosity
            )
            i0 = i1

        return values

    def finalize_population(self, vars_int, vars_float, problem_results, verbosity=1):
        """
        Finalization, given the final population data.

        Parameters
        ----------
        vars_int : np.array
            The integer variable values of the final
            generation, shape: (n_pop, n_vars_int)
        vars_float : np.array
            The float variable values of the final
            generation, shape: (n_pop, n_vars_float)
        problem_results : Any
            The results of the variable application
            to the problem
        verbosity : int
            The verbosity level, 0 = silent

        Returns
        -------
        values : np.array
            The component values, shape: (n_pop, n_components)

        """
        n_pop = vars_float.shape[0]
        values = np.full((n_pop, self.n_components()), np.nan, dtype=np.float64)

        i0 = 0
        for fi, f in enumerate(self.functions):
            i1 = i0 + self.sizes[fi]
            varsi = vars_int[:, self.func_vars_int[fi]]
            varsf = vars_float[:, self.func_vars_float[fi]]
            values[:, i0:i1] = f.finalize_population(
                varsi, varsf, problem_results, verbosity
            )
            i0 = i1

        return values

    def ana_deriv(self, vars_int, vars_float, var, components=None):
        """
        Calculates the analytic derivative, if possible.

        Use `numpy.nan` if analytic derivatives cannot be calculated.

        Parameters
        ----------
        vars_int : np.array
            The integer variable values, shape: (n_vars_int,)
        vars_float : np.array
            The float variable values, shape: (n_vars_float,)
        var : int
            The index of the differentiation float variable
        components : list of int
            The selected components, or None for all

        Returns
        -------
        deriv : numpy.ndarray
            The derivative values, shape: (n_sel_components,)

        """
        cmpnts = []
        i0 = 0
        for fi, s in enumerate(self.sizes):
            i1 = i0 + s
            if components is None:
                cmpnts.append(list(range(i0, i1)))
            else:
                cmpnts.append([c for c in components if c >= i0 and c < i1])
            i0 = i1

        n_cmpnts = len(components) if components is not None else self.n_components()
        deriv = np.full(n_cmpnts, np.nan, dtype=np.float64)

        i0 = 0
        c0 = 0
        for fi, f in enumerate(self.functions):
            i1 = i0 + self.sizes[fi]
            c1 = c0 + len(cmpnts[fi])
            if c1 > c0 and var in list(self.func_vars_float[fi]):
                varsi = vars_int[self.func_vars_int[fi]]
                varsf = vars_float[self.func_vars_float[fi]]
                vi = list(self.func_vars_float[fi]).index(var)
                deriv[c0:c1] = f.ana_deriv(varsi, varsf, vi, components=cmpnts[fi])
            i0 = i1
            c0 = c1

        return deriv
