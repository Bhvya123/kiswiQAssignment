from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy import update
from congifuration.config import SessionLocal
from models.database_models import Graph, Node, Edge, GraphRunConfig as GraphConfig, RunNodes
from models.graph import Graph as GraphData, Node as NodeData, Edge as EdgeData, GraphRunConfig
from services.graph_services import validate, run_graph, run_graph_for_islands

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API to fetch the whole graph for further processing as per the GraphRunConfig provided
@app.get("/fetch_graph")
async def fetch_graph(config: GraphRunConfig, db: Session = Depends(get_db)):
    # Fetch all nodes if neither enable_list nor disable_list is provided
    if config.enable_list:
        nodes_to_include = db.query(Node).filter(Node.node_id.in_(config.enable_list)).all()
    elif config.disable_list:
        nodes_to_include = db.query(Node).filter(~Node.node_id.in_(config.disable_list)).all()
    else:
        nodes_to_include = db.query(Node).all()
    graphData = GraphData(nodes=[])
    node_map = {}
    for node in nodes_to_include:
        nodeData = NodeData(
            node_id=node.node_id,
            data_in=node.data_in,
            data_out=node.data_out,
            mapping=node.mapping,
            paths_in=[],
            paths_out=[]
        )   
        node_map[nodeData.node_id] = nodeData
    for node in nodes_to_include:
        nodeData = NodeData(
            node_id=node.node_id,
            data_in=node.data_in,
            data_out=node.data_out,
            mapping=node.mapping,
            paths_in=[],
            paths_out=[]
        )
        paths_in = db.query(Edge).filter(Edge.id.in_(node.paths_in)).all()
        nodeData.paths_in = [
            EdgeData(
                src_node=edge.src_node_id,
                dst_node=edge.dst_node_id,
                src_to_dst_data_keys=edge.src_to_dst_data_keys
            ) for edge in paths_in if edge.src_node_id in node_map.keys()
        ]
        paths_out = db.query(Edge).filter(Edge.id.in_(node.paths_out)).all()
        nodeData.paths_out = [
            EdgeData(
                src_node=edge.src_node_id,
                dst_node=edge.dst_node_id,
                src_to_dst_data_keys=edge.src_to_dst_data_keys
            ) for edge in paths_out if edge.dst_node_id in node_map.keys()
        ]            
        graphData.nodes.append(nodeData)    
    return graphData

# API endpoint to add new node to the database
@app.post("/add_node")
def add_node(node_data: NodeData, db: Session = Depends(get_db)):
    node = Node(
        node_id=node_data.node_id,
        data_in=node_data.data_in,
        data_out=node_data.data_out,
        mapping=node_data.mapping    
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node.to_data()

# API endpoint to delete a node from the database
@app.post("/delete_node/{node_id}")
def delete_node(node_id: str, db: Session = Depends(get_db)):
    # Retrieve the node
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Find and delete all edges connected to this node
    edges = db.query(Edge).filter(or_(Edge.src_node_id == node_id, Edge.dst_node_id == node_id)).all()
    for edge in edges:
        db.delete(edge)
    
    # Delete the node itself
    db.delete(node)

    # Commit the transaction
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()  # Rollback the transaction if there's an error
        raise HTTPException(status_code=500, detail="Database integrity error") from e

    return {"detail": f"Node {node_id} and associated edges have been successfully deleted."}

# API endpoint to update a nodes values
@app.post("/update_node/{node_id}")
def update_node(node_id: str, node_data: NodeData, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node_data.data_in:
        node.data_in = node_data.data_in
    if node_data.data_out:
        node.data_out = node_data.data_out
    if node_data.mapping:
        node.mapping = node_data.mapping
    db.commit()
    db.refresh(node)
    return node.to_data()

# API endpoint to add a new edge in database
@app.post("/add_edge")
def create_edge(edge_data: EdgeData, db: Session = Depends(get_db)):
    nodes_in_db = db.query(Node).all()
    if not any(edge_data.src_node == node.node_id for node in nodes_in_db):
        return "No such source node exists in nodes table"
    if not any(edge_data.dst_node == node.node_id for node in nodes_in_db):
        return "No such destination node exists in nodes table"
    edge = Edge(
        src_node_id=edge_data.src_node,
        dst_node_id=edge_data.dst_node,
        src_to_dst_data_keys=edge_data.src_to_dst_data_keys
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge.to_data()

# API endpoint to delete edge from database
@app.post("/delete_edge")
def delete_edge(edge_id: str, db: Session = Depends(get_db)):
    edge = db.query(Edge).filter(Edge.id == edge_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    db.delete(edge)
    db.commit()
    return {"Deleted": edge}

# API endpoint to post run outputs on valid graph
@app.post("/run_config")
async def run_config(config: GraphRunConfig, db: Session = Depends(get_db)):
    graph = await fetch_graph(config, db)
    
    if not validate(graph, config):
        return {"Error": "not a valid graph"}
    
    results = run_graph(graph, config)
    if results == None:
        return {"error": "Graph Validation Failed"} 
    
    if len(graph.nodes) == 0:
        return {"error": "Graph validation failed cuz islands"}         
    run_id = results["run_id"]
    graph_updated = results["graph"]
    topological_order = results["topo"]
    level_order = results["lvlOrder"]
    leaves = results["leafNodes"]
    serialized_config = config.serialize()
    new_run_config = GraphConfig(run_id=run_id, config_data=serialized_config)
    db.add(new_run_config)
    db.commit()
    print(f"Successfully added GraphRunConfig: {new_run_config}")
    graph_entry = Graph(
        run_id=run_id,
        nodes=graph_updated.serialize(),
        toposort=topological_order,
        level_order_traversal=level_order,
        leaf_nodes=leaves
    )
    db.add(graph_entry)
    db.commit()
    db.refresh(graph_entry)
    
    for node in graph.nodes:
        existing_node = db.query(RunNodes).filter(RunNodes.node_ids == node.node_id).first()
        if existing_node:
            exisiting_run_data = existing_node.run_id or {}
            exisiting_run_data[run_id] = node.data_out
            db.execute(
                update(RunNodes)
                .where(RunNodes.node_ids == node.node_id)
                .values(run_id=exisiting_run_data)
            )
        else:
            new_node = RunNodes(node_ids=node.node_id, run_id={run_id: node.data_out})
            db.add(new_node)
    
    db.commit()
    # Returning the new graph entry details
    return {
        "run_id": graph_entry.run_id,
        "nodes": graph_entry.nodes,
        "toposort": graph_entry.toposort,
        "level_order_traversal": graph_entry.level_order_traversal,
        "leaf_nodes": graph_entry.leaf_nodes
    }

# API endpoint to get disconnected components(islands)
@app.get("/fetch_islands")
async def fetch_islands(config: GraphRunConfig, db: Session = Depends(get_db)):
    graph = await fetch_graph(config, db)
    islands = run_graph_for_islands(graph)    
    return {"islands": islands}

# API to get the graph outputs for valid graph after run
@app.get("/get_graph")
def get_graph(run_id: str, db: Session = Depends(get_db)):
    graph = db.query(Graph).filter(Graph.run_id == run_id).first()
    
    if graph == None:
        return {"Error": "No such run_id exists"}
    
    return {
        "run_id": run_id,
        "topological order": graph.toposort,
        "level_order": graph.level_order_traversal,
        "leaf_nodes": graph.leaf_nodes
    }

# API endpoint to get a nodes output value based on the run_id
@app.get("/node_value")
def get_node(node_id: str, run_id: str, db: Session = Depends(get_db)):
    node_runs = db.query(RunNodes).filter(RunNodes.node_ids == node_id).first()
    if not node_runs:
        return {"status": "no such node exists in the graph run"}
    if run_id in node_runs.run_id:
        return {"status": "success", "node_id": node_id, "run_id": run_id, "node output": node_runs.run_id[run_id]}
    else:
        return {"status": "error", "message": f"Run ID '{run_id}' not found for node '{node_id}'"}