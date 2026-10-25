"""Brute-force reference solutions for tiny graphs. They deliberately share no code with src/Python."""
from itertools import combinations


def components_count(n, edges):
    label = list(range(n))
    for e in edges:
        a, b = label[e[0]], label[e[1]]
        label = [a if x == b else x for x in label]
    return len(set(label))


def mst_oracle(n, edges):
    """Try every subset of edges (m <= 12): the cheapest acyclic subset with n - c edges is optimal."""
    c = components_count(n, edges)
    best = None
    for subset in combinations(range(len(edges)), n - c):
        label = list(range(n))
        ok, total = True, 0
        for i in subset:
            u, v, w = edges[i]
            if label[u] == label[v]:
                ok = False
                break
            a, b = label[u], label[v]
            label = [a if x == b else x for x in label]
            total += w
        if ok and (best is None or total < best):
            best = total
    return best, c


def reach_closure(n, edges):
    """reach[i][j] = a path with >= 1 edge from i to j (Warshall)."""
    reach = [[False] * n for _ in range(n)]
    for e in edges:
        reach[e[0]][e[1]] = True
    for k in range(n):
        for i in range(n):
            if reach[i][k]:
                for j in range(n):
                    if reach[k][j]:
                        reach[i][j] = True
    return reach


def scc_oracle(n, edges):
    reach = reach_closure(n, edges)
    labels = [-1] * n
    for v in range(n):
        if labels[v] == -1:
            labels[v] = v
            for u in range(v + 1, n):
                if reach[v][u] and reach[u][v]:
                    labels[u] = v
    return labels


def acyclic_oracle(n, edges):
    reach = reach_closure(n, edges)
    return not any(reach[v][v] for v in range(n))


def dag_oracle(n, source, edges):
    """Bellman-Ford; valid because a DAG has no cycles at all."""
    INF = None
    dist = [INF] * n
    dist[source] = 0
    for _ in range(n):
        for u, v, w in edges:
            if dist[u] is not None and (dist[v] is None or dist[u] + w < dist[v]):
                dist[v] = dist[u] + w
    return dist


def dsu_oracle(n, operations):
    label = list(range(n))
    states = []
    for u, v in operations:
        a, b = label[u], label[v]
        label = [a if x == b else x for x in label]
        counts = {}
        for x in label:
            counts[x] = counts.get(x, 0) + 1
        states.append([len(counts), max(counts.values())])
    return states


def tarjan_scc(n, edges):
    """Iterative Tarjan: an independent algorithm used only to cross-check Kosaraju on large inputs."""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
    index = [-1] * n
    low = [0] * n
    on = [False] * n
    labels = [-1] * n
    stack, counter, comps = [], 0, 0
    for root in range(n):
        if index[root] != -1:
            continue
        work = [(root, 0)]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on[root] = True
        while work:
            u, i = work.pop()
            if i < len(adj[u]):
                work.append((u, i + 1))
                v = adj[u][i]
                if index[v] == -1:
                    index[v] = low[v] = counter
                    counter += 1
                    stack.append(v)
                    on[v] = True
                    work.append((v, 0))
                elif on[v]:
                    low[u] = min(low[u], index[v])
            else:
                if low[u] == index[u]:
                    while True:
                        w = stack.pop()
                        on[w] = False
                        labels[w] = comps
                        if w == u:
                            break
                    comps += 1
                if work:
                    p = work[-1][0]
                    low[p] = min(low[p], low[u])
    return labels


def boruvka(n, edges):
    """Third MST algorithm (Boruvka, ties broken by edge ID) for cross-checking optimum cost."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    total, comps = 0, n
    while True:
        best = {}
        for i, (u, v, w) in enumerate(edges):
            a, b = find(u), find(v)
            if a == b:
                continue
            for r in (a, b):
                if r not in best or (w, i) < (edges[best[r]][2], best[r]):
                    best[r] = i
        if not best:
            break
        for i in set(best.values()):
            u, v, w = edges[i]
            a, b = find(u), find(v)
            if a != b:
                parent[a] = b
                total += w
                comps -= 1
    return total, comps


def dsu_small_to_large(n, operations):
    """Independent DSU model: merge the smaller member list into the larger one."""
    owner = list(range(n))
    members = {i: [i] for i in range(n)}
    comps = n
    largest = 1 if n else 0
    states = []
    for u, v in operations:
        a, b = owner[u], owner[v]
        if a != b:
            if len(members[a]) < len(members[b]):
                a, b = b, a
            for x in members[b]:
                owner[x] = a
            members[a].extend(members.pop(b))
            comps -= 1
            largest = max(largest, len(members[a]))
        states.append([comps, largest])
    return states
