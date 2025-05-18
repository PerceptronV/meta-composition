# Meta Composition

Teaching meta-generalisation through randomly-sampled DSL functions.

File structure:
- [`utils.py`](./utils.py) defines helpful methods for accessing function names and type annotations
- [`primitives.py`](./primitives.py) defines primitives for composing together a DSL (with type annotations)
- [`generators.py`](./generators.py) defines random generator functions for various types
- [`composer.py`](./composer.py) randomly samples from the primitives to create functions

Conventions:
- Input types are always defined as dictionaries {keyword: type}
- Output types are always defined as tuples (ret1_type, ret2_type, ...)
    - Single-valued functions from `primitives.py` will be converted to return a length-1 tuple
