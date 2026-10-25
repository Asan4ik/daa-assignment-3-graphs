"""Hand-made test cases. Expected answers are derived by hand (see `why`), not by running the solution.

Expected values for non-unique answers are properties, checked semantically:
  dsu      -> exact "states"
  kruskal/prim -> optimum "cost" and "components"
  scc      -> reference label per vertex (compared as a partition)
  topo     -> "acyclic"
  dag      -> "acyclic" and exact "distance"

Run `python tests/handmade.py` to (re)write tests/my_cases.jsonl and tests/expected_outputs.jsonl.
"""
import json
import pathlib

B = 10 ** 9
CASES = []


def case(name, request, expected, why):
    CASES.append({"name": name, "request": request, "expected": expected, "why": why})


def mst(name, n, edges, cost, comps, why):
    for task in ("kruskal", "prim"):
        case(f"{task}: {name}", {"task": task, "n": n, "edges": edges},
             {"cost": cost, "components": comps}, why)


# ---- DSU ---------------------------------------------------------------------------------------
case("dsu: spec example", {"task": "dsu", "n": 4, "operations": [[0, 1], [1, 2], [0, 2], [3, 3]]},
     {"states": [[3, 2], [2, 3], [2, 3], [2, 3]]},
     "0-1 merges (3 comps, size 2); 1-2 adds vertex 2 (2, 3); 0-2 is already connected; 3-3 is a self-union.")
case("dsu: n=0", {"task": "dsu", "n": 0, "operations": []}, {"states": []}, "No vertices, no operations, no states.")
case("dsu: n=1 self union", {"task": "dsu", "n": 1, "operations": [[0, 0]]}, {"states": [[1, 1]]},
     "A single vertex stays one component of size 1.")
case("dsu: n>0 without operations", {"task": "dsu", "n": 3, "operations": []}, {"states": []},
     "No operation means no state (the initial state is not reported).")
case("dsu: repeats and chain", {"task": "dsu", "n": 5, "operations": [[0, 1], [2, 3], [1, 0], [3, 4], [0, 4]]},
     {"states": [[4, 2], [3, 2], [3, 2], [2, 3], [1, 5]]},
     "{0,1}; {2,3}; repeat; {2,3,4} gives largest 3; joining both gives one component of 5.")

# ---- Kruskal / Prim (same graphs) ----------------------------------------------------------------
mst("spec example with isolate", 4, [[0, 1, 4], [1, 2, 2], [0, 2, 3]], 5, 2,
    "Triangle needs 2 edges: 2+3 = 5; vertex 3 is isolated so there are 2 components.")
mst("n=0", 0, [], 0, 0, "Empty graph: cost 0, zero components.")
mst("only a negative self-loop", 1, [[0, 0, -7]], 0, 1, "A self-loop is never selected, even when negative.")
mst("negative, parallel, loop", 3, [[0, 0, -5], [0, 1, 2], [0, 1, -3], [1, 2, 0]], -3, 1,
    "Ignore the loop; between the parallel 0-1 edges take -3; plus 1-2 weight 0: total -3.")
mst("sum beyond 32 bits", 4, [[0, 1, B], [1, 2, B], [2, 3, B], [0, 3, B]], 3 * B, 1,
    "Any 3 of 4 equal edges: 3*10^9 = 3 000 000 000 > 2^31.")
mst("negative sum beyond 32 bits", 4, [[0, 1, -B], [1, 2, -B], [2, 3, -B], [0, 3, -B]], -3 * B, 1,
    "Any 3 of 4 equal edges: -3 000 000 000 < -2^31.")
mst("isolates and one edge", 5, [[1, 2, 5]], 5, 4, "One edge; vertices 0,3,4 isolated: components = {0},{1,2},{3},{4}.")
mst("two components with ties", 6, [[0, 1, 1], [1, 2, 1], [0, 2, 1], [3, 4, 2], [4, 5, -2], [3, 5, -2]], -2, 2,
    "Triangle one: 1+1 = 2. Triangle two: -2-2 = -4. Total -2, two components.")

# ---- SCC -----------------------------------------------------------------------------------------
case("scc: spec example", {"task": "scc", "n": 4, "edges": [[0, 1], [1, 0], [1, 2], [0, 2], [2, 3]]},
     {"component": [0, 0, 2, 3]}, "0<->1 form one SCC; 2 and 3 are singletons. Condensation: {01}->{2}->{3}.")
case("scc: n=0", {"task": "scc", "n": 0, "edges": []}, {"component": []}, "Empty graph.")
case("scc: isolates", {"task": "scc", "n": 3, "edges": []}, {"component": [0, 1, 2]},
     "No edges: three singleton SCCs, no condensation edges.")
case("scc: duplicates and self-loops",
     {"task": "scc", "n": 3, "edges": [[0, 0], [0, 1], [0, 1], [1, 2], [2, 1]]}, {"component": [0, 1, 1]},
     "{0} and {1,2}; the duplicate 0->1 edge must give ONE condensation pair; loops are internal.")
case("scc: cycle plus tail", {"task": "scc", "n": 5, "edges": [[0, 1], [1, 2], [2, 0], [2, 3], [3, 4]]},
     {"component": [0, 0, 0, 3, 4]}, "{0,1,2} is a cycle, then 3 and 4 hang off it as singletons.")
case("scc: many parallel cross edges",
     {"task": "scc", "n": 4, "edges": [[0, 1], [1, 0], [2, 3], [3, 2], [0, 2], [1, 3], [1, 2]]},
     {"component": [0, 0, 2, 2]}, "{0,1} and {2,3}; three cross edges collapse to the single pair ({01},{23}).")

# ---- Topological order -------------------------------------------------------------------------
case("topo: spec example", {"task": "topo", "n": 4, "edges": [[0, 2], [1, 2], [2, 3]]}, {"acyclic": True},
     "Edges 0->2, 1->2, 2->3 have no cycle.")
case("topo: n=0", {"task": "topo", "n": 0, "edges": []}, {"acyclic": True}, "Empty graph is acyclic.")
case("topo: self-loop", {"task": "topo", "n": 2, "edges": [[1, 1]]}, {"acyclic": False}, "A self-loop is a cycle.")
case("topo: cycle in a later component",
     {"task": "topo", "n": 5, "edges": [[0, 1], [2, 3], [3, 4], [4, 2]]}, {"acyclic": False},
     "Vertices 0-1 are fine, but 2->3->4->2 is a cycle: every component must be checked.")
case("topo: diamond (finished vertex is not a cycle)",
     {"task": "topo", "n": 4, "edges": [[0, 1], [0, 2], [1, 3], [2, 3]]}, {"acyclic": True},
     "DFS reaches 3 twice; the second visit hits a FINISHED vertex, which is not a cycle.")
case("topo: parallel edges", {"task": "topo", "n": 2, "edges": [[0, 1], [0, 1]]}, {"acyclic": True},
     "Two copies of 0->1 are still acyclic.")
case("topo: two-cycle", {"task": "topo", "n": 2, "edges": [[0, 1], [1, 0]]}, {"acyclic": False}, "0->1->0.")

# ---- DAG shortest paths ------------------------------------------------------------------------
case("dag: spec example",
     {"task": "dag", "n": 5, "source": 0, "edges": [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]},
     {"acyclic": True, "distance": [0, 3, -4, 0, None]},
     "d1=3; d2=min(8, 3-7)=-4; d3=-4+4=0; vertex 4 has no incoming path.")
case("dag: singleton", {"task": "dag", "n": 1, "source": 0, "edges": []},
     {"acyclic": True, "distance": [0]}, "Only the source, distance 0.")
case("dag: unreachable vs distance -1", {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, -1]]},
     {"acyclic": True, "distance": [0, -1, None]}, "Vertex 1 is reachable at cost -1; vertex 2 is unreachable (null).")
case("dag: cycle unreachable from source",
     {"task": "dag", "n": 4, "source": 0, "edges": [[0, 1, 1], [2, 3, 1], [3, 2, 1]]},
     {"acyclic": False, "distance": []}, "2<->3 is a cycle although the source cannot reach it: the whole graph counts.")
case("dag: self-loop on source", {"task": "dag", "n": 2, "source": 0, "edges": [[0, 0, 1]]},
     {"acyclic": False, "distance": []}, "A self-loop makes the graph cyclic.")
case("dag: tied and parallel edges",
     {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, 5], [0, 1, 5], [0, 2, 1], [2, 1, 4]]},
     {"acyclic": True, "distance": [0, 5, 1]}, "Vertex 1 has three optimal routes of cost 5 (edge 0, edge 1, or 0->2->1).")
case("dag: 64-bit negative chain",
     {"task": "dag", "n": 4, "source": 0, "edges": [[0, 1, -B], [1, 2, -B], [2, 3, -B]]},
     {"acyclic": True, "distance": [0, -B, -2 * B, -3 * B]}, "Each hop costs -10^9, the last total -3 000 000 000.")
case("dag: source is not vertex 0",
     {"task": "dag", "n": 4, "source": 2, "edges": [[3, 1, 2], [2, 3, 7], [0, 2, 1]]},
     {"acyclic": True, "distance": [None, 9, 0, 7]},
     "From 2: 2->3 costs 7, 3->1 costs 2 so 9; vertex 0 only has an edge INTO the source, so it is unreachable.")
case("dag: negative edge wins over direct edge",
     {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, 4], [0, 2, 1], [2, 1, -5]]},
     {"acyclic": True, "distance": [0, -4, 1]}, "d1 = min(4, 1-5) = -4.")


def write():
    root = pathlib.Path(__file__).resolve().parent
    with open(root / "my_cases.jsonl", "w", encoding="utf-8") as f:
        for c in CASES:
            f.write(json.dumps(c["request"], separators=(",", ":")) + "\n")
    with open(root / "expected_outputs.jsonl", "w", encoding="utf-8") as f:
        for c in CASES:
            f.write(json.dumps({"name": c["name"], "expected": c["expected"], "why": c["why"]},
                               separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"wrote {len(CASES)} cases")


if __name__ == "__main__":
    write()
