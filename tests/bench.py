"""Benchmark Kruskal vs Prim on identical graphs at three sizes.

    python tests/bench.py            # writes tests/bench_results.json and prints a Markdown table

Boundary: the graph is generated and held in memory BEFORE timing (generation and JSON parsing/output
are excluded). Timed region = one call of algorithms.kruskal(request) / algorithms.prim(request), which
INCLUDES each method's own preprocessing (Kruskal: sorting + DSU; Prim: adjacency lists + heap).
Timer: time.perf_counter(). One untimed warm-up call per method per size, gc.collect() before every
timed call, 5 timed repetitions, median reported. Python has no compilation step to exclude.
Correctness (equal cost and component count, valid forest, cross-check with Boruvka) is verified first.
"""
import json
import pathlib
import platform
import random
import statistics
import sys
import gc
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "Python"))
sys.path.insert(0, str(ROOT / "tests"))
import algorithms  # noqa: E402
import checkers  # noqa: E402
import oracles  # noqa: E402

SEED = 20261025
SIZES = [(1_000, 5_000), (10_000, 50_000), (100_000, 250_000)]   # (n, m); the last is the published maximum
REPEATS = 5
B = 10 ** 9


def make_graph(n, m, seed):
    rng = random.Random(seed)
    return [[rng.randrange(n), rng.randrange(n), rng.randint(-B, B)] for _ in range(m)]


def timed(function, request):
    gc.collect()
    start = time.perf_counter()
    result = function(request)
    return time.perf_counter() - start, result


def main():
    rows = []
    for n, m in SIZES:
        edges = make_graph(n, m, SEED + n)
        request = {"n": n, "edges": edges}
        cost, comps = oracles.boruvka(n, edges)
        row = {"n": n, "m": m, "seed": SEED + n, "cost": cost, "components": comps}
        for name, function in (("kruskal", algorithms.kruskal), ("prim", algorithms.prim)):
            _, warm = timed(function, request)                       # warm-up (untimed)
            assert checkers.check_forest({"n": n, "edges": edges}, warm, cost, comps), (name, n)
            runs = [timed(function, request)[0] for _ in range(REPEATS)]
            row[name] = {"timings_s": [round(t, 4) for t in runs], "median_s": round(statistics.median(runs), 4)}
        rows.append(row)
        print(f"n={n} m={m}: kruskal {row['kruskal']['timings_s']} median {row['kruskal']['median_s']} | "
              f"prim {row['prim']['timings_s']} median {row['prim']['median_s']}", file=sys.stderr)
    env = {"python": platform.python_version(), "implementation": platform.python_implementation(),
           "platform": platform.platform(), "machine": platform.machine(), "processor": platform.processor() or "n/a",
           "cpu_count": __import__("os").cpu_count(), "timer": "time.perf_counter", "repeats": REPEATS,
           "warmup_calls_per_method_per_size": 1}
    (ROOT / "tests" / "bench_results.json").write_text(json.dumps({"environment": env, "results": rows}, indent=1))
    print("| n | m | method | timings (s) | median (s) |\n|---:|---:|---|---|---:|")
    for r in rows:
        for name in ("kruskal", "prim"):
            print(f"| {r['n']:,} | {r['m']:,} | {name} | {', '.join(map(str, r[name]['timings_s']))} | {r[name]['median_s']} |")
    print(json.dumps(env))


if __name__ == "__main__":
    main()
