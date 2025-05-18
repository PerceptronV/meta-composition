from utils import get_funcs, get_types, returns_many
from generators import DTYPE_GENERATORS


class Vertex:
    name: str
    inp_type: dict
    out_type: type | tuple[type]

class FuncVertex(Vertex):
    def __init__(self, name, func):
        self.name = name
        self.func = func
        ( self.inp_type,
          self.out_type,
          self.single    ) = get_types(func)
        if self.single:
            self.out_type = (self.out_type,)    # comma important: converts to tuple
    
    def __len__(self):
        return len(self.out_type)

    def __str__(self):
        return f'{self.name}({", ".join(k for k in self.inp_type)})'
    
    def __repr__(self):
        _i = ", ".join(f"{k}: {t}" for k, t in self.inp_type.items())
        return f'{self.name}({_i}) -> {self.out_type}'
    
    def __call__(self, *args, **kwargs):
        result = self.func(*args, **kwargs)
        if self.single:
            return (result, )                   # comma important: converts to tuple
        return result


class ConstVertex(Vertex):
    def __init__(self, value):
        self.name = str(value)
        self.value = value
        self.inp_type = {}
        self.out_type = type(value)
    
    def __len__(self):
        return 1
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    
    def __call__(self):
        return (self.value, )                   # comma important: converts to tuple


class SinkVertex(Vertex):
    def __init__(self, dtype):
        self.name = '__SINK__'
        self.inp_type = {'burn': dtype}
        self.out_type = type(None)
    
    def __len__(self):
        return 0
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name
    
    def __call__(self, *args, **kwargs):
        return


class FuncGraph:
    def __init__(self, name='compositeFn'):
        self.name = name
        self.vertices = set()
        self.adjacency = {}     # adjacency dict, with list elements; vertex: [out_idx: [(vertex, kwd)]]
        self.argdeps = {}       # reverse adjacency, but with dictionary elements; vertex: {kwd: (vertex, out_idx)}
    
    def add(self, new: Vertex):
        self.vertices.add(new)
        self.adjacency[new] = [None] * len(new)
        self.argdeps[new] = {k: None for k in new.inp_type}
        return new
    
    def feed(self, src, idx, dst, kwd):
        if self.adjacency[src][idx] is not None:
            self.adjacency[src][idx].append((dst, kwd))
        else:
            self.adjacency[src][idx] = [(dst, kwd)]
        self.argdeps[dst][kwd] = (src, idx)
    
    def _get_topo_order(self):
        '''
        Topologically sort everthing except for sink vertices.
        '''
        def dfs(vertex, visited, topo_order):
            visited.add(vertex)
            recursing.add(vertex)
            for _, into in self.argdeps[vertex].items():   # run on reverse graph
                if not into:
                    continue
                dst, _ = into
                if dst in recursing:                       # back edge
                    raise ValueError("Cyclic graph")
                if dst not in visited:
                    dfs(dst, visited, topo_order)
            topo_order.append(vertex)
            recursing.remove(vertex)

        visited = set()
        recursing = set()
        topo_order = []
        for vertex in self.vertices:
            if vertex not in visited:
                dfs(vertex, visited, topo_order)

        sink = None
        for vertex in self.vertices:
            if None in self.adjacency[vertex]:  # has an uncaught output
                if not sink:
                    sink = vertex
                else:
                    raise ValueError(f"Incomplete graph: non-sink vertex {vertex} has uncaught"
                                      "outputs. Use a sink vertex to block unused outputs.")
        if sink is None:
            raise ValueError("Graph does not have an output vertex.")
        
        return topo_order, sink
    
    def _get_out_indices(self, sink):
        out_idx = []
        for e, into in enumerate(self.adjacency[sink]):
            if into is None:
                out_idx.append(e)
        return out_idx
    
    def get_out_type(self):
        _, sink = self._get_topo_order()
        out_idx = self._get_out_indices(sink)
        return tuple(sink.out_type[i] for i in out_idx)
    
    def _get_arguments(self):
        counters = {}
        inp_type = {}
        arg_map = {}
        for vertex in self.vertices:
            for kwd in vertex.inp_type:
                if not self.argdeps[vertex][kwd]:
                    if kwd in counters:
                        counters[kwd] += 1
                    else:
                        counters[kwd] = 0
                    arg_name = f'{kwd}{counters[kwd]}'
                    inp_type[arg_name] = vertex.inp_type[kwd]
                    arg_map[(vertex, kwd)] = arg_name
        return inp_type, arg_map
    
    def get_inp_type(self):
        inp_type, _ = self._get_arguments()
        return inp_type
        
    def __len__(self):
        return len(self.vertices)
    
    def __str__(self):
        inp_type = self.get_inp_type()
        return f'{self.name}({", ".join(k for k in inp_type)})'
    
    def __repr__(self):
        inp_type = self.get_inp_type()
        out_type = self.get_out_type()
        _i = ", ".join(f"{k}: {t}" for k, t in inp_type.items())
        return f'{self.name}({_i}) -> {out_type}'
    
    def straight_line(self):
        prog = ''
        intermediates = {}      # (vertex, kwd): str
        counter = 0

        inp_type, arg_map = self._get_arguments()
        order, sink = self._get_topo_order()
        out_idx = self._get_out_indices(sink)

        prog += f'>INPUT ({", ".join(f"${k}: {t}" for k, t in inp_type.items())})\n'

        for vertex in order:
            current_kwargs = {}
            for kwd in vertex.inp_type:
                if (vertex, kwd) in intermediates:
                    current_kwargs[kwd] = intermediates[(vertex, kwd)]
                elif (vertex, kwd) in arg_map:
                    current_kwargs[kwd] = '$'+arg_map[(vertex, kwd)]
            computation = ", ".join(f"{k}: {vertex.inp_type[k]} = {v}" for k, v in current_kwargs.items())
            
            if vertex == sink:
                prog += f'>RETURN {vertex.name}({computation}){repr(out_idx)}'
                return prog
            
            names = []
            for idx in range(len(vertex)):
                var = f'!v{counter}'
                counter += 1
                for (trg, kwd) in self.adjacency[vertex][idx]:
                    intermediates[(trg, kwd)] = var
                names.append(var)
            prog += ', '.join(names) + f' = {vertex.name}({computation})\n'
        
        return prog
            

    def __call__(self, *args, **kwargs):
        intermediates = {}      # (vertex, kwd): value

        inp_type, arg_map = self._get_arguments()
        order, sink = self._get_topo_order()
        out_idx = self._get_out_indices(sink)

        for name, value in zip(inp_type, args):
            kwargs[name] = value

        for vertex in order:
            current_kwargs = {}
            for kwd in vertex.inp_type:
                if (vertex, kwd) in intermediates:
                    current_kwargs[kwd] = intermediates[(vertex, kwd)]
                elif (vertex, kwd) in arg_map:
                    current_kwargs[kwd] = kwargs[arg_map[(vertex, kwd)]]
            result = vertex(**current_kwargs)
            
            if vertex == sink:
                return tuple(result[i] for i in out_idx)
            
            for idx in range(len(vertex)):
                for (trg, kwd) in self.adjacency[vertex][idx]:
                    intermediates[(trg, kwd)] = result[idx]
        
        return None


class RandomComposer:
    def __init__(self, module):
        self.module = module
        self.funcs = get_funcs(module)
    
    def compose(self, input_types, output_type, depth=3, seed=None):
        # randomly compose functions from primitives according to type signatures
        ...
    
    def chain(self, input_type, output_type):
        # randomly chain functions according to type signatures
        ...
