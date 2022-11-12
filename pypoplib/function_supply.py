"""
This file contains function that can help deal with functions
"""
from pypoplib.base_functions import *


def get_function(function_name):
    """
    Get the function accordding to function_name
    :param function_name: Name of function
    """
    if function_name == "sphere":
        return sphere
    elif function_name == "cigar":
        return cigar
    elif function_name == "discus":
        return discus
    elif function_name == "cigar_discus":
        return cigar_discus
    elif function_name == "ellipsoid":
        return ellipsoid
    elif function_name == "different_powers":
        return different_powers
    elif function_name == "schwefel221":
        return schwefel221
    elif function_name == "schwefel222":
        return schwefel222
    elif function_name == "schwefel12":
        return schwefel12
    elif function_name == "step":
        return step
    elif function_name == "exponential":
        return exponential
    elif function_name == "rosenbrock":
        return rosenbrock
    elif function_name == "griewank":
        return griewank
    elif function_name == "bohachevsky":
        return bohachevsky
    elif function_name == "ackley":
        return ackley
    elif function_name == "rastrigin":
        return rastrigin
    elif function_name == "scaled_rastrigin":
        return scaled_rastrigin
    elif function_name == "skew_rastrigin":
        return skew_rastrigin
    elif function_name == "levy_montalvo":
        return levy_montalvo
    elif function_name == "michalewicz":
        return michalewicz
    elif function_name == "salomon":
        return salomon
    elif function_name == "shubert":
        return shubert
    elif function_name == "schaffer":
        return schaffer

