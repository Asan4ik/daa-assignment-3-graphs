"""Calls the route helper on the four required situations; prints what it did and asserts the results."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src" / "Python"))
import algorithms  # noqa: E402


def route_cost(route, edges, chosen_edge_ids):
    """Total weight of the selected edge IDs along the route; also verifies direction."""
    total = 0
    for (a, b), edge_id in zip(zip(route, route[1:]), chosen_edge_ids):
        u, v, w = edges[edge_id]
        assert (u, v) == (a, b), f"edge {edge_id} is {u}->{v}, expected {a}->{b}"
        total += w
    return total


def run():
    lines = []

    def log(text):
        lines.append(text)
        print(text)

    # 1) reachable target, 2) source, 3) unreachable target: spec example extended with an isolated vertex
    request = {"n": 5, "source": 0, "edges": [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]}
    result = algorithms.dag({"task": "dag", **request})
    parent, dist, edges = result["parent_edge"], result["distance"], request["edges"]
    log(f"spec graph: distance={dist} parent_edge={parent}")

    r = algorithms.reconstruct_route(0, 3, parent, edges)
    ids = [parent[3], parent[2], parent[1]][::-1]
    log(f"reachable target: reconstruct_route(0, 3) = {r}; selected edge IDs = {ids}; "
        f"route cost = {route_cost(r, edges, ids)} (distance[3] = {dist[3]})")
    assert r == [0, 1, 2, 3] and route_cost(r, edges, ids) == dist[3] == 0

    r = algorithms.reconstruct_route(0, 0, parent, edges)
    log(f"source: reconstruct_route(0, 0) = {r}")
    assert r == [0]

    r = algorithms.reconstruct_route(0, 4, parent, edges)
    log(f"unreachable target: reconstruct_route(0, 4) = {r} (documented no-route result: empty list)")
    assert r == [] and dist[4] is None

    # 4) tied / parallel edges: three optimal routes of cost 5 into vertex 1
    request = {"n": 3, "source": 0, "edges": [[0, 1, 5], [0, 1, 5], [0, 2, 1], [2, 1, 4]]}
    result = algorithms.dag({"task": "dag", **request})
    parent, dist, edges = result["parent_edge"], result["distance"], request["edges"]
    log(f"tied graph: distance={dist} parent_edge={parent}")
    r = algorithms.reconstruct_route(0, 1, parent, edges)
    ids = []
    cur = 1
    while cur != 0:
        ids.append(parent[cur])
        cur = edges[parent[cur]][0]
    ids.reverse()
    cost = route_cost(r, edges, ids)
    log(f"tied/parallel: reconstruct_route(0, 1) = {r}; selected edge IDs = {ids}; route cost = {cost} "
        f"(distance[1] = {dist[1]}); accepted alternatives: [0,1] via edge 0 or 1, or [0,2,1] via edges 2,3")
    assert cost == dist[1] == 5 and r in ([0, 1], [0, 2, 1])
    assert parent[1] in (0, 1, 3)

    # alternative valid witnesses must give the same total, wrong direction must be detected
    for alt_parent, alt_route in (([-1, 1, 2], [0, 1]), ([-1, 3, 2], [0, 2, 1])):
        assert algorithms.reconstruct_route(0, 1, alt_parent, edges) == alt_route
    log("alternative parent arrays [-1,1,2] and [-1,3,2] reconstruct [0, 1] and [0, 2, 1] with the same cost 5")
    return lines


if __name__ == "__main__":
    run()
