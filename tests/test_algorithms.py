"""Own tests for Assignment 3. Run from the repository root:

    python -m unittest discover -s tests -v          (everything, including full-limit tests)
    python tests/test_algorithms.py FastTests         (skip the big inputs)

The solution is exercised through the real JSON Lines entry point (src/Python/main.py) wherever
the transport matters, and through direct calls for the many small randomised comparisons.
"""
import json
import pathlib
import random
import subprocess
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "Python"))
sys.path.insert(0, str(ROOT / "tests"))

import algorithms  # noqa: E402
import checkers  # noqa: E402
import handmade  # noqa: E402
import oracles  # noqa: E402
import route_demo  # noqa: E402

MAIN = [sys.executable, str(ROOT / "src" / "Python" / "main.py")]
FUNCS = {"dsu": algorithms.dsu, "kruskal": algorithms.kruskal, "prim": algorithms.prim,
         "scc": algorithms.scc, "topo": algorithms.topo, "dag": algorithms.dag}
B = 10 ** 9


def run_process(requests, timeout=20):
    """Send requests to ONE main.py process; return (answers, seconds)."""
    data = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in requests)
    start = time.perf_counter()
    done = subprocess.run(MAIN, input=data, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    elapsed = time.perf_counter() - start
    assert done.returncode == 0, done.stderr[:2000]
    lines = done.stdout.splitlines()
    assert len(lines) == len(requests), "one output line per request"
    return [json.loads(line) for line in lines], elapsed


def verify(request, answer, expected):
    """Semantic verification of one answer against the hand/oracle-derived expectation."""
    task = request["task"]
    if task == "dsu":
        return answer == expected
    if task in ("kruskal", "prim"):
        return checkers.check_forest(request, answer, expected["cost"], expected["components"])
    if task == "scc":
        return checkers.check_scc(request, answer, expected["component"])
    if task == "topo":
        return checkers.check_topo(request, answer, expected["acyclic"])
    if task == "dag":
        return checkers.check_dag(request, answer, expected["acyclic"], expected.get("distance"))
    raise AssertionError(task)


# =================================================================================================
class FastTests(unittest.TestCase):

    # ---- hand-made cases through the real entry point; also writes tests/actual_outputs.jsonl ---
    def test_handmade_cases_through_json_lines(self):
        requests = [c["request"] for c in handmade.CASES]
        answers, _ = run_process(requests)
        with open(ROOT / "tests" / "actual_outputs.jsonl", "w", encoding="utf-8") as f:
            for a in answers:
                f.write(json.dumps(a, separators=(",", ":")) + "\n")
        for case, answer in zip(handmade.CASES, answers):
            with self.subTest(case["name"]):
                self.assertTrue(verify(case["request"], answer, case["expected"]), (answer, case["why"]))

    def test_state_reset_mixed_repeated_requests_in_one_process(self):
        cases = handmade.CASES
        shuffled = cases[::-1]
        batch = cases + shuffled + cases[::3] + cases            # repeated and reordered, mixed tasks
        requests = [{"task": "ping"}] + [c["request"] for c in batch]
        answers, _ = run_process(requests)
        self.assertEqual(answers[0], {"status": "ready"})
        for case, answer in zip(batch, answers[1:]):
            self.assertTrue(verify(case["request"], answer, case["expected"]), case["name"])
        # identical requests must give identical deterministic answers every time
        first = {json.dumps(c["request"]): a for c, a in zip(cases, answers[1:])}
        for case, answer in zip(batch, answers[1:]):
            self.assertEqual(answer, first[json.dumps(case["request"])], case["name"])

    # ---- randomised comparison with brute-force oracles ----------------------------------------
    def test_random_small_graphs_against_oracles(self):
        rng = random.Random(20260425)
        for trial in range(1500):
            n = rng.randint(0, 7)
            tag = f"trial {trial}"
            ops = [[rng.randrange(n), rng.randrange(n)] for _ in range(rng.randint(0, 9))] if n else []
            self.assertEqual(algorithms.dsu({"n": n, "operations": ops})["states"],
                             oracles.dsu_oracle(n, ops), tag)

            m = rng.randint(0, 9) if n else 0
            wmax = rng.choice([1, 3, B])
            wedges = [[rng.randrange(n), rng.randrange(n), rng.randint(-wmax, wmax)] for _ in range(m)]
            cost, comps = oracles.mst_oracle(n, wedges)
            for task in ("kruskal", "prim"):
                req = {"task": task, "n": n, "edges": wedges}
                self.assertTrue(checkers.check_forest(req, FUNCS[task](req), cost, comps), (tag, task, wedges))

            pairs = [[rng.randrange(n), rng.randrange(n)] for _ in range(rng.randint(0, 10))] if n else []
            reference = oracles.scc_oracle(n, pairs)
            req = {"task": "scc", "n": n, "edges": pairs}
            self.assertTrue(checkers.check_scc(req, algorithms.scc(req), reference), (tag, pairs))
            acyclic = oracles.acyclic_oracle(n, pairs)
            req = {"task": "topo", "n": n, "edges": pairs}
            self.assertTrue(checkers.check_topo(req, algorithms.topo(req), acyclic), (tag, pairs))

            if n:
                src = rng.randrange(n)
                if rng.random() < 0.7:                           # acyclic by construction (random relabelling)
                    perm = list(range(n))
                    rng.shuffle(perm)
                    dedges = []
                    for _ in range(rng.randint(0, 10)):
                        a, b = sorted(rng.sample(range(n), 2)) if n > 1 else (0, 0)
                        if n > 1:
                            dedges.append([perm[a], perm[b], rng.randint(-wmax, wmax)])
                else:
                    dedges = [[rng.randrange(n), rng.randrange(n), rng.randint(-5, 5)] for _ in range(rng.randint(0, 8))]
                is_acyclic = oracles.acyclic_oracle(n, [[u, v] for u, v, _ in dedges])
                dist = oracles.dag_oracle(n, src, dedges) if is_acyclic else []
                req = {"task": "dag", "n": n, "source": src, "edges": dedges}
                self.assertTrue(checkers.check_dag(req, algorithms.dag(req), is_acyclic, dist), (tag, dedges))

    # ---- checkers: accept alternative valid answers, reject invalid witnesses -----------------
    def test_checker_accepts_alternative_forests_and_rejects_invalid(self):
        req = {"task": "kruskal", "n": 3, "edges": [[0, 1, 1], [1, 2, 1], [0, 2, 1]]}
        for ids in ([0, 1], [1, 2], [0, 2], [2, 0]):                 # three different optimal forests
            self.assertTrue(checkers.check_forest(req, {"cost": 2, "edge_ids": ids, "components": 1}, 2, 1))
        bad = [
            {"cost": 3, "edge_ids": [0, 1, 2], "components": 1},     # contains a cycle
            {"cost": 1, "edge_ids": [0], "components": 1},           # does not span
            {"cost": 2, "edge_ids": [0, 0], "components": 1},        # repeated edge ID
            {"cost": 2, "edge_ids": [0, 5], "components": 1},        # ID out of range
            {"cost": 3, "edge_ids": [0, 1], "components": 1},        # claimed cost differs from optimum
            {"cost": 2, "edge_ids": [0, 1], "components": 2},        # wrong component count
        ]
        for answer in bad:
            self.assertFalse(checkers.check_forest(req, answer, 2, 1), answer)
        loop = {"task": "kruskal", "n": 2, "edges": [[0, 0, -9], [0, 1, 4]]}
        self.assertFalse(checkers.check_forest(loop, {"cost": -5, "edge_ids": [0, 1], "components": 1}, 4, 1))
        self.assertFalse(checkers.check_forest(loop, {"cost": -9, "edge_ids": [0], "components": 1}, 4, 1))

    def test_checker_accepts_alternative_scc_labels_and_rejects_invalid(self):
        req = {"task": "scc", "n": 4, "edges": [[0, 1], [1, 0], [1, 2], [0, 2], [2, 3]]}
        reference = [0, 0, 2, 3]
        self.assertTrue(checkers.check_scc(req, {"component": [5, 5, 7, 9], "condensation": [[5, 7], [7, 9]]}, reference))
        self.assertTrue(checkers.check_scc(req, {"component": [9, 9, 4, 0], "condensation": [[4, 0], [9, 4]]}, reference))
        bad = [
            {"component": [5, 5, 5, 9], "condensation": [[5, 9]]},                    # wrongly merged SCCs
            {"component": [5, 6, 7, 9], "condensation": [[5, 7], [6, 5], [5, 6], [6, 7], [7, 9]]},  # wrongly split
            {"component": [5, 5, 7, 9], "condensation": [[5, 7]]},                    # missing pair
            {"component": [5, 5, 7, 9], "condensation": [[5, 7], [5, 7], [7, 9]]},    # duplicate pair
            {"component": [5, 5, 7, 9], "condensation": [[5, 7], [7, 9], [5, 5]]},    # internal pair
            {"component": [5, 5, 7, 9], "condensation": [[5, 7], [9, 7]]},            # reversed direction
            {"component": [5, 5, 7, -1], "condensation": [[5, 7], [7, -1]]},          # negative label
        ]
        for answer in bad:
            self.assertFalse(checkers.check_scc(req, answer, reference), answer)

    def test_checker_topological_orders(self):
        req = {"task": "topo", "n": 4, "edges": [[0, 2], [1, 2], [2, 3]]}
        for order in ([0, 1, 2, 3], [1, 0, 2, 3]):
            self.assertTrue(checkers.check_topo(req, {"acyclic": True, "order": order}, True))
        for order in ([2, 0, 1, 3], [0, 1, 2], [0, 1, 2, 2], [0, 1, 2, 4]):
            self.assertFalse(checkers.check_topo(req, {"acyclic": True, "order": order}, True), order)
        self.assertFalse(checkers.check_topo(req, {"acyclic": False, "order": []}, True))
        cyc = {"task": "topo", "n": 2, "edges": [[0, 1], [1, 0]]}
        self.assertTrue(checkers.check_topo(cyc, {"acyclic": False, "order": []}, False))
        self.assertFalse(checkers.check_topo(cyc, {"acyclic": False, "order": [0, 1]}, False))

    def test_checker_dag_witnesses(self):
        req = {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, 5], [0, 1, 5], [0, 2, 1], [2, 1, 4]]}
        dist = [0, 5, 1]
        for parent in ([-1, 0, 2], [-1, 1, 2], [-1, 3, 2]):          # parallel edges and the 0->2->1 route
            self.assertTrue(checkers.check_dag(req, {"acyclic": True, "distance": dist, "parent_edge": parent}, True, dist))
        bad = [
            [-1, 2, 2],     # edge 2 ends at vertex 2, not at vertex 1
            [-1, 0, 0],     # edge 0 ends at vertex 1, not at vertex 2
            [-1, 3, -1],    # reachable vertex 2 has no parent edge
            [0, 0, 2],      # source must have parent -1
            [-1, 0, 9],     # edge ID out of range
        ]
        for parent in bad:
            self.assertFalse(checkers.check_dag(req, {"acyclic": True, "distance": dist, "parent_edge": parent}, True, dist), parent)
        self.assertFalse(checkers.check_dag(req, {"acyclic": True, "distance": [0, 6, 1], "parent_edge": [-1, 0, 2]}, True, dist))
        unreachable = {"task": "dag", "n": 2, "source": 0, "edges": []}
        self.assertFalse(checkers.check_dag(unreachable, {"acyclic": True, "distance": [0, None], "parent_edge": [-1, 0]}, True, [0, None]))
        self.assertFalse(checkers.check_dag(unreachable, {"acyclic": True, "distance": [0, -1], "parent_edge": [-1, -1]}, True, [0, None]))

    def test_solution_output_differs_from_wrong_answers(self):
        """Mutation sanity: the checkers must fail on a deliberately damaged real answer."""
        req = {"task": "kruskal", "n": 4, "edges": [[0, 1, 4], [1, 2, 2], [0, 2, 3]]}
        ans = algorithms.kruskal(req)
        self.assertTrue(checkers.check_forest(req, ans, 5, 2))
        self.assertFalse(checkers.check_forest(req, {**ans, "edge_ids": [0, 1]}, 5, 2))   # 4+2 = 6 != 5

    # ---- route helper ---------------------------------------------------------------------------
    def test_route_helper_all_required_cases(self):
        lines = route_demo.run()
        self.assertEqual(len(lines), 7)

    def test_route_helper_robustness(self):
        edges = [[0, 1, 1], [1, 2, 1]]
        self.assertEqual(algorithms.reconstruct_route(0, 2, [-1, 0, 1], edges), [0, 1, 2])
        self.assertEqual(algorithms.reconstruct_route(1, 1, [-1, -1, 1], edges), [1])
        self.assertEqual(algorithms.reconstruct_route(0, 2, [-1, -1, -1], edges), [])
        self.assertEqual(algorithms.reconstruct_route(0, 2, [-1, 1, 0], [[2, 1, 0], [1, 2, 0]]), [])  # looping witness

    def test_n_zero_and_loops_edge_cases(self):
        self.assertEqual(algorithms.dsu({"n": 0, "operations": []}), {"states": []})
        self.assertEqual(algorithms.kruskal({"n": 0, "edges": []}), {"cost": 0, "edge_ids": [], "components": 0})
        self.assertEqual(algorithms.prim({"n": 0, "edges": []}), {"cost": 0, "edge_ids": [], "components": 0})
        self.assertEqual(algorithms.scc({"n": 0, "edges": []}), {"component": [], "condensation": []})
        self.assertEqual(algorithms.topo({"n": 0, "edges": []}), {"acyclic": True, "order": []})
        self.assertEqual(algorithms.dag({"n": 1, "source": 0, "edges": []}),
                         {"acyclic": True, "distance": [0], "parent_edge": [-1]})


# =================================================================================================
def chain_edges(n, weight=None):
    return [[i, i + 1] if weight is None else [i, i + 1, weight(i)] for i in range(n - 1)]


class LargeTests(unittest.TestCase):
    """Full published limits: n = 100 000, m or operations = 250 000, plus 100 000-vertex deep chains."""

    N, M = 100_000, 250_000

    def run_checked(self, request, expected, label):
        answers, seconds = run_process([request])
        ok = verify(request, answers[0], expected)
        print(f"  [{label}] {seconds:.2f}s via main.py (limit 20s)")
        self.assertTrue(ok, label)
        self.assertLess(seconds, 20)
        return answers[0]

    def test_dsu_full_limit_random_and_deep_chain(self):
        rng = random.Random(1)
        ops = [[rng.randrange(self.N), rng.randrange(self.N)] for _ in range(self.M)]
        self.run_checked({"task": "dsu", "n": self.N, "operations": ops},
                         {"states": oracles.dsu_small_to_large(self.N, ops)}, "dsu random 100000/250000")
        chain = [[i, i + 1] for i in range(self.N - 1)]
        expected = [[self.N - 1 - i, i + 2] for i in range(self.N - 1)]
        self.run_checked({"task": "dsu", "n": self.N, "operations": chain}, {"states": expected}, "dsu chain")
        # reverse chain: each new vertex is the first argument, so the big tree is always the second one
        reverse = [[i, i - 1] for i in range(1, self.N)]
        self.run_checked({"task": "dsu", "n": self.N, "operations": reverse},
                         {"states": oracles.dsu_small_to_large(self.N, reverse)}, "dsu reverse chain")

    def test_mst_full_limit(self):
        rng = random.Random(2)
        graphs = {
            "random 100000/250000": (self.N, [[rng.randrange(self.N), rng.randrange(self.N), rng.randint(-B, B)]
                                              for _ in range(self.M)]),
            "sparse, many components 100000/50000": (self.N, [[rng.randrange(self.N), rng.randrange(self.N), rng.randint(-B, B)]
                                                              for _ in range(50_000)]),
            "dense 1000/250000 (many parallel edges)": (1000, [[rng.randrange(1000), rng.randrange(1000), rng.randint(-B, B)]
                                                              for _ in range(self.M)]),
            "all weights +1e9, 3e9+ totals": (self.N, [[i, i + 1, B] for i in range(self.N - 1)]),
            "all weights -1e9 with ties": (self.N, [[rng.randrange(self.N), rng.randrange(self.N), -B] for _ in range(self.M)]),
        }
        for label, (n, edges) in graphs.items():
            cost, comps = oracles.boruvka(n, edges)                  # third, independent algorithm
            for task in ("kruskal", "prim"):
                self.run_checked({"task": task, "n": n, "edges": edges}, {"cost": cost, "components": comps},
                                 f"{task} {label}")

    def test_scc_full_limit_and_deep_chains(self):
        n = self.N
        forward = chain_edges(n)
        answer = self.run_checked({"task": "scc", "n": n, "edges": forward}, {"component": list(range(n))}, "scc forward chain")
        self.assertEqual(len(answer["condensation"]), n - 1)
        self.run_checked({"task": "scc", "n": n, "edges": [[b, a] for a, b in forward]},
                         {"component": list(range(n))}, "scc reverse chain")
        cycle = forward + [[n - 1, 0]]
        answer = self.run_checked({"task": "scc", "n": n, "edges": cycle}, {"component": [0] * n}, "scc one 100000-cycle")
        self.assertEqual(len(set(answer["component"])), 1)
        self.assertEqual(answer["condensation"], [])
        rng = random.Random(3)
        random_edges = [[rng.randrange(n), rng.randrange(n)] for _ in range(self.M)]
        self.run_checked({"task": "scc", "n": n, "edges": random_edges},
                         {"component": oracles.tarjan_scc(n, random_edges)}, "scc random vs Tarjan")
        sparse = [[rng.randrange(n), rng.randrange(n)] for _ in range(n // 2)]
        self.run_checked({"task": "scc", "n": n, "edges": sparse},
                         {"component": oracles.tarjan_scc(n, sparse)}, "scc sparse random vs Tarjan")

    def random_dag(self, rng, n, m, weight):
        perm = list(range(n))
        rng.shuffle(perm)                                            # hidden topological order
        edges = []
        for _ in range(m):
            a, b = sorted(rng.sample(range(n), 2))
            edges.append([perm[a], perm[b], rng.randint(-weight, weight)])
        return perm, edges

    def test_topo_full_limit_and_deep_chains(self):
        n = self.N
        forward = chain_edges(n)
        self.run_checked({"task": "topo", "n": n, "edges": forward}, {"acyclic": True}, "topo forward chain")
        self.run_checked({"task": "topo", "n": n, "edges": [[b, a] for a, b in forward]}, {"acyclic": True}, "topo reverse chain")
        self.run_checked({"task": "topo", "n": n, "edges": forward + [[n - 1, 0]]}, {"acyclic": False}, "topo chain closed to a cycle")
        self.run_checked({"task": "topo", "n": n, "edges": forward + [[n // 2, n // 2]]}, {"acyclic": False}, "topo chain with one self-loop")
        _, edges = self.random_dag(random.Random(4), n, self.M, 0)
        self.run_checked({"task": "topo", "n": n, "edges": [[u, v] for u, v, _ in edges]}, {"acyclic": True}, "topo random DAG 250000")

    def test_dag_full_limit_and_deep_chains(self):
        n = self.N
        weights = lambda i: -B if i % 2 else B                       # noqa: E731  alternating +-1e9
        edges = chain_edges(n, weights)
        expected, total = [0], 0
        for i in range(n - 1):
            total += weights(i)
            expected.append(total)
        answer = self.run_checked({"task": "dag", "n": n, "source": 0, "edges": edges},
                                  {"acyclic": True, "distance": expected}, "dag deep chain")
        self.assertEqual(algorithms.reconstruct_route(0, n - 1, answer["parent_edge"], edges), list(range(n)))
        # source in the middle: first half unreachable (null), second half reachable
        mid = n // 2
        expected_mid = [None] * mid + [0]
        total = 0
        for i in range(mid, n - 1):
            total += weights(i)
            expected_mid.append(total)
        self.run_checked({"task": "dag", "n": n, "source": mid, "edges": edges},
                         {"acyclic": True, "distance": expected_mid}, "dag chain, source in the middle")
        # cycle at the far end, unreachable from the source
        cyc = chain_edges(10, lambda i: 1) + [[n - 2, n - 1, 1], [n - 1, n - 2, 1]]
        self.run_checked({"task": "dag", "n": n, "source": 0, "edges": cyc},
                         {"acyclic": False}, "dag unreachable 2-cycle at the end of a large graph")
        rng = random.Random(5)
        perm, rand_edges = self.random_dag(rng, n, self.M, B)
        src = perm[0]
        dist = [None] * n                                            # independent DP in the hidden topological order
        dist[src] = 0
        out = {}
        for u, v, w in rand_edges:
            out.setdefault(u, []).append((v, w))
        for u in perm:
            if dist[u] is not None:
                for v, w in out.get(u, ()):
                    if dist[v] is None or dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
        self.run_checked({"task": "dag", "n": n, "source": src, "edges": rand_edges},
                         {"acyclic": True, "distance": dist}, "dag random 100000/250000, weights +-1e9")

    def test_big_mixed_batch_in_one_process(self):
        rng = random.Random(6)
        n = 20_000
        edges = [[rng.randrange(n), rng.randrange(n), rng.randint(-B, B)] for _ in range(50_000)]
        requests = [
            {"task": "kruskal", "n": n, "edges": edges}, {"task": "prim", "n": n, "edges": edges},
            {"task": "scc", "n": n, "edges": [[u, v] for u, v, _ in edges]},
            {"task": "topo", "n": 3, "edges": [[0, 1], [1, 2]]}, {"task": "dsu", "n": 3, "operations": [[0, 1]]},
        ] * 2
        answers, seconds = run_process(requests)
        self.assertEqual(answers[:5], answers[5:])
        self.assertEqual(answers[0]["cost"], answers[1]["cost"])
        print(f"  [mixed big batch, repeated twice in one process] {seconds:.2f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
