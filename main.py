from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from congifuration.config import SessionLocal
from models.database_models import Graph, Node, Edge, GraphRunConfig as GraphConfig
from models.graph import Graph as GraphData, Node as NodeData, Edge as EdgeData, GraphRunConfig
from typing import List
from schema import GraphSchema
from services.graph_services import validate, run_graph
import json

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@app.get("/")
async def responser() -> str:
    print("Api hit done!!")
    return "Api is working!!"

# API to fetch the whole graph for further processing as per the GraphRunConfig provided
@app.get("/fetch_graph")
async def fetch_graph(db: Session = Depends(get_db)):
    all_nodes = db.query(Node).all()
    graphData = GraphData(nodes = [])
    for node in all_nodes:
        nodeData = NodeData(node_id = node.node_id,
                            data_in = node.data_in,
                            data_out = node.data_out,
                            paths_in = [],
                            paths_out = [])
        edge_ids_in = node.paths_in
        edge_ids_out = node.paths_out
        for i in edge_ids_in:
            query = select(Edge).where(Edge.id == i)
            edge_to_append = db.execute(query).fetchall()[0]
            newEdge = EdgeData(src_node = edge_to_append[0].src_node_id, 
                           dst_node = edge_to_append[0].dst_node_id,
                           src_to_dst_data_keys = edge_to_append[0].src_to_dst_data_keys)
            nodeData.paths_in.append(newEdge)
        for i in edge_ids_out:
            query = select(Edge).where(Edge.id == i)
            edge_to_append = db.execute(query).fetchall()[0]
            newEdge = EdgeData(src_node = edge_to_append[0].src_node_id, 
                           dst_node = edge_to_append[0].dst_node_id,
                           src_to_dst_data_keys = edge_to_append[0].src_to_dst_data_keys)
            nodeData.paths_out.append(newEdge)
        graphData.nodes.append(nodeData)    
    return graphData

@app.post("/add_node")
def add_node(node_data: NodeData, db: Session = Depends(get_db)):
    node = Node(
        node_id=node_data.node_id,
        data_in=node_data.data_in,
        data_out=node_data.data_out   
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node.to_data()

@app.post("/delete_node/{node_id}")
def delete_node(node_id: str, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()

@app.post("/update_node/{node_id}")
def update_node(node_id: str, node_data: NodeData, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node_data.data_in:
        node.data_in = node_data.data_in
    if node_data.data_out:
        node.data_out = node_data.data_out
    db.commit()
    db.refresh(node)
    return node.to_data()

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

@app.post("/update_edge/{edge_id}")
def update_edge(edge_id: int, edge_data: EdgeData, db: Session = Depends(get_db)):
    edge = db.query(Edge).filter(Edge.id == edge_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Node not found")
    if edge_data.src_to_dst_data_keys:
        edge.src_to_dst_data_keys = edge_data.src_to_dst_data_keys
    db.commit()
    db.refresh(edge)
    
    return edge.to_data()

@app.post("/delete_edge/{edge_id}")
def delete_edge(edge_id: int, db: Session = Depends(get_db)):
    edge = db.query(Edge).filter(Edge.id == edge_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    db.delete(edge)
    db.commit()

@app.post("/run_config")
async def run_config(config: GraphRunConfig, db: Session = Depends(get_db)):
    graph = await fetch_graph(db)
    if validate(graph):
        run_id, graph_updated, topological_order, level_order, islands = run_graph(graph, config)
        # topological_order = [node.serialize for node in topological_order]
        print(graph_updated)
        print(level_order)
        print(topological_order)
        print(islands)
        
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
            islands=islands
        )
        
        db.add(graph_entry)
        db.commit()
        db.refresh(graph_entry)

        # Return the new graph entry details
        return {
            "run_id": graph_entry.run_id,
            "nodes": graph_entry.nodes,
            "toposort": graph_entry.toposort,
            "level_order_traversal": graph_entry.level_order_traversal,
            "islands": graph_entry.islands
        }
    else:
        return {"error": "Graph validation failed"}        
