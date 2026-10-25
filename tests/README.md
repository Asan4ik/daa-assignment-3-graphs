# Own tests

| File | Purpose |
|---|---|
| `handmade.py` | 43 hand-derived cases (`why` explains each expected answer); `python tests/handmade.py` writes the two files below |
| `my_cases.jsonl` | inputs (one request per line) |
| `expected_outputs.jsonl` | expected answers + justification (exact, or optimum/property for non-unique answers) |
| `actual_outputs.jsonl` | actual outputs of `python tools/run.py --input tests/my_cases.jsonl` |
| `checkers.py`, `oracles.py` | semantic checkers and independent brute-force / alternative-algorithm oracles |
| `test_algorithms.py` | unit tests: hand-made cases, state reset, 1 500 random oracle comparisons, checker accept/reject tests, route helper, full-limit and deep-chain tests |
| `route_demo.py` | route-helper calls (reachable, source, unreachable, tied/parallel) |
| `bench.py`, `bench_results.json` | Kruskal vs Prim benchmark and its raw results |
| `test_run_log.txt` | verbose log of `python -m unittest discover -s tests -v` |

Commands (from the repository root):

```sh
python tools/run.py --input tests/my_cases.jsonl     # actual outputs
python -m unittest discover -s tests -v              # everything (~25 s)
python -m unittest tests.test_algorithms.FastTests   # without the 100 000 / 250 000 inputs
python tests/route_demo.py
python tests/bench.py
```
