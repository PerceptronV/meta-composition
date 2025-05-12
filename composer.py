import random
from utils import get_funcs_dict, get_type_dict
from utils import type_generator


class RandomComposer:
    def __init__(self, module):
        self.module = module
        self.funcs = get_funcs_dict(module)
    
    def compose(self, input_type, output_type, depth=3, seed=None):
        # randomly compose functions from primitives according to type signatures
        ...
    
    def chain(self, input_type, output_type):
        # randomly chain functions according to type signatures
        ...
