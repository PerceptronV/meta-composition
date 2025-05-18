import primitives
from composer import FuncGraph, FuncVertex

g = FuncGraph()
a = FuncVertex('int_add', primitives.int_add)
b = FuncVertex('repeat', primitives.str_repeat)

g.add(a)
g.add(b)
g.feed(a, 0, b, 'n')    # feeds output 0 of funcvertex a to input 'n' of funcvertex b

print(g)
print(repr(g), '\n')

print(g.get_inp_type())
print(g.get_out_type(), '\n')

print(g.straight_line())
print(g(s0='a', x0=2, y0=3))
