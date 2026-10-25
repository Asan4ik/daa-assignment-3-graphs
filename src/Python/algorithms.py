"""Implement the six graph methods and your route helper. See the README at the repository root."""

import heapq

class _DSU:
    """Disjoint sets: path compression (iterative) + union by size."""

    __slots__ = ("parent", "size")

    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x):
        parent = self.parent
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(self, a, b):
        """Merge the sets of a and b; return True if they were different."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True


def dsu(request):
    """DSU with path compression and union by size; return states."""
    n = request["n"]
    operations = request["operations"]

    sets = _DSU(n)
    components = n
    largest = 1 if n > 0 else 0
    states = []
    for u, v in operations:
        if sets.union(u, v):
            components -= 1
            ra = sets.find(u)
            if sets.size[ra] > largest:
                largest = sets.size[ra]
        states.append([components, largest])
    return {"states": states}


def kruskal(request):
    """Separate Kruskal implementation; return cost, edge_ids, components."""
    n = request["n"]
    edges = request["edges"]

    order = sorted(range(len(edges)), key=lambda i: edges[i][2])
    sets = _DSU(n)
    chosen = []
    cost = 0
    for i in order:
        u, v, w = edges[i]
        if sets.union(u, v):
            chosen.append(i)
            cost += w
            if len(chosen) == n - 1:
                break
    return {"cost": cost, "edge_ids": chosen, "components": n - len(chosen)}


def prim(request):
    """Separate Prim implementation; restart for every unvisited component."""
    n = request["n"]
    edges = request["edges"]

    adjacency = [[] for _ in range(n)]
    for i, (u, v, w) in enumerate(edges):
        if u == v:
            continue
        adjacency[u].append((w, i, v))
        adjacency[v].append((w, i, u))

    visited = [False] * n
    chosen = []
    cost = 0
    components = 0
    push, pop = heapq.heappush, heapq.heappop
    for start in range(n):
        if visited[start]:
            continue
        components += 1
        visited[start] = True
        heap = list(adjacency[start])
        heapq.heapify(heap)
        while heap:
            w, i, v = pop(heap)
            if visited[v]:
                continue
            visited[v] = True
            chosen.append(i)
            cost += w
            for entry in adjacency[v]:
                if not visited[entry[2]]:
                    push(heap, entry)
    return {"cost": cost, "edge_ids": chosen, "components": components}


def scc(request):
    """Kosaraju with two DFS passes; return component and condensation."""
    n = request["n"]
    edges = request["edges"]

    raise NotImplementedError("TODO scc")


def topo(request):
    """Three-state DFS and reverse finish order; return acyclic and order."""
    n = request["n"]
    edges = request["edges"]

    raise NotImplementedError("TODO topo")


def dag(request):
    """Whole-graph cycle check and DAG relaxation; add your own route helper."""
    n = request["n"]
    source = request["source"]
    edges = request["edges"]

    raise NotImplementedError("TODO dag")
