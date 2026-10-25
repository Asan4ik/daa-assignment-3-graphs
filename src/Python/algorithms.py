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

    forward = [[] for _ in range(n)]
    transpose = [[] for _ in range(n)]
    for u, v in edges:
        forward[u].append(v)
        transpose[v].append(u)

    seen = [False] * n
    pointer = [0] * n
    finish = []
    for root in range(n):
        if seen[root]:
            continue
        seen[root] = True
        stack = [root]
        while stack:
            u = stack[-1]
            neighbours = forward[u]
            if pointer[u] < len(neighbours):
                v = neighbours[pointer[u]]
                pointer[u] += 1
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
            else:
                finish.append(u)
                stack.pop()

    component = [-1] * n
    count = 0
    for root in reversed(finish):
        if component[root] != -1:
            continue
        component[root] = count
        stack = [root]
        while stack:
            u = stack.pop()
            for v in transpose[u]:
                if component[v] == -1:
                    component[v] = count
                    stack.append(v)
        count += 1

    pairs = set()
    for u, v in edges:
        a, b = component[u], component[v]
        if a != b:
            pairs.add(a * count + b)
    condensation = [[key // count, key % count] for key in pairs]
    return {"component": component, "condensation": condensation}


def _adjacency(n, pairs, weighted=False):
    adjacency = [[] for _ in range(n)]
    if weighted:
        for i, (u, v, w) in enumerate(pairs):
            adjacency[u].append((v, w, i))
    else:
        for u, v in pairs:
            adjacency[u].append(v)
    return adjacency


def _topological_order(n, adjacency, neighbour=lambda entry: entry):
    state = [0] * n          # 0 unvisited, 1 active, 2 finished
    pointer = [0] * n
    finish = []
    for root in range(n):
        if state[root]:
            continue
        state[root] = 1
        stack = [root]
        while stack:
            u = stack[-1]
            neighbours = adjacency[u]
            if pointer[u] < len(neighbours):
                v = neighbour(neighbours[pointer[u]])
                pointer[u] += 1
                if state[v] == 0:
                    state[v] = 1
                    stack.append(v)
                elif state[v] == 1:
                    return None
            else:
                state[u] = 2
                finish.append(u)
                stack.pop()
    finish.reverse()
    return finish


def topo(request):
    """Three-state DFS and reverse finish order; return acyclic and order."""
    n = request["n"]
    edges = request["edges"]

    order = _topological_order(n, _adjacency(n, edges))
    if order is None:
        return {"acyclic": False, "order": []}
    return {"acyclic": True, "order": order}


def dag(request):
    """Whole-graph cycle check and DAG relaxation; route helper is reconstruct_route."""
    n = request["n"]
    source = request["source"]
    edges = request["edges"]

    adjacency = _adjacency(n, edges, weighted=True)
    order = _topological_order(n, adjacency, neighbour=lambda entry: entry[0])
    if order is None:
        return {"acyclic": False, "distance": [], "parent_edge": []}

    distance = [None] * n
    parent_edge = [-1] * n
    distance[source] = 0
    for u in order:
        du = distance[u]
        if du is None:
            continue
        for v, w, i in adjacency[u]:
            candidate = du + w
            if distance[v] is None or candidate < distance[v]:
                distance[v] = candidate
                parent_edge[v] = i
    return {"acyclic": True, "distance": distance, "parent_edge": parent_edge}


def reconstruct_route(source, target, parent_edge, edges):
    if target == source:
        return [source]
    if parent_edge[target] == -1:
        return []
    route = [target]
    current = target
    while current != source:
        edge_id = parent_edge[current]
        if edge_id == -1 or len(route) > len(parent_edge):
            return []
        current = edges[edge_id][0]
        route.append(current)
    route.reverse()
    return route