import random

def random_string() -> str:
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz')
                   for _ in range(random.randint(1, 5)))

def random_int() -> int:
    return random.randint(0, 5)

def random_float() -> float:
    return random.uniform(-2.0, 2.0)


DTYPE_GENERATORS = {
    str: random_string,
    int: random_int,
    float: random_float
}
