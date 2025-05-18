# Meta Composition

Teaching meta-generalisation through randomly-sampled DSL functions.

File structure:
- [`utils.py`](./utils.py) defines helpful methods for accessing function names and type annotations
- [`primitives.py`](./primitives.py) defines primitives for composing together a DSL (with type annotations)
- [`generators.py`](./generators.py) defines random generator functions for various types
- [`composer.py`](./composer.py) randomly samples from the primitives to create functions
