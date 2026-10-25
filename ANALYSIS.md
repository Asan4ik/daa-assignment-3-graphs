# Analysis & Implementation Report: Graph Algorithms

## 1. Overview & General Architecture
All graph algorithms (`dsu`, `kruskal`, `prim`, `scc`, `topo`, and `dag`) along with the `reconstruct_route` helper are implemented in `src/Python/algorithms.py` using Python 3.12. 

### State Reset
* **Design:** Every method strictly encapsulates its state using local variables created during the function call. There are no global caches, module-level state variables, or persistent data structures across requests.
* **Verification:** Tested by submitting mixed test cases, sending the same cases in reverse order, and interleaving requests within a single long-running process to ensure complete isolation.

### Deep DFS & Recursion Safety
* **Design:** Python's default recursion limit can easily trigger `RecursionError` on deep graphs. To handle chains up to $100,000$ vertices safely, all DFS traversals (used in SCC, Topological Sort, and DAG) are implemented iteratively using an explicit stack.
* **Adjacency Pointers:** Each vertex on the stack maintains an adjacency pointer tracking how many neighbors have been processed. When a vertex is revisited, traversal resumes directly from its pointer, ensuring adjacency lists are never scanned twice ($O(n + m)$ time overall).

---

## 2. Algorithm Breakdown

### DSU (Disjoint-Set Union)
* **Steps:** Initialize `parent[i] = i`, `size[i] = 1`, `components = n`, and `largest = 1` (or `0` if $n = 0$). For each pair $(u, v)$, find roots using iterative path compression. If roots differ, attach the smaller tree to the larger one, update sizes, decrement `components`, and update `largest`. Append `[components, largest]` to `states` after each operation (including self-unions and repeated unions).
* **Invariant:** The trees formed by the `parent` array correspond exactly to the connected components, and `size[root]` correctly stores the number of vertices in that tree.
* **Correctness:** Path compression and union-by-size preserve set equivalence classes. Self-loops and duplicate unions do not alter connectivity or component counts.
* **Boundary Cases:** $n = 0$ (yielding no states), zero operations, self-unions, duplicate pairs, and linear chains of $100,000$ elements.
* **Complexity:** $O(n + q \alpha(n))$ amortized time, $O(n + q)$ memory.

### Kruskal's Algorithm
* **Steps:** Extract all edges, sort edge indices by weight, and iterate through them. If `find(u) != find(v)`, union the components, record the edge ID, and accumulate its weight. Terminate when $n - 1$ edges are chosen (or edges are exhausted). `components` is computed as $n - \text{number of chosen edges}$.
* **Invariant:** At any step, the chosen edges form a minimum spanning forest of the subgraph processed so far.
* **Correctness:** Follows the cut property (choosing the minimum weight safe edge) while avoiding cycles via DSU. Self-loops are naturally skipped because their endpoints share the same root.
* **Boundary Cases:** $n = 0$, graphs with no edges, only self-loops, parallel edges, tied weights, negative weights, disconnected components, and isolated vertices.
* **Complexity:** $O(n + m \log(m+1))$ time, $O(n + m)$ memory.

### Prim's Algorithm
* **Steps:** Build adjacency lists containing `(weight, edge_id, neighbour)` tuples, ignoring self-loops. Iterate through all unvisited vertices, incrementing the component count, marking the vertex visited, and pushing its outgoing edges into a binary heap (`heapq`). Pop the minimum edge; if its destination is already visited, discard it. Otherwise, visit the node, record the edge ID, add its weight, and push its unvisited outgoing edges.
* **Invariant:** The selected edges within the current component form a minimum spanning tree over the visited vertex subset, and the heap maintains all outgoing boundary edges.
* **Correctness:** Correctly applies the cut property via a lazy priority queue. Restarts ensure all disconnected components and isolated vertices are fully processed.
* **Boundary Cases:** Same as Kruskal. Parallel edges are handled correctly as secondary copies are discarded upon visiting their destination vertex.
* **Complexity:** $O(n + m \log(m+1))$ time, $O(n + m)$ memory.

### Kosaraju's Strongly Connected Components (SCC)
* **Steps:** Construct the original graph and its transpose. Pass 1 runs an iterative DFS on the original graph, recording vertices in finishing order. Pass 2 processes vertices in reverse finishing order; each unlabelled vertex initiates a DFS on the transpose graph to mark an SCC. Condensation edges $(u, v)$ between different component labels are deduplicated using a hash set keyed by $a \cdot \text{count} + b$.
* **Invariant:** Each traversal in Pass 2 discovers exactly one strongly connected component.
* **Correctness:** Based on the standard Kosaraju property where latest finishing times in the original graph guarantee valid topological ordering of components on the transpose graph.
* **Boundary Cases:** $n = 0$, isolated vertices, self-loops, duplicate edges, multi-edge bundles between components, cycles of $100,000$ vertices, and bidirectional chains.
* **Complexity:** $O(n + m)$ expected time, $O(n + m)$ memory.

### Topological Ordering
* **Steps:** Run an iterative DFS over all vertices using three states (0: unvisited, 1: active/on stack, 2: finished). If an edge points to an active vertex, a cycle exists (`acyclic = false`, `order = []`). Edges to finished vertices are skipped. Once all outgoing edges of a vertex are processed, it is marked finished and appended to a list. If acyclic, return the reversed finish list.
* **Invariant:** Active vertices represent the current recursion stack path, and finished vertices have all their descendants fully resolved.
* **Correctness:** Back-edges to active vertices detect all directed cycles. Without cycles, finishing order reversal ensures every directed edge $u \to v$ places $u$ before $v$.
* **Boundary Cases:** $n = 0$, self-loops, 2-cycles, cycles in downstream components, diamond structures (visiting a finished node twice), and chains of $100,000$ vertices.
* **Complexity:** $O(n + m)$ time and memory.

### DAG Shortest Paths & Route Helper
* **Steps:** Run the topological DFS check across the graph. If any cycle is detected (even in unreachable components), return `acyclic = false`. Otherwise, initialize `distance = None` and `parent_edge = -1`, setting `distance[source] = 0`. Iterate through vertices in topological order, skipping unreachable nodes (`distance is None`), and relax outgoing edges, updating distances and `parent_edge` when shorter paths are found.
* **Invariant:** When a vertex is processed in topological order, its shortest distance from the source is finalized.
* **Correctness:** Topological ordering guarantees that all incoming edges to any vertex are relaxed before the vertex itself is processed. Negative weights are permitted since the graph is verified to be acyclic.
* **Boundary Cases:** $n = 1$, unreachable vertices, cycles outside source reachability, non-zero sources, parallel/tied edges, and weights exceeding 32-bit limits.
* **Route Reconstruction Helper (`reconstruct_route`):** Starts at target, iteratively traverses backward using `parent_edge` to source, and reverses the node sequence. Returns `[source]` for source-to-source, `[]` for unreachable targets or broken parent loops, and correctly handles tied/parallel edges.

---

## 3. Route Helper Verification & Traces

Running `python tests/route_demo.py` produced the following verified outputs:

* **Reachable Target (`0` to `3`):**
  * `reconstruct_route(0, 3) = [0, 1, 2, 3]`
  * Selected edge IDs: `[0, 2, 3]`
  * Edge weights & directions: edge `0` ($0 \to 1, w=3$), edge `2` ($1 \to 2, w=-7$), edge `3` ($2 \to 3, w=4$).
  * Total weight verification: $3 - 7 + 4 = 0$ (matches `distance[3] = 0`).
* **Source (`0` to `0`):**
  * `reconstruct_route(0, 0) = [0]` (Cost: `0`).
* **Unreachable Target (`0` to `4`):**
  * `reconstruct_route(0, 4) = []` (Documented no-route result; JSON distance correctly outputs `null`).
* **Tied / Parallel Edges (`0` to `1`):**
  * Routes of cost `5`: direct parallel edges (`0` or `1`), or via intermediate vertex `2` (`0 -> 2 -> 1` using edges `2` and `3`). The solver successfully reconstructs valid paths matching cost `5`.

---

## 4. Benchmark: Kruskal vs. Prim

### Setup & Methodology
* **Environment:** Linux x86_64, Intel Xeon 2.10 GHz (1 CPU), 4 GB RAM, CPython 3.12.3.
* **Generator & Seed:** Random graphs generated via `random.Random(20261025 + n)`. Each edge configured as `[randrange(n), randrange(n), randint(-1e9, 1e9)]` (incorporating loops, parallel edges, and disconnected components). Both algorithms received identical edge lists.
* **Timing & Measurement:** Measured using `time.perf_counter()`. One uncounted warm-up call per size and method. `gc.collect()` invoked prior to each timed run. 5 timed runs executed, reporting the median.
* **Timing Boundary:** Excludes graph generation, JSON parsing, and input/output formatting. Includes method preprocessing (Kruskal: sorting and DSU init; Prim: adjacency list construction and heap initialization).

### Results

| Size $(n, m)$ | Kruskal Timings (s) | Kruskal Median | Prim Timings (s) | Prim Median | Ratio (Prim / Kruskal) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$(1,000, 5,000)$** | $0.0024, 0.0024, 0.0023, 0.0022, 0.0023$ | **$0.0023\text{ s}$** | $0.0046, 0.0044, 0.0043, 0.0043, 0.0044$ | **$0.0044\text{ s}$** | $\approx 1.9\times$ |
| **$(10,000, 50,000)$** | $0.0358, 0.0355, 0.0350, 0.0354, 0.0355$ | **$0.0355\text{ s}$** | $0.0826, 0.0814, 0.0830, 0.0790, 0.0788$ | **$0.0814\text{ s}$** | $\approx 2.3\times$ |
| **$(100,000, 250,000)$** | $0.3769, 0.3882, 0.4187, 0.3715, 0.3625$ | **$0.3769\text{ s}$** | $0.9067, 0.9156, 0.9654, 0.9984, 0.9124$ | **$0.9156\text{ s}$** | $\approx 2.4\times$ |

### Observations & Limitations
* **Asymptotic Parity:** Both algorithms operate in $O(n + m \log m)$ time and $O(n + m)$ memory theoretically.
* **Performance Gap:** Kruskal consistently outperformed Prim by roughly $1.9\times$ to $2.4\times$. This occurs because CPython executes Kruskal's core sorting step largely in optimized C code, whereas Prim's lazy heap approach involves heavier Python-level interpreter loop overhead for repeated heap pushes, pops, and adjacency dictionary lookups.
* **Scaling:** Scaling inputs by $10\times$ in vertices and $5\times$ in edges increased execution time by approximately $10.6\times$ for Kruskal and $11.2\times$ for Prim, scaling linearly with edge count.
* **Limitations:** Benchmarks reflect a single CPython interpreter runtime, specific CPU constraints, and randomly generated edge distributions. Results may vary across dense graphs, other programming languages, or when utilizing pre-sorted inputs.

---

## 5. Academic Integrity & Acknowledgments
* **AI Tools Assistance:** Claude was used during the development process to brainstorm clean iterator patterns for explicit-stack DFS, verify JSON lines formatting rules, write documentation and structure benchmarking scripts
* **Student Verification:** All algorithms, data structures, test suites (`tests/handmade.py`), route helper logic, and empirical benchmarks were independently reviewed, executed, debugged, and verified by the student