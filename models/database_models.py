from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from sqlalchemy import event, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from .graph import Node as NodeData, Edge as EdgeData, GraphRunConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

USER = "root"
PASSWORD = "Meticulous%4013"
DATABASE = "gb"
DATABASE_URL = f"mysql://{USER}:{PASSWORD}@localhost/{DATABASE}"

engine = create_engine(DATABASE_URL)

class Graph(Base):
    __tablename__ = "graphs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nodes = Column(MySQLJSON, nullable=True, default=[]) # List of nodes stored which are used in this graph
    run_id = Column(String(250), ForeignKey("graph_run_configs.run_id"), unique=True, nullable=False)  # Foreign key reference to Run
    toposort = Column(MySQLJSON, nullable=True, default=[])  # Store topological sorting results
    level_order_traversal = Column(MySQLJSON, nullable=True, default=[])  # Store level order traversal results
    islands = Column(MySQLJSON, nullable=True, default=[])  # Store number of islands in the graph

    # run_config = relationship("GraphRunConfig", back_populates="graph", uselist=False)
    
    def __repr__(self):
        return f"<Graph(id={self.id}, run_id={self.run_id}, number_of_islands={self.number_of_islands})>"
        
class Node(Base):
    __tablename__ = "nodes"
    node_id = Column(String(50), primary_key=True, nullable=False)
    data_in = Column(MySQLJSON, nullable=True, default={})  # Serialized incoming data
    data_out = Column(MySQLJSON, nullable=True, default={})  # Serialized outgoing data

    # New columns to store lists of edge IDs for incoming and outgoing edges
    paths_in = Column(MySQLJSON, nullable=True, default=[])
    paths_out = Column(MySQLJSON, nullable=True, default=[])

    # Define relationships for outgoing and incoming edges
    outgoing_edges = relationship("Edge", back_populates="source_node", foreign_keys="Edge.src_node_id")
    incoming_edges = relationship("Edge", back_populates="destination_node", foreign_keys="Edge.dst_node_id")
   
    def to_data(self) -> NodeData:
        """Convert ORM Node to dataclass Node."""
        paths_in_ids = [edge.id for edge in self.incoming_edges]  # Get IDs of incoming edges
        paths_out_ids = [edge.id for edge in self.outgoing_edges]  # Get IDs of outgoing edges

        return NodeData(
            node_id=self.node_id,
            data_in=self.data_in,
            data_out=self.data_out,
            paths_in=paths_in_ids,
            paths_out=paths_out_ids
        )

    def from_data(self, node_data: NodeData):
        """Populate ORM Node from dataclass Node."""
        self.node_id = node_data.node_id
        self.data_in = node_data.data_in
        self.data_out = node_data.data_out

        # Set `paths_in` and `paths_out` lists with IDs
        self.paths_in = [edge.id for edge in node_data.paths_in]
        self.paths_out = [edge.id for edge in node_data.paths_out]

class Edge(Base):
    __tablename__ = "edges"
    id = Column(Integer, primary_key=True, autoincrement=True)
    src_node_id = Column(String(50), ForeignKey("nodes.node_id"), nullable=False)
    dst_node_id = Column(String(50), ForeignKey("nodes.node_id"), nullable=False)
    src_to_dst_data_keys = Column(MySQLJSON, nullable=False, default={})

    # Relationships to nodes
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

class GraphRunConfig(Base):
    __tablename__ = "graph_run_configs"
    run_id = Column(String(250), primary_key=True)  # This is also the foreign key for the graph table
    config_data = Column(MySQLJSON, nullable=False, default={})  # Store serialized config data
    def __repr__(self):
        return f"<GraphRunConfig(run_id={self.run_id}, config_data={self.config_data})>"

# Defining listeners for automatic database updates on different CRUD api calls
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

@event.listens_for(Edge, 'after_delete')
def update_node_paths_on_delete(mapper, connection, target):
    """Automatically update paths_in and paths_out in nodes when an edge is deleted."""
    src_node_id = target.src_node_id
    dst_node_id = target.dst_node_id
    edge_id = target.id

    # Start a session
    Session = sessionmaker(bind=connection)
    session = Session()

    try:
        # Remove edge_id from paths_out for src_node_id
        index_query = select(func.JSON_SEARCH(Node.paths_out, 'one', edge_id)).where(Node.node_id == src_node_id)
        index_result = session.execute(index_query).scalar()
        print(f"Index in paths_out for {src_node_id}: {index_result}")

        if index_result is not None:
            # Use the found index to remove the edge_id safely
            connection.execute(
                update(Node)
                .where(Node.node_id == src_node_id)
                .values(paths_out=func.JSON_REMOVE(Node.paths_out, index_result))
            )
            print(f"Updated paths_out for {src_node_id}")

        # Remove edge_id from paths_in for dst_node_id
        index_query = select(func.JSON_SEARCH(Node.paths_in, 'one', edge_id)).where(Node.node_id == dst_node_id)
        index_result = session.execute(index_query).scalar()
        print(f"Index in paths_in for {dst_node_id}: {index_result}")

        if index_result is not None:
            # Use the found index to remove the edge_id safely
            connection.execute(
                update(Node)
                .where(Node.node_id == dst_node_id)
                .values(paths_in=func.JSON_REMOVE(Node.paths_in, index_result))
            )
            print(f"Updated paths_in for {dst_node_id}")

        # Cleanup: Remove any stale edge IDs that don't exist in the edges table
        existing_edges = session.execute(select(Edge.id)).scalars().all()
        print(f"Existing edges in DB: {existing_edges}")

        # Clean up paths_out for all nodes
        for node in session.query(Node).all():
            current_paths_out = node.paths_out
            # Only remove edge IDs that are not in the existing_edges
            updated_paths_out = [edge for edge in current_paths_out if edge in existing_edges]
            connection.execute(
                update(Node)
                .where(Node.node_id == node.node_id)
                .values(paths_out=updated_paths_out)
            )

        # Clean up paths_in for all nodes
        for node in session.query(Node).all():
            current_paths_in = node.paths_in
            # Only remove edge IDs that are not in the existing_edges
            updated_paths_in = [edge for edge in current_paths_in if edge in existing_edges]
            connection.execute(
                update(Node)
                .where(Node.node_id == node.node_id)
                .values(paths_in=updated_paths_in)
            )

        # Commit the session if necessary
        session.commit()

    except SQLAlchemyError as e:
        # Handle exceptions
        session.rollback()
        print(f"Error: {str(e)}")
    finally:
        session.close()

@event.listens_for(Node, 'after_delete')
def update_edge_after_delete(mapper, connection, target):
    session = Session(bind=connection)
    for edge in target.paths_in:
        session.delete(edge)
    for edge in target.paths_out:
        session.delete(edge)
    session.commit()

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()

nodes_data = [
    {"node_id": "node1", "data_in": {"input1": 0}, "data_out": {"output1": 10}},
    {"node_id": "node2", "data_in": {"input2": 0}, "data_out": {"output2": 20}},
    {"node_id": "node3", "data_in": {"input3": 0}, "data_out": {"output3": 30}},
    {"node_id": "node4", "data_in": {"input4": 0}, "data_out": {"output4": 40}},
    {"node_id": "node5", "data_in": {"input5": 0}, "data_out": {"output5": 50}},
    {"node_id": "node6", "data_in": {"input6": 0}, "data_out": {"output6": 60}},
    {"node_id": "node7", "data_in": {"input7": 0}, "data_out": {"output7": 70}},
    {"node_id": "node8", "data_in": {"input8": 0}, "data_out": {"output8": 80}},
    {"node_id": "node9", "data_in": {"input9": 0}, "data_out": {"output9": 90}},
    {"node_id": "node10", "data_in": {"input10": 0}, "data_out": {"output10": 100}},
]

edges_data = [
    {"src_node": "node1", "dst_node": "node2", "src_to_dst_data_keys": {"output1": "input2"}},
    {"src_node": "node2", "dst_node": "node3", "src_to_dst_data_keys": {"output2": "input3"}},
    {"src_node": "node3", "dst_node": "node4", "src_to_dst_data_keys": {"output3": "input4"}},
    {"src_node": "node4", "dst_node": "node5", "src_to_dst_data_keys": {"output4": "input5"}},
    {"src_node": "node5", "dst_node": "node6", "src_to_dst_data_keys": {"output5": "input6"}},
    {"src_node": "node6", "dst_node": "node7", "src_to_dst_data_keys": {"output6": "input7"}},
    {"src_node": "node7", "dst_node": "node8", "src_to_dst_data_keys": {"output7": "input8"}},
    {"src_node": "node8", "dst_node": "node9", "src_to_dst_data_keys": {"output8": "input9"}},
    {"src_node": "node9", "dst_node": "node10", "src_to_dst_data_keys": {"output9": "input10"}},
    {"src_node": "node1","dst_node": "node10", "src_to_dst_data_keys": {}}  # Example of a dependency edge without data transfer
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