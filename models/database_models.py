from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from sqlalchemy import event, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from .graph import Node as NodeData, Edge as EdgeData, GraphRunConfig
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker

load_dotenv() 
Base = declarative_base()

# Load MySQL credentials from environment variables
USER = "root"
PASSWORD = "Meticulous%4013"
HOST = "mysql-container"
PORT = "3306"
DATABASE = "gb"

# Update the database URL to use the HOST and PORT from Docker environment variables
DATABASE_URL = f"mysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

engine = create_engine(DATABASE_URL)

# Graph Table to store run results for provided graph configs
class Graph(Base):
    __tablename__ = "graphs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nodes = Column(MySQLJSON, nullable=True, default=[]) # List of nodes stored which are used in this graph
    run_id = Column(String(250), ForeignKey("graph_run_configs.run_id"), unique=True, nullable=False)  # Foreign key reference to Run
    toposort = Column(MySQLJSON, nullable=True, default=[])  # Store topological sorting results
    level_order_traversal = Column(MySQLJSON, nullable=True, default=[])  # Store level order traversal results
    leaf_nodes = Column(MySQLJSON, default=[]) # Store leaf_nodes for easy access
    
    def __repr__(self):
        return f"<Graph(id={self.id}, run_id={self.run_id}, number_of_islands={self.number_of_islands})>"

# Node table which will store the nodes
class Node(Base):
    __tablename__ = "nodes"
    node_id = Column(String(50), primary_key=True, nullable=False)
    data_in = Column(MySQLJSON, nullable=True, default={})  
    data_out = Column(MySQLJSON, nullable=True, default={}) 
    mapping = Column(MySQLJSON, nullable=True, default={})
    
    paths_in = Column(MySQLJSON, nullable=True, default=[])
    paths_out = Column(MySQLJSON, nullable=True, default=[])

    outgoing_edges = relationship("Edge", back_populates="source_node", foreign_keys="Edge.src_node_id")
    incoming_edges = relationship("Edge", back_populates="destination_node", foreign_keys="Edge.dst_node_id")
   
    def to_data(self) -> NodeData:
        """Convert ORM Node to dataclass Node."""
        paths_in_ids = [edge.id for edge in self.incoming_edges]  
        paths_out_ids = [edge.id for edge in self.outgoing_edges] 

        return NodeData(
            node_id=self.node_id,
            data_in=self.data_in,
            data_out=self.data_out,
            mapping=self.mapping,
            paths_in=paths_in_ids,
            paths_out=paths_out_ids
        )

    def from_data(self, node_data: NodeData):
        """Populate ORM Node from dataclass Node."""
        self.node_id = node_data.node_id
        self.data_in = node_data.data_in
        self.data_out = node_data.data_out
        self.mapping = node_data.mapping
        self.paths_in = [edge.id for edge in node_data.paths_in]
        self.paths_out = [edge.id for edge in node_data.paths_out]

# Edge table to store edges
class Edge(Base):
    __tablename__ = "edges"
    id = Column(Integer, primary_key=True, autoincrement=True)
    src_node_id = Column(String(50), ForeignKey("nodes.node_id"), nullable=False)
    dst_node_id = Column(String(50), ForeignKey("nodes.node_id"), nullable=False)
    src_to_dst_data_keys = Column(MySQLJSON, nullable=False, default={})

    source_node = relationship("Node", back_populates="outgoing_edges", foreign_keys=[src_node_id])
    destination_node = relationship("Node", back_populates="incoming_edges", foreign_keys=[dst_node_id])
    
    def to_data(self) -> EdgeData:
        """Convert ORM Edge to dataclass Edge."""
        return EdgeData(
            src_node=self.src_node_id,
            dst_node=self.dst_node_id,
            src_to_dst_data_keys=self.src_to_dst_data_keys
        )

    def from_data(self, edge_data: EdgeData):
        """Populate ORM Edge from dataclass Edge."""
        self.src_node_id = edge_data.src_node
        self.dst_node_id = edge_data.dst_node
        self.src_to_dst_data_keys = edge_data.src_to_dst_data_keys

# Config table to store configs run
class GraphRunConfig(Base):
    __tablename__ = "graph_run_configs"
    run_id = Column(String(250), primary_key=True) 
    config_data = Column(MySQLJSON, nullable=False, default={})
    def __repr__(self):
        return f"<GraphRunConfig(run_id={self.run_id}, config_data={self.config_data})>"

# Table to optimize the search for node output based on run_id
class RunNodes(Base):
    __tablename__="graph_nodes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    node_ids = Column(String(50), nullable=False)
    run_id = Column(MySQLJSON, nullable=False, default={})

# Listener for updating node paths after edge insertion in database
@event.listens_for(Edge, 'after_insert')
def update_node_paths_on_insert(mapper, connection, target):
    """Automatically update paths_in and paths_out in nodes when a new edge is inserted."""
    src_node_id = target.src_node_id
    dst_node_id = target.dst_node_id
    edge_id = target.id

    connection.execute(
        Node.__table__.update()
        .where(Node.node_id == src_node_id)
        .values(paths_out=func.JSON_ARRAY_APPEND(Node.paths_out, '$', edge_id))
    )
    connection.execute(
        Node.__table__.update()
        .where(Node.node_id == dst_node_id)
        .values(paths_in=func.JSON_ARRAY_APPEND(Node.paths_in, '$', edge_id))
    )

# Listener for updating node paths after edge deletion from database
@event.listens_for(Edge, 'after_delete')
def update_node_paths_on_delete(mapper, connection, target):
    """Automatically update paths_in and paths_out in nodes when an edge is deleted."""
    src_node_id = target.src_node_id
    dst_node_id = target.dst_node_id
    edge_id = target.id

    Session = sessionmaker(bind=connection)
    session = Session()

    try:
        index_query = select(func.JSON_SEARCH(Node.paths_out, 'one', edge_id)).where(Node.node_id == src_node_id)
        index_result = session.execute(index_query).scalar()
        print(f"Index in paths_out for {src_node_id}: {index_result}")

        if index_result is not None:
            connection.execute(
                update(Node)
                .where(Node.node_id == src_node_id)
                .values(paths_out=func.JSON_REMOVE(Node.paths_out, index_result))
            )
            print(f"Updated paths_out for {src_node_id}")
        index_query = select(func.JSON_SEARCH(Node.paths_in, 'one', edge_id)).where(Node.node_id == dst_node_id)
        index_result = session.execute(index_query).scalar()
        print(f"Index in paths_in for {dst_node_id}: {index_result}")

        if index_result is not None:
            connection.execute(
                update(Node)
                .where(Node.node_id == dst_node_id)
                .values(paths_in=func.JSON_REMOVE(Node.paths_in, index_result))
            )
            print(f"Updated paths_in for {dst_node_id}")

        existing_edges = session.execute(select(Edge.id)).scalars().all()
        print(f"Existing edges in DB: {existing_edges}")

        for node in session.query(Node).all():
            current_paths_out = node.paths_out
            updated_paths_out = [edge for edge in current_paths_out if edge in existing_edges]
            connection.execute(
                update(Node)
                .where(Node.node_id == node.node_id)
                .values(paths_out=updated_paths_out)
            )

        for node in session.query(Node).all():
            current_paths_in = node.paths_in
            updated_paths_in = [edge for edge in current_paths_in if edge in existing_edges]
            connection.execute(
                update(Node)
                .where(Node.node_id == node.node_id)
                .values(paths_in=updated_paths_in)
            )

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error: {str(e)}")
    finally:
        session.close()

# Listener for deleting corresponding edges after deletion of node 
@event.listens_for(Node, 'after_delete')
def update_edge_after_delete(mapper, connection, target):
    session = Session(bind=connection)
    # Iterate over paths_in and paths_out, fetching and deleting the actual Edge instances
    for edge_id in target.paths_in:
        edge_instance = session.query(Edge).get(edge_id)
        if edge_instance:
            session.delete(edge_instance)
    for edge_id in target.paths_out:
        edge_instance = session.query(Edge).get(edge_id)
        if edge_instance:
            session.delete(edge_instance)
    session.commit()
    session.close()
    

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()

def update_node_mapping(node_id: str, data_in, data_out, db):
    node = db.query(Node).filter(Node.node_id == node_id).first()
    node.data_in = data_in
    node.data_out = data_out
    db.commit()
    db.refresh(node)
    return

# Populating with sample data
nodes_data = [
    {"node_id": "node0", "data_in": {"input0": "0, int"}, "data_out": {"output0": "0, int"}, "mapping": {"input0": "output0"}},
    {"node_id": "node1", "data_in": {"input1": "0, int"}, "data_out": {"output1": "0, int"}, "mapping": {"input1": "output1"}},
    {"node_id": "node2", "data_in": {"input2": "0, int"}, "data_out": {"output2": "0, int"}, "mapping": {"input2": "output2"}},
    {"node_id": "node3", "data_in": {"input3": "0, int"}, "data_out": {"output3": "0, int"}, "mapping": {"input3": "output3"}},
    {"node_id": "node4", "data_in": {"input4": "0, int"}, "data_out": {"output4": "0, int"}, "mapping": {"input4": "output4"}},
    {"node_id": "node5", "data_in": {"input5": "0, int"}, "data_out": {"output5": "0, int"}, "mapping": {"input5": "output5"}},
    {"node_id": "node6", "data_in": {"input6": "0, int"}, "data_out": {"output6": "0, int"}, "mapping": {"input6": "output6"}},
    {"node_id": "node7", "data_in": {"input7": "0, int"}, "data_out": {"output7": "0, int"}, "mapping": {"input7": "output7"}},
    {"node_id": "node8", "data_in": {"input8": "0, int"}, "data_out": {"output8": "0, int"}, "mapping": {"input8": "output8"}},
    {"node_id": "node9", "data_in": {"input9": "0, int"}, "data_out": {"output9": "0, int"}, "mapping": {"input9": "output9"}},
    {"node_id": "node10", "data_in": {"input10": "0, int"}, "data_out": {"output10": "0, int"}, "mapping": {"input10": "output10"}},
    {"node_id": "node11", "data_in": {"input11": "0, int"}, "data_out": {"output11": "0, int"}, "mapping": {"input11": "output11"}},
]

edges_data = [
    # {"src_node": "node0", "dst_node": "node1", "src_to_dst_data_keys": {"output0": "input1"}},
    {"src_node": "node1", "dst_node": "node2", "src_to_dst_data_keys": {"output1": "input2"}},
    {"src_node": "node2", "dst_node": "node3", "src_to_dst_data_keys": {"output2": "input3"}},
    {"src_node": "node3", "dst_node": "node4", "src_to_dst_data_keys": {"output3": "input4"}},
    {"src_node": "node4", "dst_node": "node5", "src_to_dst_data_keys": {"output4": "input5"}},
    {"src_node": "node5", "dst_node": "node6", "src_to_dst_data_keys": {"output5": "input6"}},
    {"src_node": "node6", "dst_node": "node7", "src_to_dst_data_keys": {"output6": "input7"}},
    {"src_node": "node7", "dst_node": "node8", "src_to_dst_data_keys": {"output7": "input8"}},
    {"src_node": "node8", "dst_node": "node9", "src_to_dst_data_keys": {"output8": "input9"}},
    {"src_node": "node9", "dst_node": "node10", "src_to_dst_data_keys": {"output9": "input10"}},
    {"src_node": "node1", "dst_node": "node11", "src_to_dst_data_keys": {"output1": "input11"}},
    {"src_node": "node11", "dst_node": "node10", "src_to_dst_data_keys": {"output11": "input10"}},
    {"src_node": "node0", "dst_node": "node10", "src_to_dst_data_keys": {"output0": "input10"}},
    {"src_node": "node1", "dst_node": "node3", "src_to_dst_data_keys": {"output1": "input3"}},
    {"src_node": "node1", "dst_node": "node10", "src_to_dst_data_keys": {"output1": "input10"}},
]

for node_data in nodes_data:
    node = Node()
    node.from_data(NodeData(**node_data))
    session.add(node)

for edge_data in edges_data:
    edge = Edge()
    edge.from_data(EdgeData(**edge_data))
    session.add(edge)

session.commit()
session.close()
print("Data inserted successfully!")