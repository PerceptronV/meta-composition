import types
from typing import Dict
from typing import (
    get_origin,
    get_args,
    get_type_hints
)


def same_origin(dtype1, dtype2):
    return get_origin(dtype1) == get_origin(dtype2)

def type_origin(dtype):
    return get_origin(dtype)

def type_args(dtype):
    return get_args(dtype)


def get_funcs(module):
    func_dict = {}
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, types.FunctionType):
            func_dict[name] = obj
    return func_dict


def returns_many(dtype):
    many = False
    out_args = get_args(dtype)
    if out_args and not (dtype == dict or same_origin(dtype, Dict)):
        many = True
    return many


def get_types(func):
    inp_type_dict = get_type_hints(func)
    del inp_type_dict['return']
    out_type = get_type_hints(func, include_extras=True).get('return')

    single = True
    if returns_many(out_type):
        out_type = get_args(out_type)
        single = False
    return inp_type_dict, out_type, single
