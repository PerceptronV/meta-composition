import primitives
import generators
from composer import FuncGraph, FuncVertex, RandomComposer

g = FuncGraph()
a = FuncVertex('int_add', primitives.int_add)
b = FuncVertex('repeat', primitives.str_repeat)
c = FuncVertex('int_sub', primitives.int_sub)

g.add(a)
g.add(b)
g.add(c)
g.feed(a, 0, b, 'n')    # feeds output 0 of funcvertex a to input 'n' of funcvertex b
g.feed(a, 0, c, 'x')

print(g)
print(repr(g), '\n')

print(g.get_inp_type())
print(g.get_out_type(), '\n')

g.input_order = (int, str, int, int)
g.output_order = (int, str)
print(g.straight_line())
print(g(2, 'a', 3, 4))

print('\n\nGENERATION\n\n')

inp_type = (int, str, float)
out_type = (int, str)
comp = RandomComposer(primitives)
g = comp.sample(inp_type, out_type, max_depth=4, seed=0)
print(g.straight_line(), '\n')

for _ in range(10):
    inp = tuple(generators.DTYPE_GENERATORS[typ]() for typ in inp_type)
    print(inp, '->', g(*inp))
