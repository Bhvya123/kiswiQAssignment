from typing import Dict, List, Any
from dataclasses import dataclass, asdict, field

@dataclass
class Edge:
    src_node: str   # Node ID of the node sending the data.
    dst_node: str   # Node ID of the node receiving the data.
    src_to_dst_data_keys: Dict[str, str]    # Maps data_out keys of source node to data_in keys of destination node.

    def serialize(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Edge":
        return Edge(
            src_node=data["src_node"],
            dst_node=data["dst_node"],
            src_to_dst_data_keys=data["src_to_dst_data_keys"]
        )

@dataclass
class Node:
    node_id: str
    data_in: Dict[str, str]    # Incoming data with its datatype.
    data_out: Dict[str, str]   # Outgoing data with its datatype.
    mapping: Dict[str, str]    # Maps data_in key to data_out key values 
    paths_in: List[Edge] = field(default_factory=list)  # All the nodes which come before this node for root nodes it is None.
    paths_out: List[Edge] = field(default_factory=list) # All the nodes which come after this node.
    
    def serialize(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "data_in": self.data_in,
            "data_out": self.data_out,
            "mapping": self.mapping,
            "paths_in": [edge.serialize() for edge in self.paths_in],
            "paths_out": [edge.serialize() for edge in self.paths_out]
        }

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Node":
        return Node(
            node_id=data["node_id"],
            data_in=data["data_in"],
            data_out=data["data_out"],
            mapping=data["mapping"],
            paths_in=[Edge.deserialize(edge) for edge in data["paths_in"]],
            paths_out=[Edge.deserialize(edge) for edge in data["paths_out"]]
        )
    
    def on_update_data_in(self):
        for key1, key2 in self.mapping.items():
            self.data_out[key2] = self.data_in[key1]
    
@dataclass
class Graph:
    nodes: List[Node]  # List of nodes in the graph
    
    def serialize(self) -> Dict[str, Any]:
        return {
            "nodes": [node.serialize() for node in self.nodes]
        }

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Graph":
        return Graph(
            nodes=[Node.deserialize(node) for node in data["nodes"]]
        )
    
    def update_node_data(self, node):
        # Find node and update its data
        for nodes in self.nodes:
            if nodes.node_id == node.node_id:
                nodes.data_in = node.data_in
                nodes.data_out = node.data_out
                break

@dataclass
class GraphRunConfig:
    root_inputs: Dict[str, Dict[str, str]]  # Get data_in values for root nodes 
    data_overwrites: Dict[str, Dict[str, str]]  # Get data_in values for different non-root nodes
    enable_list: List[str]  # List of enabled nodes
    disable_list: List[str] # List of disabled nodes
    
    def serialize(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "GraphRunConfig":
        return GraphRunConfig(
            root_inputs=data["root_inputs"],
            data_overwrites=data["data_overwrites"],
            enable_list=data["enable_list"],
            disable_list=data["disable_list"]
        )