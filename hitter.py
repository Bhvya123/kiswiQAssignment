import requests
from backend.models.graph import Graph as GraphData, Node as NodeData, Edge as EdgeData, GraphRunConfig

# Define the base URL for the API
base_url = "http://127.0.0.1:8000"

# Test fetching a graph
def test_fetch_graph():
    url = f"{base_url}/fetch_graph"
    graph_config = GraphRunConfig(
        root_inputs={"node1": {"input1": "10, int"}, "node0": {"input0": "5, int"}},
        data_overwrites={},
        enable_list=["node1", "node0", "node10"],
        disable_list=[]
    )
    response = requests.get(url, json=graph_config.serialize())
    if response.status_code == 200:
        graph_data = GraphData(nodes=response.json())
        print("Graph fetched successfully:", graph_data)
    else:
        print(f"Error fetching graph: {response.status_code}, {response.json()}")

# Test creating a graph run config
def test_create_graph_run_config():
    url = f"{base_url}/run_config"
    graph_config = GraphRunConfig(
        root_inputs={"node1": {"input1": "10, int"}, "node0": {"input0": "5, int"}},
        data_overwrites={},
        enable_list=["node1", "node0", "node10"],
        disable_list=[]
    )
    response = requests.post(url, json=graph_config.serialize())
    if response.status_code == 200:
        print("Graph run config created successfully:", response.json())
    else:
        print(f"Error creating graph run config: {response.status_code}, {response.json()}")

# Test fetching a node value
def test_fetch_node_value():
    url = f"{base_url}/node_value?node_id=node2&run_id=c6b9a407-d0d8-4844-8a3e-a20a6994bc8a"
    response = requests.get(url)
    if response.status_code == 200:
        print("Node value fetched successfully:", response.json())
    else:
        print(f"Error fetching node value: {response.status_code}, {response.json()}")

# Test fetching a graph by run id
def test_fetch_graph_by_run_id():
    url = f"{base_url}/get_graph?run_id=c6b9a407-d0d8-4844-8a3e-a20a6994bc8a"
    response = requests.get(url)
    if response.status_code == 200:
        print("Graph fetched by run id:", response.json())
    else:
        print(f"Error fetching graph by run id: {response.status_code}, {response.json()}")

# Test adding a node
def test_add_node():
    url = f"{base_url}/add_node"
    node_data = NodeData(
        node_id="node12",
        data_in={"input12": "10, int"},
        data_out={"output12": "20, int"},
        mapping={"input12": "output12"}
    )
    response = requests.post(url, json=node_data.serialize())
    if response.status_code == 200:
        print("Node added successfully:", response.json())
    else:
        print(f"Error adding node: {response.status_code}, {response.json()}")

# Test deleting an edge
def test_delete_edge():
    url = f"{base_url}/delete_edge?edge_id=1"
    response = requests.post(url)
    if response.status_code == 200:
        print("Edge deleted successfully:", response.json())
    else:
        print(f"Error deleting edge: {response.status_code}, {response.json()}")

# Test adding an edge
def test_add_edge():
    url = f"{base_url}/add_edge/"
    edge_data = EdgeData(
        src_node="node11",
        dst_node="node12",
        src_to_dst_data_keys={"output11": "input12"}
    )
    response = requests.post(url, json=edge_data.serialize())
    if response.status_code == 200:
        print("Edge added successfully:", response.json())
    else:
        print(f"Error adding edge: {response.status_code}, {response.json()}")

# Test updating a node
def test_update_node():
    url = f"{base_url}/update_node/node1"
    node_data = NodeData(
        node_id="node1",
        data_in={"data0": "5"},
        data_out={},
        mapping={},
        paths_in=[],
        paths_out=[]
    )
    response = requests.post(url, json=node_data.serialize())
    if response.status_code == 200:
        print("Node updated successfully:", response.json())
    else:
        print(f"Error updating node: {response.status_code}, {response.json()}")

# Test deleting a node
def test_delete_node():
    url = f"{base_url}/delete_node/node1"
    response = requests.post(url)
    if response.status_code == 200:
        print("Node deleted successfully:", response.json())
    else:
        print(f"Error deleting node: {response.status_code}, {response.json()}")

# Test fetching islands
def test_fetch_islands():
    url = f"{base_url}/fetch_islands"
    graph_config = GraphRunConfig(
        root_inputs={"node1": {"input1": "10, int"}},
        data_overwrites={},
        enable_list=["node1", "node2", "node3", "node10", "node11", "node5", "node0"],
        disable_list=[]
    )
    response = requests.get(url, json=graph_config.serialize())
    if response.status_code == 200:
        print("Islands fetched successfully:", response.json())
    else:
        print(f"Error fetching islands: {response.status_code}, {response.json()}")

if __name__ == "__main__":
    # Call each test function
    test_fetch_graph()
    test_create_graph_run_config()
    test_fetch_node_value()
    test_fetch_graph_by_run_id()
    test_add_node()
    test_delete_edge()
    test_add_edge()
    test_update_node()
    test_delete_node()
    test_fetch_islands()

