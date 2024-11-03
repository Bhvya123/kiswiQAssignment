import requests
from models.graph import Graph as GraphData, Node as NodeData, Edge as EdgeData, GraphRunConfig
####################################################
# # graph_id = 1 
# response = requests.get(f"http://127.0.0.1:8000/fetch_graph")

# if response.status_code == 200:
#     graph_data = GraphData(nodes=response.json())
#     print(graph_data)
# else:
#     print(f"Error: {response.status_code}, {response.json()}")
####################################################

####################################################
url = "http://127.0.0.1:8000/run_config"

graphConfig = GraphRunConfig(
    root_inputs={"node1": {"input1": "10"}},
    data_overwrites={},
    enable_list=[],
    disable_list=[]
)

response = requests.post(url, json=graphConfig.serialize())
if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {response.status_code}, {response.json()}")
####################################################

####################################################

# url = "http://127.0.0.1:8000/add_node"
# data = {
#     "node_id": "node5",
#     "data_in": {"sender": "10"},
#     "data_out": {"data_n": "20"}
# }

# response = requests.post(url, json=data)

# if response.status_code == 200:
#     print("Node created successfully:", response.json())
# else:
#     print("Error:", response.status_code, response.json())
####################################################

####################################################
# url = "http://127.0.0.1:8000/delete_edge/1"
# response = requests.post(url)

# if response.status_code == 200:
#     print("Node created successfully:", response.json())
# else:
#     print("Error:", response.status_code, response.json())    
####################################################

####################################################
# url = "http://127.0.0.1:8000/add_edge/"
# edgeData = EdgeData(
#     src_node="node2",
#     dst_node="node3",
#     src_to_dst_data_keys={"data2":"data3"}
# )

# response = requests.post(url, json=edgeData.serialize())
# if response.status_code == 200:
#     print("Node created successfully:", response.json())
# else:
#     print("Error:", response.status_code, response.json()) 
####################################################

####################################################
# url = "http://127.0.0.1:8000/update_node/node1"

# nodeData = NodeData(
#     node_id="node1",
#     data_in={"data0": "5"},
#     data_out={},
#     paths_in=[],
#     paths_out=[]
# )

# response = requests.post(url, json=nodeData.serialize())
# if response.status_code == 200:
#     print("Node created successfully:", response.json())
# else:
#     print("Error:", response.status_code, response.json()) 
####################################################

####################################################
# url = "http://127.0.0.1:8000/delete_node/node1"

# response = requests.post(url)
# if response.status_code == 200:
#     print("Node created successfully:", response.json())
# else:
#     print("Error:", response.status_code, response.json()) 
####################################################

####################################################
# url = "http://127.0.0.1:8000/update_edge/1"
# edgeData = EdgeData(
#     src_node="node2",
#     dst_node="node3",
#     src_to_dst_data_keys={"data2":"data3"}
# )

# response = requests.post(url, json=edgeData.serialize())
# if response.status_code == 200:
#     print("Node created successfully:", response.json())
# else:
#     print("Error:", response.status_code, response.json()) 
