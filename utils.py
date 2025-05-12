import os
import types
import typing
from typing import get_origin, get_args


def get_funcs_dict(module):
    func_dict = {}
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, types.FunctionType):
            func_dict[name] = obj
    return func_dict

def get_type_dict(func):
    return typing.get_type_hints(func)

def same_origin(dtype1, dtype2):
    return get_origin(dtype1) == get_origin(dtype2)

def type_origin(dtype):
    return get_origin(dtype)

def type_args(dtype):
    return get_args(dtype)

def type_generator(dtype):
    ...
    # generate random test values for given datatypes used by func_primitives
