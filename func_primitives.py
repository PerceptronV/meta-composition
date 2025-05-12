from typing import Any, Dict, List


# Integer operations
def int_add(x: int, y: int) -> int:
    return x + y

def int_sub(x: int, y: int) -> int:
    return x - y

def int_mul(x: int, y: int) -> int:
    return x * y

def int_div(x: int, y: int) -> int:
    return x // y if y != 0 else 0

# Float operations
def float_add(x: float, y: float) -> float:
    return x + y

def float_mul(x: float, y: float) -> float:
    return x * y

def float_div(x: float, y: float) -> float:
    return x / y if y != 0.0 else 0.0

# String operations
def str_concat(a: str, b: str) -> str:
    return a + b

def str_upper(s: str) -> str:
    return s.upper()

def str_repeat(s: str, n: int) -> str:
    return s * n

def str_length(s: str) -> int:
    return len(s)

# List operations
def list_append(lst: List[Any], item: Any) -> List[Any]:
    return lst + [item]

def list_length(lst: List[Any]) -> int:
    return len(lst)

def list_get(lst: List[Any], index: int) -> Any:
    if 0 <= index < len(lst):
        return lst[index]
    return None

def list_concat(a: List[Any], b: List[Any]) -> List[Any]:
    return a + b

# Dictionary operations
def dict_get(d: Dict[Any, Any], key: Any) -> Any:
    return d.get(key, None)

def dict_set(d: Dict[Any, Any], key: Any, value: Any) -> Dict[Any, Any]:
    d_copy = d.copy()
    d_copy[key] = value
    return d_copy

def dict_keys(d: Dict[Any, Any]) -> List[Any]:
    return list(d.keys())
