from models.graph import Edge, Node, Graph, GraphRunConfig
from typing import List
from models.database_models import update_node_mapping, Session
from collections import defaultdict
import uuid
from collections import deque

# Helper function for validation to check for duplicates, dataType mismatch and detect cycles in graph
VISITED, VISITING, UNVISITED = 0, 1, 2

# Helper function for validation to check for duplicates, data type mismatch, cycles, and islands
def validate_helper(node_id, status, node_dict, visited_edges, root_map):
    status[node_id] = VISITING
    node = node_dict[node_id]
    seen_src_keys = {}

    for edge in node.paths_in:
        src_node = node_dict[edge.src_node]
        dst_node = node
        if edge.src_to_dst_data_keys:
            for src_key, dst_key in edge.src_to_dst_data_keys.items():
                # Check for missing keys in source and destination nodes
                if (src_node.data_out and src_key not in src_node.data_out.keys()) or (dst_node.data_in and dst_key not in dst_node.data_in.keys()):
                    print(f"Data key {src_key} from {edge.src_node} to {dst_key} in {edge.dst_node} missing")
                    return False
                # Check for data type mismatch
                if src_node.data_out[src_key].split(",")[1] != dst_node.data_in[dst_key].split(",")[1]:
                    print(f"Type mismatch on edge from {edge.src_node} to {edge.dst_node}: {src_key} and {dst_key} have incompatible types")
                    return False

        # Check for duplicate edges
        if edge.src_node in seen_src_keys:
            for src_key, dst_key in edge.src_to_dst_data_keys.items():
                if seen_src_keys[edge.src_node].get(dst_key) == src_key:
                    print(f"Duplicate edge detected from {edge.src_node} to {node_id} targeting {dst_key}")        
                    return False
        else:
            seen_src_keys[edge.src_node] = edge.src_to_dst_data_keys

        # Recursive DFS check for cycles
        if status[edge.src_node] == UNVISITED:
            if not validate_helper(edge.src_node, status, node_dict, visited_edges, root_map):
                return False
        elif status[edge.src_node] == VISITING:
            print(f"Cycle detected in the graph")
            return False
        
        # Mark the edge as visited
        visited_edges.add((edge.src_node, edge.dst_node))
    
    # Parity check for incoming edges
    for edge in node.paths_out:
        if (edge.src_node, edge.dst_node) in visited_edges:
            print(f"Edge parity violation: outgoing edge from {edge.src_node} to {edge.dst_node} has corresponding incoming edge")
            return False
        dst_node = node_dict[edge.dst_node]
        if edge not in dst_node.paths_in:
            print(f"Edge parity violation: {edge.dst_node} does not recognize incoming edge from {edge.src_node}")
            return False

    status[node_id] = VISITED
    return True

# Main validation function to check graph configuration
def validate(graph: Graph, config: GraphRunConfig):
    status = {node.node_id: UNVISITED for node in graph.nodes}
    node_dict = {node.node_id: node for node in graph.nodes}    # Quick access to nodes by ID
    visited_edges = set()   # Track visited edges for parity check
    root_map = {node.node_id: node for node in graph.nodes if node.node_id in config.root_inputs.keys()}

    # Start validation from each root node
    for root_id in root_map:
        if status[root_id] == UNVISITED:
            if not validate_helper(root_id, status, node_dict, visited_edges, root_map):
                return False
    
    # if len(getIslands(graph)) != 0:
    #     return False

    return True

# Function to get islands
def run_graph_for_islands(graph: Graph):
    islands = getIslands(graph)
    return islands

# Function to get graph run outputs
def run_graph(graph: Graph, config: GraphRunConfig):
    # Modifying data_in of nodes based on root_inputs and data_overwrites
    db = Session()
    root_nodes = []
    for node in graph.nodes:
        if node.node_id in config.root_inputs.keys():
            node.data_in = config.root_inputs[node.node_id]
            node.on_update_data_in()
            graph.update_node_data(node)
            root_nodes.append(node)
            update_node_mapping(node.node_id, node.data_in, node.data_out, db)
        if node.data_in is None:
            node.data_in = {}
        if node.node_id in config.data_overwrites.keys():
            node.data_in.update(config.data_overwrites[node.node_id])
            node.on_update_data_in()
            graph.update_node_data(node)
            update_node_mapping(node.node_id, node.data_in, node.data_out, db)
    # Data transfer between nodes
    node_map = {node.node_id: node for node in graph.nodes}
    queue = deque()
    level_transfer_checker = {}
    
    for node in root_nodes:
        queue.append([node, 0])
        level_transfer_checker[node.node_id] = [0, node.node_id]
    
    while len(queue) != 0:
        node = queue.popleft()
        for edge in node[0].paths_out:
            dst_node = node_map[edge.dst_node]
            if dst_node.node_id not in level_transfer_checker.keys():
                for src_key, dst_key in edge.src_to_dst_data_keys.items():
                    dst_node.data_in[dst_key] = node[0].data_out[src_key]
                level_transfer_checker[dst_node.node_id] = [node[1]+1, node[0].node_id]
            elif level_transfer_checker[dst_node.node_id][0]-1 > node[1]:
                for src_key, dst_key in edge.src_to_dst_data_keys.items():
                    dst_node.data_in[dst_key] = node[0].data_out[src_key]
                level_transfer_checker[dst_node.node_id] = [node[1]+1, node[0].node_id]
            elif level_transfer_checker[dst_node.node_id][0] == node[1]:
                if level_transfer_checker[dst_node.node_id][1] > node[0].node_id:
                    for src_key, dst_key in edge.src_to_dst_data_keys.items():
                        dst_node.data_in[dst_key] = node[0].data_out[src_key]
                    level_transfer_checker[dst_node.node_id][1] = node[0].node_id
            dst_node.on_update_data_in()
            graph.update_node_data(dst_node)
            update_node_mapping(dst_node.node_id, dst_node.data_in, dst_node.data_out, db)
            queue.append([dst_node, node[1]+1])        

    topological_order = toposort(graph)
    level_order2 = level_wise_order(graph, config)
    leafs = leaf_nodes(graph, root_nodes)
    # Creating unique run ID for the runConfig
    run_id = str(uuid.uuid4())
    
    return {"run_id": run_id, "graph": graph, "topo": {node.node_id: node.data_out for node in topological_order}, "lvlOrder": level_order2, "leafNodes": {node.node_id: node.data_out for node in leafs}}

# Function to get topological order of nodes in graph as per config provided
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

# Function to get level_order traversal of graph
def level_wise_order(graph: Graph, config: GraphRunConfig) -> List[List[str]]:
    level_order = []
    node_map = {node.node_id: node for node in graph.nodes}
    in_degree = {node.node_id: 0 for node in graph.nodes}
    for node in graph.nodes:
        for edge in node.paths_in:
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
                in_degree[edge.dst_node] -= 1
                if in_degree[edge.dst_node] == 0:
                    queue.append(edge.dst_node)
        level_order.append(current_level)

    return level_order

# Function to get disconnected components in graph as per runConfig
def getIslands(graph: Graph) -> List[List[str]]:
    node_map = {node.node_id: node for node in graph.nodes}
    def dfs(node_id, visited, components):
        visited.add(node_id)
        components.append(node_id)
        for edge in node_map[node_id].paths_out:
            if edge.dst_node not in visited:
                dfs(edge.dst_node, visited, components)
        for edge in node_map[node_id].paths_in:
            if edge.src_node not in visited:
                dfs(edge.src_node, visited, components)
    visited = set()
    islands = []
    for node_id, _ in node_map.items():
        if node_id not in visited:
            component = []
            dfs(node_id, visited, component)
            islands.append(component)    
    return islands

# Function to get leaf nodes for the graphRun configs
def leaf_nodes(graph: Graph, root_nodes: List) -> List[Node]:
    node_map = {node.node_id: node for node in graph.nodes}
    queue = deque()
    leaf_list = []
    visited = defaultdict(bool)    
    for node in root_nodes:
        queue.append(node)
        visited[node.node_id] = True
    while len(queue) != 0:
        node = queue.popleft()
        if len(node.paths_out) == 0:
            leaf_list.append(node)
        else:
            for edge in node.paths_out:
                if visited[edge.dst_node] == False:
                    queue.append(node_map[edge.dst_node])
    return leaf_list

