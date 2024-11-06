# Graph Processing API

This project provides a RESTful API built with FastAPI and SQLAlchemy to manage and analyze graphs stored in a MySQL database. The API supports CRUD operations for nodes and edges, graph validation, and retrieval of graph-related results, including topological order, level order traversal, and isolated components (islands).

## Technologies Used

- **Database**: MySQL
- **Language**: Python
- **Libraries**:
  - **FastAPI**: for building the API
  - **SQLAlchemy**: for ORM and database interactions
  - **Collections and other standard Python libraries**

## API Endpoints

### Graph Endpoints

1. **Fetch Graph**: Retrieve the entire graph based on a `GraphRunConfig`.
   - **Endpoint**: `GET /fetch_graph`
   - **Parameters**: `config` (a set of node IDs to include/exclude)
   - **Response**: Serialized graph data including nodes and edges.

2. **Add Node**: Add a new node to the database.
   - **Endpoint**: `POST /add_node`
   - **Body**: `NodeData` object (node attributes and mappings).
   - **Response**: Confirmation with added node data.

3. **Delete Node**: Remove a node and its associated edges from the database.
   - **Endpoint**: `POST /delete_node/{node_id}`
   - **Parameters**: `node_id`
   - **Response**: Confirmation of node and edge deletion.

4. **Update Node**: Update properties of an existing node.
   - **Endpoint**: `POST /update_node/{node_id}`
   - **Body**: Updated `NodeData`.
   - **Response**: Updated node data.

5. **Add Edge**: Add a new edge between nodes.
   - **Endpoint**: `POST /add_edge`
   - **Body**: `EdgeData` object (source and destination node IDs).
   - **Response**: Confirmation with added edge data.

6. **Delete Edge**: Remove an edge based on its ID.
   - **Endpoint**: `POST /delete_edge`
   - **Parameters**: `edge_id`
   - **Response**: Confirmation of edge deletion.

7. **Run Configuration**: Validate and process a graph based on configuration.
   - **Endpoint**: `POST /run_config`
   - **Body**: `GraphRunConfig`
   - **Response**: Processed results including topological sort, level order traversal, and leaves.

8. **Fetch Islands**: Retrieve disconnected components (islands) in the graph.
   - **Endpoint**: `GET /fetch_islands`
   - **Response**: List of isolated nodes/groups.

9. **Get Graph Outputs**: Retrieve graph output for a specific run.
   - **Endpoint**: `GET /get_graph`
   - **Parameters**: `run_id`
   - **Response**: Serialized graph results (topological order, level order, leaf nodes).

10. **Node Output Value**: Get the output value of a node based on a specific run.
    - **Endpoint**: `GET /node_value`
    - **Parameters**: `node_id`, `run_id`
    - **Response**: Node output data if available for the specified run.

## Database Structure

### Graph Table
- **Purpose**: Stores run results for different graph configurations.
- **Fields**:
  - `id`: Primary key
  - `nodes`: JSON representation of nodes involved in the graph
  - `run_id`: Unique run ID (foreign key referencing `graph_run_configs`)
  - `toposort`: Topological sorting results
  - `level_order_traversal`: Level order traversal results
  - `leaf_nodes`: List of leaf nodes

### Node Table
- **Purpose**: Stores individual node data.
- **Fields**:
  - `node_id`: Primary key
  - `data_in`, `data_out`, `mapping`: JSON data related to node properties
  - `paths_in`, `paths_out`: JSON lists of connected edge IDs
  - **Listener for Node Deletions**:
     - When a node is deleted, this listener removes any edges associated with the node from the `paths_in` and `paths_out` of other nodes. It ensures that the corresponding edge records are deleted from the database to maintain integrity.


### Edge Table
- **Purpose**: Stores edges between nodes.
- **Fields**:
  - `id`: Primary key
  - `src_node_id`: Source node (foreign key)
  - `dst_node_id`: Destination node (foreign key)
  - `src_to_dst_data_keys`: JSON of data keys transferred between nodes
  - **Listeners for Edge Insertions and Deletions**:
     - **After Insert**: Automatically updates the `paths_in` and `paths_out` in the corresponding nodes when a new edge is inserted.
     - **After Delete**: When an edge is deleted, it updates the `paths_in` and `paths_out` arrays for the affected nodes and also removes the corresponding edge from the nodes' path arrays.

### GraphRunConfig Table
   - **Purpose**: This table is used to store the configurations related to each graph run. Each entry represents a unique run configuration, identified by a `run_id`, which is the primary key. The `config_data` column stores the configuration details as a JSON object, allowing flexibility to store dynamic configuration parameters for each run.

   - **Columns**:
     - `run_id`: A unique identifier for each graph run configuration (Primary Key).
     - `config_data`: A JSON column that stores the configuration data related to the graph run. This can include settings such as input values, parameters, and other configurations required for processing the graph.

   - **Example Query**:  
     To retrieve a specific configuration by its `run_id`:
     ```sql
     SELECT * FROM graph_run_configs WHERE run_id = 'some_unique_run_id';
     ```

### RunNodes Table
   - **Purpose**: This table optimizes the search and retrieval of node outputs associated with specific graph runs. The `RunNodes` table links the `node_ids` with the corresponding `run_id`. It allows for efficient querying of nodes based on the graph run they belong to.

   - **Fields**:
     - `id`: The primary key, an auto-incrementing integer that uniquely identifies each row in the `RunNodes` table.
     - `node_ids`: A string column storing the node identifiers associated with the graph run.
     - `run_id`: A JSON column that stores the `run_id` associated with the nodes in this table. This column allows the nodes to be tied to the specific run configuration.

   - **Example Query**:  
     To fetch nodes for a specific `run_id`:
     ```sql
     SELECT * FROM graph_nodes WHERE run_id = 'some_unique_run_id';
     ```

## Data Classes
In addition to the database tables, the following data classes are used to represent the structure of nodes, edges, and graph configurations in memory. These classes are essential for serializing and deserializing data for efficient storage and retrieval.

### Edge Class
   This class represents an edge in the graph. An edge connects two nodes, and it stores the mappings of data from the source node to the destination node. The `src_node` and `dst_node` attributes refer to the IDs of the source and destination nodes, respectively. The `src_to_dst_data_keys` dictionary maps the outgoing data from the source node to the incoming data of the destination node.

   - **Attributes**:
     - `src_node`: The ID of the source node.
     - `dst_node`: The ID of the destination node.
     - `src_to_dst_data_keys`: A dictionary mapping the outgoing data keys from the source node to the incoming data keys of the destination node.

   - **Methods**:
     - `serialize`: Converts the edge to a dictionary for storage or transmission.
     - `deserialize`: Converts a dictionary back into an `Edge` object.

### Node Class
   A node represents a processing unit in the graph. It holds information about its incoming and outgoing data (`data_in` and `data_out`), mappings between incoming and outgoing data, and the paths that lead into and out of the node (represented as a list of `Edge` objects).

   - **Attributes**:
     - `node_id`: The unique identifier for the node.
     - `data_in`: A dictionary containing the incoming data and its data type.
     - `data_out`: A dictionary containing the outgoing data and its data type.
     - `mapping`: A dictionary mapping the incoming data keys to the corresponding outgoing data keys.
     - `paths_in`: A list of `Edge` objects representing the nodes that feed into this node.
     - `paths_out`: A list of `Edge` objects representing the nodes that this node feeds into.

   - **Methods**:
     - `serialize`: Converts the node to a dictionary.
     - `deserialize`: Converts a dictionary back into a `Node` object.
     - `on_update_data_in`: Updates the outgoing data (`data_out`) based on the current incoming data (`data_in`) using the `mapping`.

### Graph Class
   The `Graph` class represents the entire directed graph. It stores a list of nodes and provides methods for serializing the graph and updating node data.

   - **Attributes**:
     - `nodes`: A list of `Node` objects that are part of the graph.

   - **Methods**:
     - `serialize`: Converts the graph to a dictionary.
     - `deserialize`: Converts a dictionary back into a `Graph` object.
     - `update_node_data`: Updates the data for a specific node in the graph.

### GraphRunConfig Class
   The `GraphRunConfig` class stores the configuration for a specific run of the graph, including the inputs for the root nodes, data overwrites for non-root nodes, and lists of enabled and disabled nodes. This class is critical for managing the runtime configuration of the graph.

   - **Attributes**:
     - `root_inputs`: A dictionary containing the `data_in` values for the root nodes.
     - `data_overwrites`: A dictionary containing the `data_in` values for non-root nodes.
     - `enable_list`: A list of node IDs that are enabled for the current run.
     - `disable_list`: A list of node IDs that are disabled for the current run.

   - **Methods**:
     - `serialize`: Converts the configuration to a dictionary.
     - `deserialize`: Converts a dictionary back into a `GraphRunConfig` object.

These data classes serve as the backbone for handling graph data in the application, enabling serialization, deserialization, and dynamic updates of graph structures and configurations during runtime.

### Algorithms and Time Complexity

The following functions are used to validate the structure and configuration of a graph, check for cycles, handle data transfer between nodes, and determine the traversal order. Each function has its own complexity based on the nature of the operations performed, particularly with respect to the number of nodes and edges in the graph.

1. **`validate_helper` Function**  
   - **Purpose**: This helper function is used in depth-first search (DFS) traversal to check for cycles, duplicate edges, data key mismatches, and edge parity.
   - **Complexity**: \(O(E + V)\), where \(E\) is the number of edges and \(V\) is the number of nodes, as it involves visiting each node and edge once.
   - **Steps**:
     - Cycles are detected using DFS by marking nodes with `VISITING` and `VISITED` status.
     - Duplicate edges are detected using a hash map (`seen_src_keys`).
     - Type mismatches are identified by comparing data keys between connected nodes.
     - Parity checks ensure that each outgoing edge has a corresponding incoming edge.

2. **`validate` Function**  
   - **Purpose**: This is the main validation function that checks the graph configuration by initiating DFS from root nodes.
   - **Complexity**: \(O(E + V)\) due to the reliance on `validate_helper`.
   - **Steps**:
     - Initializes each node’s status and maps each node by its ID for quick access.
     - Begins DFS from each root node to validate connections, data integrity, and cycle-free configuration.

3. **`run_graph_for_islands` Function**  
   - **Purpose**: Identifies isolated subgraphs (islands) within the graph.
   - **Complexity**: \(O(E + V)\), as it uses DFS to find all connected components.
   - **Steps**:
     - Calls the `getIslands` function to detect disconnected components.

4. **`run_graph` Function**  
   - **Purpose**: Executes the graph based on configuration settings, transferring data and recording traversal results.
   - **Complexity**: Dependent on multiple factors, with an overall complexity around \(O(E + V)\) for traversal and data updates.
   - **Steps**:
     - Updates root nodes with initial data inputs.
     - Performs BFS to propagate data through the graph.
     - Generates a topological order, level order traversal, and identifies leaf nodes.

5. **`toposort` Function**  
   - **Purpose**: Produces a topological sort of the nodes in the graph, ensuring no cycles are present.
   - **Complexity**: \(O(V + E)\), as it performs DFS on each node.
   - **Steps**:
     - DFS is applied to arrange nodes in an order where each node appears before its dependent nodes.

6. **`level_wise_order` Function**  
   - **Purpose**: Provides a level-wise ordering of nodes, showing the hierarchical structure.
   - **Complexity**: \(O(V + E)\), as it uses BFS to determine levels of nodes.
   - **Steps**:
     - Calculates in-degrees and iterates through nodes level by level, reducing in-degrees to track dependencies.

7. **`getIslands` Function**  
   - **Purpose**: Finds disconnected components within the graph.
   - **Complexity**: \(O(V + E)\) due to DFS traversal.
   - **Steps**:
     - Uses DFS to explore all nodes and identify isolated subgraphs.

8. **`leaf_nodes` Function**  
   - **Purpose**: Identifies leaf nodes based on the configuration.
   - **Complexity**: \(O(V + E)\), where \(V\) represents nodes and \(E\) edges, as it processes each node and its outgoing edges.
   - **Steps**:
     - Uses BFS to detect nodes without outgoing edges, marking them as leaf nodes. 

These algorithms ensure efficient graph validation, traversal, and processing, with each function optimized to handle operations on nodes and edges based on the graph's complexity.

## Getting Started

### Requirements
- Python 3.11+
- MySQL database instance

### Setup

1. **Create a Docker Network**

   This network will allow containers to communicate with each other.

   ```bash
   docker network create my-network
   ```

2. **Build the Docker Image for the Application**

   Build the Docker image with a specified tag (e.g., `myapp:1.0.0`).

   ```bash
   docker buildx build -t myapp:1.0.0 .
   ```

3. **Run the MySQL Container**

   Start a MySQL container within the same network. Replace `{RootPassword}` with your desired root password.

   ```bash
   docker run --name mysql-container --network my-network -e MYSQL_ROOT_PASSWORD={RootPassword} -d mysql:latest
   ```

4. **Create the Application Database**

   Exec into the MySQL container to create the required database (e.g., `gb`).

   ```bash
   docker exec -it mysql-container mysql -u root -p
   ```

   Once inside the MySQL shell, run:

   ```sql
   CREATE DATABASE gb;
   ```

5. **Run the Application Container**

   Start the application container, exposing it on port `8000` and connecting it to `my-network`.

   ```bash
   docker run --name myapp-container -p 8000:8000 --network my-network myapp:1.0.0
   ```

   Make sure to setup HOST, USERNAME, PASSWORD, PORT and DATABASE in config.py as well as database_models.py files.

6. **Test API EndPoints**

   Using the hitter.py script, to test every end-point via using requests library in python. 