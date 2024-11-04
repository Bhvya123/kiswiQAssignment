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
    paths_in: List[Edge] = field(default_factory=list)  # All the nodes which come before this node for root nodes it is None.
    paths_out: List[Edge] = field(default_factory=list) # All the nodes which come after this node.
    
    def serialize(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "data_in": self.data_in,
            "data_out": self.data_out,
            "paths_in": [edge.serialize() for edge in self.paths_in],
            "paths_out": [edge.serialize() for edge in self.paths_out]
        }

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Node":
        return Node(
            node_id=data["node_id"],
            data_in=data["data_in"],
            data_out=data["data_out"],
            paths_in=[Edge.deserialize(edge) for edge in data["paths_in"]],
            paths_out=[Edge.deserialize(edge) for edge in data["paths_out"]]
        )
    
@dataclass
class Graph:
    nodes: List[Node] 
    
    def serialize(self) -> Dict[str, Any]:
        return {
            "nodes": [node.serialize() for node in self.nodes]
        }

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> "Graph":
        return Graph(
            nodes=[Node.deserialize(node) for node in data["nodes"]]
        )

@dataclass
class GraphRunConfig:
    root_inputs: Dict[str, Dict[str, str]]
    data_overwrites: Dict[str, Dict[str, str]]
    enable_list: List[str]
    disable_list: List[str]    
    
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