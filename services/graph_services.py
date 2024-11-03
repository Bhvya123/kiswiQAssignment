from models.graph import Edge, Node, Graph, GraphRunConfig
from typing import List
import uuid
from collections import deque

VISITED, VISITING, UNVISITED = 0, 1, 2

def validate_helper(node_id, status, node_dict, visited_edges):
    status[node_id] = VISITING
    node = node_dict[node_id]
    seen_src_keys = {}
    for edge in node.paths_in:
        src_node = node_dict[edge.src_node]
        dst_node = node
        if edge.src_to_dst_data_keys:
            for src_key, dst_key in edge.src_to_dst_data_keys.items():
                if not dst_node.data_in:
                    break
                if (src_node.data_out and src_key not in src_node.data_out) or (dst_node.data_in and dst_key not in dst_node.data_in):
                    raise ValueError(f"Data key {src_node} from {edge.src_node} to {dst_key} in {edge.dst_node} missing")
                # if src_node.data_out[src_key] != dst_node.data_in[dst_key]:
                #     raise ValueError(f"Type mismatch on edge from {edge.src_node} to {edge.dst_node}: {src_key} and {dst_key} have incompatible types")
        if edge.src_node in seen_src_keys:
            for src_key, dst_key in edge.src_to_dst_data_keys.items():
                if seen_src_keys[edge.src_node].get(dst_key) == src_key:
                    raise ValueError(f"Duplicate edge detected from {edge.src_node} to {node_id} targeting {dst_key}")        
        else:
            seen_src_keys[edge.src_node] = edge.src_to_dst_data_keys
        if status[edge.src_node] == UNVISITED:
            if not validate_helper(edge.src_node, status, node_dict, visited_edges):
                return False
            elif status[edge.src_node] == VISITING:
                raise ValueError(f"Cycle detected in the graph")
        visited_edges.add((edge.src_node, edge.dst_node))    
    for edge in node.paths_out:
        if (edge.src_node, edge.dst_node) in visited_edges:
            raise ValueError(f"Edge parity violation: outgoing edge from {edge.src_node} to {edge.dst_node} has corresponding incoming edge")
        dst_node = node_dict[edge.dst_node]
        if edge not in dst_node.paths_in:
            raise ValueError(f"Edge parity violation: {edge.dst_node} does not recognise incoming edge from {edge.src_node}")
        status[node_id] = VISITED
    return True

def validate(graph: Graph):
    status = {node.node_id: UNVISITED for node in graph.nodes}
    node_dict = {node.node_id: node for node in graph.nodes}    # To access nodes quickly
    visited_edges = set()   # For parity check of edges for duplicate detection
    for node in graph.nodes:
        if status[node.node_id] == UNVISITED:
            if not validate_helper(node.node_id, status, node_dict, visited_edges):
                return False
    return True

def run_graph(graph: Graph, config: GraphRunConfig):
    # Modifying data_in of nodes based on root_inputs and data_overwrites
    for node in graph.nodes:
        if node.node_id in config.root_inputs:
            node.data_in = {}
            node.data_in.update(config.root_inputs[node.node_id])
        if node.data_in is None:
            node.data_in = {}
        if node.node_id in config.data_overwrites:
            node.data_in.update(config.data_overwrites[node.node_id])
    
    # Removing unwanted edges from paths_in and paths_out
    for node in graph.nodes:
        node.paths_out = [
            edge for edge in node.paths_out 
            if edge.src_node in config.enable_list 
            and edge.dst_node not in config.disable_list
        ]
        node.paths_in = [
            edge for edge in node.paths_in 
            if edge.src_node in config.enable_list 
            and edge.dst_node not in config.disable_list
        ]
    
    # Keeping only those nodes in graph which are not in disable_list and are in enable_list
    if config.enable_list:
        graph.nodes = [node for node in graph.nodes if node.node_id in config.enable_list]
    if config.disable_list:
        graph.nodes = [node for node in graph.nodes if node.node_id not in config.disable_list]

    # LevelOrder
    level_order = level_wise_order(graph, config)
    node_levels = {}
    for level_index, level_nodes in enumerate(level_order):
        for node_id in level_nodes:
            node_levels[node_id] = level_index

    # Processing the data transfers through edges after initial root_inputs and data_overwrites are set
    for node in graph.nodes:
        for edge in node.paths_in:
            src_node = next((n for n in graph.nodes if n.node_id == edge.src_node), None)
            if src_node:
                if not edge.src_to_dst_data_keys:
                    edge.src_to_dst_data_keys = {}
                for src_key, dst_key in edge.src_to_dst_data_keys.items():
                    if node.data_in is None:
                        node.data_in = {}
                    node.data_in[dst_key] = (
                        (src_node.data_out.get(src_key) if src_node.data_out else None) or
                        node.data_in.get(dst_key, None)
                    )
        outgoing_edges = {}
        for edge in node.paths_out:
            dst_node = next((n for n in graph.nodes if n.node_id == edge.dst_node), None)
            if dst_node:
                if not edge.src_to_dst_data_keys:
                    edge.src_to_dst_data_keys = {}
                for src_key, dst_key in edge.src_to_dst_data_keys.items():
                    if dst_key:
                        if dst_node.node_id not in outgoing_edges:
                            outgoing_edges[dst_node.node_id] = []
                        outgoing_edges[dst_node.node_id].append((src_key, dst_key, node.node_id))

        # Processing for the outgoing edges in same level
        for dst_node_id, transfers in outgoing_edges.items():
            dst_node_level = node_levels[dst_node_id]
            same_level_transfers = [
                (src_key, dst_key, src_node_id) for (src_key, dst_key, src_node_id) in transfers 
                if node_levels[src_node_id] == dst_node_level 
            ]

            same_level_transfers.sort(key=lambda x: x[2])  # x[2] -> source node ID

            # Send data only from the first node in lexicographical order at the same level
            if same_level_transfers:
                first_transfer = same_level_transfers[0]
                src_key, dst_key, _ = first_transfer
                if dst_key:
                    if dst_node.data_in is None:
                        dst_node.data_in = {}
                    dst_node.data_in[dst_key] = (node.data_out.get(src_key) if node.data_out else None)
    topological_order = toposort(graph)
    islands = getIslands(graph)
    # Creating unique run ID for the runConfig
    run_id = str(uuid.uuid4())
    return run_id, graph, {node.node_id: node.data_out for node in topological_order}, level_order, islands


def toposort(graph: Graph) -> List[Node]:
    order, visited = [], set()
    def dfs(node):
        if node.node_id in visited:
            return
        visited.add(node.node_id)
        for edge in node.paths_out:
            for dst_node in graph.nodes:
                if dst_node.node_id == edge.dst_node:
                    dfs(dst_node)
        order.append(node)
    for node in graph.nodes:
        if node.node_id not in visited:
            dfs(node)
    return order[::-1]

def level_wise_order(graph: Graph, config: GraphRunConfig) -> List[List[str]]:
    level_order = []
    node_map = {node.node_id: node for node in graph.nodes}
    in_degree = {node.node_id: 0 for node in graph.nodes}
    for node in graph.nodes:
        for edge in node.paths_out:
            in_degree[edge.dst_node] += 1
    queue = deque([node_id for node_id in in_degree.keys() if in_degree[node_id] == 0])
    while queue:
        current_level = []
        level_size = len(queue)
        print(level_size)
        for _ in range(level_size):
            node_id = queue.popleft()
            current_level.append(node_id)
            current_node = node_map[node_id]
            for edge in current_node.paths_out:
                if edge.src_node not in node_map.keys() or edge.dst_node not in node_map.keys():
                    continue
                in_degree[edge.dst_node] -= 1
                if in_degree[edge.dst_node] == 0:
                    queue.append(edge.dst_node)
        level_order.append(current_level)

    return level_order

def getIslands(graph: Graph) -> List[List[str]]:
    node_map = {node.node_id: node for node in graph.nodes}
    def dfs(node_id, visited, components):
        visited.add(node_id)
        components.append(node_id)
        for edge in node_map[node_id].paths_out:
            if edge.dst_node not in visited:
                dfs(edge.dst_node, visited, components)
    visited = set()
    islands = []
    for node_id, _ in node_map.items():
        if node_id not in visited:
            component = []
            dfs(node_id, visited, component)
            islands.append(component)    
    return islands

