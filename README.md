# Meta Composition

Teaching meta-generalisation through randomly-sampled DSL functions.

File structure:
- [`utils.py`](./utils.py) defines helpful methods for accessing function names and type annotations
- [`func_primitives.py`](./func_primitives.py) defines primitives for composing together a DSL
- [`composer.py`](./composer.py) randomly samples from the primitives to create functions
