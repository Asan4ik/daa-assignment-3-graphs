"""Semantic checkers for answers that are not unique (written independently of src/Python)."""


def is_int(x):
    return type(x) is int and -(1 << 63) <= x < (1 << 63)


def check_forest(req, out, opt_cost, opt_components):
    """Valid minimum spanning forest: feasible edge IDs, no cycle, spans every component, optimal cost."""
    n, edges = req["n"], req["edges"]
    if out.get("cost") != opt_cost or out.get("components") != opt_components:
        return False
    ids = out["edge_ids"]
    if len(ids) != len(set(ids)) or len(ids) != n - opt_components:
        return False
    parent = list(range(n))                      # own tiny union-find (path halving), independent of the solution

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def merge(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        parent[rb] = ra
        return True

    total = 0
    for i in ids:
        if not (is_int(i) and 0 <= i < len(edges)):
            return False
        u, v, w = edges[i]
        if not merge(u, v):                      # self-loop or cycle
            return False
        total += w
    if total != opt_cost:
        return False
    return all(find(u) == find(v) for u, v, _ in edges)   # still spans every original component


def check_scc(req, out, reference_labels):
    """Same partition as the reference and exactly the set of distinct cross-component pairs."""
    labels = out["component"]
    if len(labels) != len(reference_labels) or any(not is_int(x) or x < 0 for x in labels):
        return False
    fwd, rev = {}, {}
    for a, b in zip(labels, reference_labels):
        if fwd.setdefault(a, b) != b or rev.setdefault(b, a) != a:
            return False
    pairs = [tuple(p) for p in out["condensation"]]
    expected = {(labels[u], labels[v]) for u, v in req["edges"] if labels[u] != labels[v]}
    return len(pairs) == len(set(pairs)) and set(pairs) == expected


def check_topo(req, out, expected_acyclic):
    if out["acyclic"] is not expected_acyclic:
        return False
    if not expected_acyclic:
        return out["order"] == []
    order, n = out["order"], req["n"]
    if sorted(order) != list(range(n)):
        return False
    pos = {v: i for i, v in enumerate(order)}
    return all(pos[u] < pos[v] for u, v in req["edges"])


def check_dag(req, out, expected_acyclic, expected_distance):
    """Distances must equal the optimum; every parent edge must end at its vertex and chain to the source."""
    if out["acyclic"] is not expected_acyclic:
        return False
    if not expected_acyclic:
        return out["distance"] == [] and out["parent_edge"] == []
    n, s, edges = req["n"], req["source"], req["edges"]
    dist, par = out["distance"], out["parent_edge"]
    if dist != expected_distance or len(par) != n:
        return False
    for v in range(n):
        if v == s or dist[v] is None:
            if par[v] != -1:
                return False
            continue
        if not (0 <= par[v] < len(edges)):
            return False
        a, b, w = edges[par[v]]
        if b != v or dist[a] is None or dist[a] + w != dist[v]:
            return False
    done = [False] * n                            # following parents must reach the source (memoised, O(n))
    done[s] = True
    for v in range(n):
        if dist[v] is None or done[v]:
            continue
        chain, cur = [], v
        while not done[cur]:
            chain.append(cur)
            if len(chain) > n:
                return False
            cur = edges[par[cur]][0]
        for c in chain:
            done[c] = True
    return True
