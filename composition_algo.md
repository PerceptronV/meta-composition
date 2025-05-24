
# Random Sampling Algorithm for Arbitrary DSL with Type Annotations

The goal is to randomly 'wire' function primitives into a function graph with desired input and output type signatures. 

Within this algorithm, the input into each primitive can be one of three types:
1. A direct input into the function graph; or
2. Another function's outputs; or
3. A constant value

Each function's outputs have to be:
1. Used as an output, and/or
2. Wired to another function as input; or
3. Sunk (never used)

Over each iteration, the algorithm chooses one new function primitive, wires its outputs to wherever they are still needed, and pushes the primtive's inputs into a `frontier` set, to be satisfied in the future iterations (by one of the three types above).

## The Search State

**Require:** multiset of desired input type signatures `input_type` $T^\leftarrow$, multiset of desired output type signatures `output_type` $T^\rightarrow$, maximum depth of function graph `max_depth` $d_{max}$.

| Variable | Meaning |
|----------|-------------------------------------------|
| `goal`: $T^\leftarrow$ | Equals `input_type`. Multiset of the desired input type signature (for the entire function graph as a whole). |
| `frontier`: $F$ | Multiset of input types waiting to be satisfied by future function outputs, direct inputs, or a constant value. This is initialised to the desired output type signature `output_type` $T^\rightarrow$ (so that we can find primitives that give the desired output type signature). |
| `depth`: $d$ | Integer that tracks the current longest path in the function graph, measured in number of primitive compositions (e.g. `f(g(...))` has depth 2). This measures the complexity of the current graph. _Note: When constructing the graph, the depth of each primitive is also tracked separately (an output primitive has depth 1, and the primitive that feeds into it has depth 2, and so on)._ |
| `depth_queues`: $Q$ | If there are multiple instances of the same type waiting to be satisfied in `frontier`, how do we choose which one to satisfy first? `depth_queues` maintains a Min Heap for each instance of the types in `frontier`, so that we prioritise satisfying inputs with a lower depth. _Note: All desired output types are pushed into `depth_queues` with depth 0._ |
| `outputs_hit`: $n$ | Integer that counts the number of desired output types that have been satsified via primitive outputs. |

## Multiset Resemblance

Given two multisets $A, B$, we define their resemblance to be $r(A, B) = \frac{|A \cap B|}{|A \cup B|}$. This helps us score each primitive by how much their type signature resembles a particular signature.

## The Algorithm

Assume we have function primitives $f_i$, each with a multiset of input type signatures $t^\leftarrow_i$ and output type signatures $t^\rightarrow_i$.

While $F \neq T$ **and** $n < |T^\rightarrow|$:
   - Compute the set resemblance $r(t^\rightarrow_i, F)$ between each primitive's **output** type signature and the current `frontier` $F$; if `depth` $d$ is close to `max_depth` $d_{max}$ (e.g. $d \geq d_{max} - 2$), additionally also compute the set resemblance $r(t^\leftarrow, T^\leftarrow)$ between each primitive's **input** type signatures and `input_type`. This gives a resemblances vector $\bf{r}$.
   - Apply softmax with temperature $\tau$ to compute scores $\bf{s} = \sigma(\bf{r}, \tau)$. Use a lower temperature when `depth` $d=0$ or $d$ is close to $d_{max}$ so we reliably get primitives that satisfy our requirements.
   - Sample a primitive function $f_i$, with probabilities weighed by their respective scores in $\bf{s}$.
   - Wire each output type in $t^\rightarrow_i$ to its corresponding destination in `frontier` $F$, and prioritise wiring to lower depths. Increment $n$ when wiring directly to a desired output type (which have depth 0).
      - With probability 0.2, wire the same output to another input in `frontier` $F$, so that 'branching' occurs in the function graph and one output can be re-used in multiple places.
      - The depth $d_i$ of primitive $f_i$ is equal to 1 plus the greatest depth of the primitives it wires to.
   - Push the input types $t^\leftarrow_i$ of $f_i$ into frontier $F$, and update `depth_queues` $Q$ with the depth $d_i$ of primitive $f_i$. This enables the inputs of $f_i$ to be satisfied by future functions, inputs, or constants.
   - Update graph-wise depth $d$ to be $\max(d, d_i)$.
   - If $d \geq d_{max}$, try a last-resort fix to satisfy excess frontier types ($F - T^\leftarrow$) by randomly selecting constants.
      - E.g. If $F = \{int, int, str\}$ and $T^\leftarrow = \{int, str\}$, we can satisfy the extra $int$ type by plugging in an random integer as a constant input.
