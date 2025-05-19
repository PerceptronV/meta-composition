import math
import types
from typing import (
    get_origin,
    get_args,
    get_type_hints
)


SINK_KWD = '_'      # the only keyword argument of sink vertices in function graphs
OUT_KWD = 'out'  # the only keyword argument of output vertices


def softmax(
    arr: list[float],
    temp: float = 0.7
) -> list[float]:
    """
    Compute the softmax of a list of numbers.

    Parameters
    ----------
    arr
        The list of numbers to compute the softmax of.

    Returns
    -------
    softmax
        The softmax of the list of numbers.
    """
    exp_arr = [math.exp(x / temp) for x in arr]
    s = sum(exp_arr)
    return [x / s for x in exp_arr]


def argmax(arr: list[float]) -> int:
    """
    Get the index of the maximum element in a list of 
    NON-NEGATIVE floats.

    Parameters
    ----------
    arr
        The list of floats to find the maximum index of.

    Returns
    -------
    max_idx
        The index of the maximum element in the list.

    """
    max_itm = -1
    max_idx = None
    for e, v in enumerate(arr):
        if v > max_itm:
            max_itm = v
            max_idx = e
    return max_idx


def get_funcs(
    module: types.ModuleType
) -> dict[str, types.FunctionType]:
    """
    Get all functions from a module.

    Parameters
    ----------
    module
        Module object to inspect.

    Returns
    -------
    func_dict
        A dictionary of {name: function object} where the name is the name of
        the function and the value is the function object itself.
    """
    func_dict = {}
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, types.FunctionType):
            func_dict[name] = obj
    return func_dict


def returns_single(
    dtype: type
) -> bool:
    """
    Check if a type hint returns a single value.
    True if dtype is not: (a tuple and has args).


    Parameters
    ----------
    dtype
        The type hint to check.

    Returns
    -------
    single
        True if the type hint returns a single value, False otherwise.
    """
    return not  (   len(get_args(dtype)) > 0
                    and 
                    tuple in (dtype, get_origin(dtype))   )


def get_types(
    func: types.FunctionType
) -> tuple[dict[str, type], type | tuple[type], bool]:
    """
    Get type hints from a function.

    Parameters
    ----------
    func
        Function object to inspect.

    Returns
    -------
    inp_type_dict
        A dictionary of {name: type hint} for each argument of the function.
    out_type
        The type hint for the return value of the function. If the function
        returns a single value, this will be converted into a one-element tuple.
    single
        A boolean for whether the original function returns a single value or a tuple.
    """
    inp_type_dict = get_type_hints(func)
    out_type = inp_type_dict.pop('return')

    if (single := returns_single(out_type)):
        out_type = (out_type,)               # comma important: converts to tuple
    else:
        out_type = get_args(out_type)

    return inp_type_dict, out_type, single
