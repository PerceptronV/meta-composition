import types
import heapq
import random
from collections import Counter

from utils import get_funcs, get_types
from utils import softmax, argmax
from utils import SINK_KWD, OUT_KWD
from generators import DTYPE_GENERATORS


class Vertex:
    name: str
    inp_type: dict[str, type]
    out_type: tuple[type]

    def __lt__(self, other):
        return len(self) < len(other)


class FuncVertex(Vertex):
    def __init__(self, name: str, func: types.FunctionType):
        """
        Create a new function vertex.

        Parameters
        ----------
        name
            The name of this vertex.
        func
            The underlying function to be called by this vertex.
        """
        self.name = name
        self.func = func
        ( self.inp_type,
          self.out_type,
          self.single    ) = get_types(func)
    
    def __len__(self) -> int:
        return len(self.out_type)

    def __str__(self) -> str:
        return f'{self.name}({", ".join(k for k in self.inp_type)})'
    
    def __repr__(self) -> str:
        _i = ", ".join(f"{k}: {t}" for k, t in self.inp_type.items())
        return f'{self.name}({_i}) -> {self.out_type}'
    
    def __call__(self, *args, **kwargs) -> tuple:
        result = self.func(*args, **kwargs)
        if self.single:
            return (result,)                    # comma important: converts to tuple
        return result


class ConstVertex(Vertex):
    def __init__(self, value):
        """
        Initialize a constant vertex with a given value.

        Parameters
        ----------
        value
            The constant value for this vertex. The name of the vertex will
            be the string representation of this value, and the output type
            will be the type of the value.
        """
        self.name = str(value)
        self.value = value
        self.inp_type = {}
        self.out_type = type(value)
    
    def __len__(self) -> int:
        return 1
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.name
    
    def __call__(self) -> tuple:
        return (self.value,)                    # comma important: converts to tuple


class SinkVertex(Vertex):
    def __init__(self, dtype: type):
        """
        Initialize a sink vertex with a given type to discard useless outputs.

        Parameters
        ----------
        dtype
            The type of the output to be discarded.
        """
        self.name = SINK_KWD
        self.inp_type = {SINK_KWD: dtype}
        self.out_type = type(None)
    
    def __len__(self) -> int:
        return 0
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.name
    
    def __call__(self, *args, **kwargs):
        return


class OutVertex(Vertex):
    def __init__(self, dtype: type):
        self.name = "~ret"
        self.inp_type = {OUT_KWD: dtype}
        self.out_type = (dtype,)                    # comma important: converts to tuple
    
    def __len__(self) -> int:
        return 1
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.name
    
    def __call__(self, *args, **kwargs):
        if len(args) >= 1:
            return (args[0],)                       # comma important: converts to tuple
        return (kwargs[OUT_KWD],)                   # comma important: converts to tuple


class FuncGraph:
    """
    An object to compose functions as a graph and execute it.

    Attributes
    ----------
    name
        The name of this function graph.
    vertices
        A set of `Vertex` objects.
    adjacency
        A dictionary mapping from `Vertex` to a list of lists, where
            the outer list is indxed by output index, and each inner list contains 
            `(target_vertex, keyword)` pairs.
    argdeps
        A dictionary mapping from `Vertex` to an inner dictionary, mapping
            from keyword to `(source_vertex, output_idx)`.
    input_order
        A tuple of types to order the arguments by.
    output_order
        A tuple of types to order the outputs by.
    """

    name: str
    vertices: set[Vertex]
    adjacency: dict[Vertex, list[type[None] | list[tuple[Vertex, str]]]]
    argdeps: dict[Vertex, dict[str, tuple[Vertex, int]]]
    input_order: tuple[type]
    output_order: tuple[type]

    def __init__(self, name: str = 'compositeFn'):
        """
        Initialize an empty function graph.

        Parameters
        ----------
        name
            The name of this function graph.

        Notes
        -----
        `vertices` is a set of `Vertex` objects.
        `adjacency` is a dictionary mapping from `Vertex` to a list of lists, where
            the outer list is indxed by output index, and each inner list contains 
            `(target_vertex, keyword)` pairs.
        `argdeps` is a dictionary mapping from `Vertex` to an inner dictionary, mapping
            from keyword to `(source_vertex, output_idx)`.
        `input_order` is a tuple of types to order the arguments by.
        `output_order` is a tuple of types to order the outputs by.
        """
        self.name = name
        self.vertices = set()
        self.adjacency = {}     # adjacency dict, with list elements; vertex: [out_idx: [(vertex, kwd)]]
        self.argdeps = {}       # reverse adjacency, but with dictionary elements; vertex: {kwd: (vertex, out_idx)}
        self.input_order = None
        self.output_order = None
    
    def add(self, new: Vertex) -> Vertex:
        """
        Add a new vertex to the function graph.

        Parameters
        ----------
        new : Vertex
            The vertex to be added to the graph.

        Returns
        -------
        Vertex
            The added vertex.
        """
        self.vertices.add(new)
        self.adjacency[new] = [None] * len(new)
        self.argdeps[new] = {k: None for k in new.inp_type}
        return new
    
    def feed(self, src: Vertex, idx: int, dst: Vertex, kwd: str):
        """
        Connect an output of a source vertex to an input of a destination vertex.

        Parameters
        ----------
        src : Vertex
            The source vertex.
        idx : int
            The output index of the source vertex.
        dst : Vertex
            The destination vertex.
        kwd : str
            The keyword of the input to the destination vertex.
        """
        if self.adjacency[src][idx] is not None:
            self.adjacency[src][idx].append((dst, kwd))
        else:
            self.adjacency[src][idx] = [(dst, kwd)]
        self.argdeps[dst][kwd] = (src, idx)
    
    def _get_topo_order(self) -> tuple[list[Vertex], Vertex]:
        """
        Compute a topological order of the function graph.

        Returns
        -------
        topo_order : list[Vertex]
            A list of vertices in topological order.
        out : Vertex
            The output vertex of the graph (highest topological
            order with output).
        """
       
        def dfs(vertex: Vertex, visited: set[Vertex], topo_order: list[Vertex]):
            """
            Perform a depth-first search on the reversed graph, to find the
            topological order of the graph through post-order. This does not
            take into account sink nodes, and checks for cycles in the graph.

            Parameters
            ----------
            vertex : Vertex
                The current vertex to search.
            visited : set[Vertex]
                Set of visited vertices.
            topo_order : list[Vertex]
                List of vertices in topological order.
            """
            visited.add(vertex)
            recursing.add(vertex)
            for _, into in self.argdeps[vertex].items():   # run on reverse graph
                if into is None:
                    continue
                dst, _ = into
                if dst in recursing:                       # back edge
                    raise ValueError("Cyclic graph")
                if dst not in visited:
                    dfs(dst, visited, topo_order)
            if len(self.adjacency[vertex]) > 0:            # non-sink vertex
                topo_order.append(vertex)
            recursing.remove(vertex)

        visited = set()
        recursing = set()
        topo_order = []
        for vertex in self.vertices:
            if vertex not in visited:
                dfs(vertex, visited, topo_order)

        return topo_order
    
    def _get_out_indices(self, out: Vertex) -> list[int]:
        """
        Get a list of output indices of the given vertex `out` that have no
        destination vertex (i.e., the output is not connected to any input of
        any other vertex).

        Parameters
        ----------
        out : Vertex
            The vertex to get the output indices for.

        Returns
        -------
        out_idx : list[int]
            A list of output indices of `out` that are not connected to any
            input of any other vertex.
        """
        out_idx = []
        for e, into in enumerate(self.adjacency[out]):
            if into is None:
                out_idx.append(e)
        return out_idx
    
    def _get_outputs(
        self,
        type_ordering: tuple[type] = None
    ) -> tuple[tuple[type], tuple[tuple[Vertex, int]]]:
        """
        Get the outputs of the graph, and where they are derived from.

        Parameters
        ----------
        type_ordering : tuple[type], optional
            A tuple of types to order the outputs by.

        Returns
        -------
        out_type : list[type]
            A list of output types of the graph.
        out_map : list[tuple[Vertex, int]]
            A list of tuples, where each tuple contains the output vertex and
            the index of the output type.
        """
        outs = []

        for vertex in self.vertices:
            if ( not isinstance(vertex, SinkVertex) and
                 None in self.adjacency[vertex] ):  # has an uncaught output
                outs.append(vertex)
        if len(outs) == 0:
            raise ValueError("Graph does not have an output vertex.")
        
        outs_idx = [self._get_out_indices(o) for o in outs]
        
        out_type = []
        out_map = []
        for o, o_i in zip(outs, outs_idx):
            out_type.extend([o.out_type[j] for j in o_i])
            out_map.extend([(o, j) for j in o_i])
        
        # if a preferred ordering is provided, reflect that in the output
        if type_ordering is None:
            type_ordering = self.output_order
        
        if ( type_ordering is not None and
             Counter(out_type) == Counter(type_ordering) ):
            used = set()
            new_out_type = []
            new_out_map = []
            for typ in type_ordering:
                for e, (o, o_i) in enumerate(zip(out_type, out_map)):
                    if o == typ and e not in used:
                        used.add(e)
                        new_out_type.append(o)
                        new_out_map.append(o_i)
                        break
            out_type, out_map = new_out_type, new_out_map

        return tuple(out_type), tuple(out_map)
    
    def get_out_type(self) -> tuple[type]:
        """
        Get the output type of this graph.

        The output type is determined by the output type of the last vertex in
        the topological order of the graph, after removing any output indices
        that are connected to any input of any vertex.

        Returns
        -------
        out_type : tuple[type]
            The output type of this graph.
        """
        out_type, _ = self._get_outputs()
        return tuple(out_type)
    
    def _get_arguments(
        self,
        type_ordering: tuple[type] = None
    ) -> tuple[dict[str, type], dict[tuple[Vertex, str], str]]:
        """
        Get a dictionary of input types and a dictionary mapping argument names to their corresponding
        keyword argument names in the input dictionary.

        The input dictionary is constructed by iterating through all vertices in the graph and
        accumulating their input types into a single dictionary. If an input type is encountered
        multiple times, a counter is used to disambiguate the names by appending a number to the
        argument name.

        Parameters
        ----------
        type_ordering : tuple[type], optional
            A tuple of types to order the arguments by.

        Returns
        -------
        inp_type : dict[str, type]
            A dictionary of argument names to their corresponding type.
        arg_map : dict[tuple[Vertex, str], str]
            A dictionary mapping argument names to their corresponding keyword argument names.
        """
        counters = {}
        inp_type = {}
        arg_map = {}
        for vertex in self.vertices:
            for kwd in vertex.inp_type:
                if self.argdeps[vertex][kwd] is None:
                    if kwd in counters:
                        counters[kwd] += 1
                    else:
                        counters[kwd] = 0
                    arg_name = f'{kwd}{counters[kwd]}'
                    inp_type[arg_name] = vertex.inp_type[kwd]
                    arg_map[(vertex, kwd)] = arg_name
        
        # if a preferred ordering is provided, reflect that in the
        # insertion order of the input dictionary
        if type_ordering is None:
            type_ordering = self.input_order
        
        if ( (type_ordering is not None) and 
             (Counter(inp_type.values()) == Counter(type_ordering)) ):
            new_inp_type = {}
            used = set()
            for typ in type_ordering:
                for k, v in inp_type.items():
                    if v == typ and k not in used:
                        used.add(k)
                        new_inp_type[k] = v
                        break
            inp_type = new_inp_type

        return inp_type, arg_map
    
    def get_inp_type(self) -> dict[str, type]:
        """
        Retrieve a dictionary of input types for the function graph.

        Returns
        -------
        dict[str, type]
            A dictionary where each key is an argument name and the value is
            the corresponding type of the argument.
        """
        inp_type, _ = self._get_arguments()
        return inp_type
        
    def __len__(self) -> int:
        return len(self.vertices)
    
    def __str__(self) -> str:
        inp_type = self.get_inp_type()
        return f'{self.name}({", ".join(k for k in inp_type)})'
    
    def __repr__(self) -> str:
        inp_type = self.get_inp_type()
        out_type = self.get_out_type()
        _i = ", ".join(f"{k}: {t}" for k, t in inp_type.items())
        return f'{self.name}({_i}) -> {out_type}'
    
    def straight_line(self) -> str:
        """
        Renders the function graph as a straight-line program.

        Returns
        -------
        str
            The generated straight-line program.
        """
        prog = ''
        intermediates = {}      # (vertex, kwd): str
        counter = 0

        inp_type, arg_map = self._get_arguments()
        out_type, out_map = self._get_outputs()
        order = self._get_topo_order()

        prog += f'> INPUT ({", ".join(f"${k}: {inp_type[k]}" for k in inp_type)})\n'

        for vertex in order:
            current_kwargs = {}
            for kwd in vertex.inp_type:
                if (vertex, kwd) in arg_map:
                    current_kwargs[kwd] = '$'+arg_map[(vertex, kwd)]
                elif self.argdeps[vertex][kwd] in intermediates:
                    current_kwargs[kwd] = intermediates[self.argdeps[vertex][kwd]]
            computation = ", ".join(f"{k}: {vertex.inp_type[k]} = {v}" for k, v in current_kwargs.items())
            
            names = []
            for idx in range(len(vertex)):
                var = f'!v{counter}'
                counter += 1
                intermediates[(vertex, idx)] = var
                names.append(var)
            prog += ', '.join(names) + f' = {vertex.name}({computation})\n'
        
        returns = [intermediates[o] for o in out_map]
        prog += '> RETURN ' + ", ".join(returns)
        return prog

    def __call__(self, *args, **kwargs):
        intermediates = {}      # (vertex, kwd): value

        inp_type, arg_map = self._get_arguments()
        out_type, out_map = self._get_outputs()
        order = self._get_topo_order()

        for name, value in zip(inp_type, args):
            kwargs[name] = value

        for vertex in order:
            current_kwargs = {}
            for kwd in vertex.inp_type:
                if (vertex, kwd) in arg_map:
                    current_kwargs[kwd] = kwargs[arg_map[(vertex, kwd)]]
                elif self.argdeps[vertex][kwd] is not None:
                    current_kwargs[kwd] = intermediates[self.argdeps[vertex][kwd]]
            result = vertex(**current_kwargs)
            
            for idx in range(len(vertex)):
                intermediates[(vertex, idx)] = result[idx]
        
        return tuple(intermediates[o] for o in out_map)


class RandomComposer:
    """
    A class for randomly composing functions from a module.

    Attributes
    ----------
    module : types.ModuleType
        A module object containing functions to be composed.
    funcs : dict[str, types.FunctionType]
        A dictionary of functions from the module.
    funcs_types : dict[str, tuple[Counter[type], Counter[type]]]
        A dictionary mapping function names to their input and output types.
    """

    module: types.ModuleType
    funcs: dict[str, types.FunctionType]
    funcs_types: dict[str, tuple[Counter[type], Counter[type]]]

    def __init__(self, module: types.ModuleType):
        """
        Initialize the composer with a module containing functions to be composed.

        Parameters
        ----------
        module : types.ModuleType
            A module object containing functions to be composed.
        """
        self.module = module
        self.funcs = get_funcs(module)

        self.funcs_types = {}
        for name, func in self.funcs.items():
            inp_type, out_type, _ = get_types(func)
            self.funcs_types[name] = (
                Counter(inp_type.values()),
                Counter(out_type)
            )

    def _find_resemblance_scores(
        self,
        inp_set: Counter[type] = None,
        out_set: Counter[type] = None,
        inp_weighing: float = 2.0,
        temp: float = 0.7
    ):
        resemblance = lambda x, y : (x & y).total() / (x | y).total()
        names = []
        scores = []

        for name, (fn_inp_set, fn_out_set) in self.funcs_types.items():
            score = 0
            if inp_set is not None:
                score += resemblance(inp_set, fn_inp_set) * inp_weighing
            if out_set is not None:
                score += resemblance(out_set, fn_out_set)
            
            if score > 0:
                names.append(name)
                scores.append(score)

        return names, softmax(scores, temp=temp)

    def _compose_func(
        self,
        input_type: tuple[type],
        output_type: tuple[type],
        max_depth: int,
        p_branching: float = 0.2,
        n_lookahead: int = 2,
        low_temp: float = 0.3,
        inp_weighing: float = 2.0
    ) -> FuncGraph:
        
        goal = Counter(input_type)
        frontier = Counter(output_type)
        depth_queues = {typ: [] for typ in frontier}
        for typ in output_type:              # use input_type here to maintain quantity
            heapq.heappush(
                depth_queues[typ],
                (0, None, None)             # (depth, vertex, kwd) for lexicographical ordering by depth
            )

        depth = 0
        outputs_hit = 0
        graph = FuncGraph()

        while frontier != goal or outputs_hit < len(output_type):
            
            # compute type signature resemblances
            kwargs = {
                'out_set': frontier
            }
            if depth >= max_depth - n_lookahead:
                kwargs['inp_set'] = goal
                kwargs['inp_weighing'] = inp_weighing
            if depth == 0 or depth >= max_depth - n_lookahead:
                kwargs['temp'] = low_temp   # more predictability at start and end
            names, scores = self._find_resemblance_scores(**kwargs)

            # choose a function to add
            choice = random.choices(names, weights=scores, k=1)[0]
            func = self.funcs[choice]
            fn_inp_type, fn_out_type, _ = get_types(func)
            fn_depth = 0

            # add function to graph
            vertex = FuncVertex(choice, func)
            graph.add(vertex)

            # update frontier and depth_queues with function output types
            for idx, typ in enumerate(fn_out_type):
                used = False
                while typ in frontier:     # feed useful outputs to earlier stuff first
                    used = True
                    frontier[typ] -= 1
                    if frontier[typ] == 0:
                        del frontier[typ]
                    (_d, dst, kwd) = heapq.heappop(depth_queues[typ])

                    fn_depth = max(fn_depth, _d + 1)
                    if dst is None:
                        outputs_hit += 1
                        _o = OutVertex(typ)
                        graph.add(_o)
                        graph.feed(vertex, idx, _o, OUT_KWD)
                    else:
                        graph.feed(vertex, idx, dst, kwd)
                    if random.random() > p_branching:   # allow same output to be used multiple times
                        break
                
                if not used:             # sink unused outputs
                    dst = SinkVertex(typ)
                    graph.add(dst)
                    graph.feed(vertex, idx, dst, SINK_KWD)
            
            # update frontier and depth_queues with function input types
            for kwd, typ in fn_inp_type.items():
                if typ not in depth_queues:
                    depth_queues[typ] = []
                frontier.update([typ])
                heapq.heappush(depth_queues[typ], (fn_depth, vertex, kwd))
            
            # update depth
            depth = max(depth, fn_depth)
            if depth > max_depth:
                return None
            
            # apply constants to fit goal when nearing the end
            if depth >= max_depth:
                residues = frontier - goal
                if typ not in DTYPE_GENERATORS:
                    continue
                while typ in residues:
                    residues[typ] -= 1
                    if residues[typ] == 0:
                        del residues[typ]
                    frontier[typ] -= 1
                    if frontier[typ] == 0:
                        del frontier[typ]
                    (_d, dst, kwd) = heapq.heappop(depth_queues[typ])
                    
                    v = ConstVertex(DTYPE_GENERATORS[typ]())
                    graph.add(v)
                    if dst is None:
                        outputs_hit += 1
                        _o = OutVertex(typ)
                        graph.add(_o)
                        graph.feed(v, 0, _o, OUT_KWD)
                    else:
                        graph.feed(v, 0, dst, kwd)

        graph.input_order = input_type
        graph.output_order = output_type
        return graph
    
    def sample(self, input_type, output_type, max_depth=4, seed=0):
        random.seed(seed)
        
        while True:
            graph = self._compose_func(
                input_type,
                output_type,
                max_depth
            )
            if graph is not None:
                return graph
