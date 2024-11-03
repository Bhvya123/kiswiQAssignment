from pydantic import BaseModel
from typing import List, Dict, Optional, Any
class EdgeSchema(BaseModel):
    src_node: str
    dst_node: str
    src_to_dst_data_keys: Dict[str, str]

class NodeSchema(BaseModel):
    node_id: str
    data_in: Optional[Dict[str, Any]]
    data_out: Dict[str, str]
    paths_in: List[EdgeSchema]
    paths_out: List[EdgeSchema]

class GraphSchema(BaseModel):
    nodes: List[NodeSchema]
