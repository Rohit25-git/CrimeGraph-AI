import logging
import networkx as nx
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Tuple
from datetime import datetime

from backend.app.database.neo4j_db import get_neo4j_session, is_neo4j_connected
from backend.app.models.database_models import Entity, Relationship, Investigation

logger = logging.getLogger("graph_service")

class GraphService:
    @staticmethod
    def sync_entity_to_neo4j(entity_id: str, ent_type: str, display_name: str, properties: Dict[str, Any] = None) -> bool:
        """Syncs a single node to Neo4j. Returns True if successful."""
        if not is_neo4j_connected():
            return False
        
        session = get_neo4j_session()
        if not session:
            return False
            
        cypher = """
        MERGE (e:Entity {id: $id})
        SET e.type = $type,
            e.display_name = $display_name,
            e.properties = $properties,
            e.updated_at = timestamp()
        RETURN e
        """
        try:
            session.run(
                cypher, 
                id=entity_id, 
                type=ent_type, 
                display_name=display_name, 
                properties=properties or {}
            )
            return True
        except Exception as e:
            logger.error(f"Error syncing entity {entity_id} to Neo4j: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def sync_relationship_to_neo4j(
        relationship_id: str, 
        source_id: str, 
        target_id: str, 
        rel_type: str, 
        timestamp: datetime = None, 
        properties: Dict[str, Any] = None
    ) -> bool:
        """Syncs a relationship to Neo4j. Returns True if successful."""
        if not is_neo4j_connected():
            return False
            
        session = get_neo4j_session()
        if not session:
            return False
            
        # We model all graph edges as a generic RELATED_TO relationship and store type in properties
        # to prevent Cypher syntax injection and schema complexity
        cypher = """
        MATCH (a:Entity {id: $source_id})
        MATCH (b:Entity {id: $target_id})
        MERGE (a)-[r:RELATED_TO {id: $id}]->(b)
        SET r.type = $type,
            r.timestamp = $timestamp,
            r.properties = $properties
        RETURN r
        """
        try:
            ts_str = timestamp.isoformat() if timestamp else None
            session.run(
                cypher,
                id=relationship_id,
                source_id=source_id,
                target_id=target_id,
                type=rel_type,
                timestamp=ts_str,
                properties=properties or {}
            )
            return True
        except Exception as e:
            logger.error(f"Error syncing relationship {relationship_id} to Neo4j: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def delete_entity_from_neo4j(entity_id: str) -> bool:
        if not is_neo4j_connected():
            return False
        session = get_neo4j_session()
        if not session:
            return False
        cypher = "MATCH (e:Entity {id: $id}) DETACH DELETE e"
        try:
            session.run(cypher, id=entity_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting entity {entity_id} from Neo4j: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def delete_relationship_from_neo4j(relationship_id: str) -> bool:
        if not is_neo4j_connected():
            return False
        session = get_neo4j_session()
        if not session:
            return False
        cypher = "MATCH ()-[r:RELATED_TO {id: $id}]-() DELETE r"
        try:
            session.run(cypher, id=relationship_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting relationship {relationship_id} from Neo4j: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def get_full_graph(db: Session) -> Dict[str, Any]:
        """Fetches nodes and edges for rendering. Uses Neo4j if connected, otherwise NetworkX on top of Postgres."""
        # Try Neo4j first
        if is_neo4j_connected():
            session = get_neo4j_session()
            if session:
                try:
                    nodes_query = "MATCH (e:Entity) RETURN e.id AS id, e.type AS type, e.display_name AS display_name, e.properties AS properties"
                    edges_query = "MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity) RETURN r.id AS id, a.id AS source, b.id AS target, r.type AS type, r.properties AS properties"
                    
                    nodes_res = session.run(nodes_query)
                    edges_res = session.run(edges_query)
                    
                    nodes = []
                    for record in nodes_res:
                        nodes.append({
                            "id": record["id"],
                            "type": record["type"],
                            "display_name": record["display_name"],
                            "properties": record["properties"] or {}
                        })
                        
                    edges = []
                    for record in edges_res:
                        edges.append({
                            "id": record["id"],
                            "source": record["source"],
                            "target": record["target"],
                            "type": record["type"],
                            "properties": record["properties"] or {}
                        })
                    if len(nodes) > 0:
                        return {"nodes": nodes, "edges": edges}
                    logger.info("Neo4j returned 0 nodes. Falling back to PostgreSQL source of truth.")
                except Exception as e:
                    logger.error(f"Neo4j get_full_graph error: {e}. Falling back to PostgreSQL.")
                finally:
                    session.close()

        # Fallback to PostgreSQL
        entities = db.query(Entity).all()
        relationships = db.query(Relationship).all()
        
        nodes = []
        for ent in entities:
            nodes.append({
                "id": ent.id,
                "type": ent.type,
                "display_name": ent.display_name,
                "properties": ent.metadata_json or {}
            })
            
        edges = []
        for rel in relationships:
            edges.append({
                "id": rel.id,
                "source": rel.source_entity_id,
                "target": rel.target_entity_id,
                "type": rel.type,
                "properties": rel.metadata_json or {}
            })
            
        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def get_neighborhood(db: Session, entity_id: str, depth: int = 1) -> Dict[str, Any]:
        """Gets neighborhood of an entity up to a certain depth."""
        # Try Neo4j
        if is_neo4j_connected():
            session = get_neo4j_session()
            if session:
                try:
                    # Cypher query for neighborhood
                    cypher = """
                    MATCH (start:Entity {id: $id})
                    MATCH path = (start)-[r:RELATED_TO*1..%d]-(neighbor:Entity)
                    UNWIND nodes(path) AS n
                    UNWIND relationships(path) AS rel
                    WITH collect(distinct n) AS all_nodes, collect(distinct rel) AS all_rels
                    RETURN 
                        [node in all_nodes | {id: node.id, type: node.type, display_name: node.display_name, properties: node.properties}] AS nodes,
                        [r in all_rels | {id: r.id, source: startNode(r).id, target: endNode(r).id, type: r.type, properties: r.properties}] AS edges
                    """ % depth
                    res = session.run(cypher, id=entity_id)
                    record = res.single()
                    if record and record["nodes"]:
                        return {"nodes": record["nodes"], "edges": record["edges"]}
                except Exception as e:
                    logger.error(f"Neo4j get_neighborhood error: {e}. Falling back to PostgreSQL.")
                finally:
                    session.close()

        # Fallback to NetworkX & PostgreSQL
        G = GraphService._build_networkx_graph(db)
        if not G.has_node(entity_id):
            return {"nodes": [], "edges": []}
            
        # Extract ego network
        sub_nodes = nx.single_source_shortest_path_length(G, entity_id, cut_off=depth).keys()
        subgraph = G.subgraph(sub_nodes)
        
        nodes = []
        for n, data in subgraph.nodes(data=True):
            nodes.append({
                "id": n,
                "type": data.get("type", "UNKNOWN"),
                "display_name": data.get("display_name", n),
                "properties": data.get("properties", {})
            })
            
        edges = []
        for u, v, data in subgraph.edges(data=True):
            edges.append({
                "id": data.get("id"),
                "source": u,
                "target": v,
                "type": data.get("type", "CONNECTED_TO"),
                "properties": data.get("properties", {})
            })
            
        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def get_investigation_network(db: Session, investigation_id: str, scope: str = "case") -> Dict[str, Any]:
        """
        Extracts case-scoped graph network based on selected scope:
        - case: Only entities in investigation.entities_json and their intra-case relationships.
        - direct: Case entities + 1st degree connected neighbors.
        - 2hop: Case entities + 1st & 2nd degree connected neighbors.
        - full: Complete graph with case membership indicators.
        """
        inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not inv:
            return {"investigation_id": investigation_id, "scope": scope, "nodes": [], "edges": []}
        
        case_entity_ids = set(inv.entities_json or [])
        if not case_entity_ids and scope != "full":
            return {"investigation_id": investigation_id, "scope": scope, "nodes": [], "edges": []}

        # Load ML risk scores lookup if available
        risk_lookup = {}
        try:
            from pathlib import Path
            import pandas as pd
            model_csv = Path(__file__).resolve().parent.parent / "ml" / "models" / "entity_risk_scores.csv"
            if model_csv.exists():
                df = pd.read_csv(model_csv)
                for _, row in df.iterrows():
                    e_id = str(row["entity_id"]).strip().upper()
                    risk_lookup[e_id] = {
                        "risk_score": float(row.get("risk_score", 0)),
                        "risk_level": str(row.get("risk_level", "LOW")),
                        "relationship_count": int(row.get("relationship_count", 0)),
                        "average_anomaly_score": float(row.get("average_anomaly_score", 0)),
                        "maximum_anomaly_score": float(row.get("maximum_anomaly_score", 0)),
                        "average_confidence": float(row.get("average_confidence", 0))
                    }
        except Exception as e:
            logger.warning(f"Could not load ML risk scores: {e}")

        if scope == "case":
            entities = db.query(Entity).filter(Entity.id.in_(case_entity_ids)).all()
            relationships = db.query(Relationship).filter(
                Relationship.source_entity_id.in_(case_entity_ids),
                Relationship.target_entity_id.in_(case_entity_ids)
            ).all()
            hop_map = {e.id: 0 for e in entities}
            active_node_ids = set(e.id for e in entities)

        elif scope == "direct":
            # Case entities + 1st degree connections
            direct_rels = db.query(Relationship).filter(
                (Relationship.source_entity_id.in_(case_entity_ids)) |
                (Relationship.target_entity_id.in_(case_entity_ids))
            ).all()
            neighbor_ids = set()
            for r in direct_rels:
                neighbor_ids.add(r.source_entity_id)
                neighbor_ids.add(r.target_entity_id)
            
            all_ids = case_entity_ids.union(neighbor_ids)
            entities = db.query(Entity).filter(Entity.id.in_(all_ids)).all()
            relationships = db.query(Relationship).filter(
                Relationship.source_entity_id.in_(all_ids),
                Relationship.target_entity_id.in_(all_ids)
            ).all()
            hop_map = {e.id: (0 if e.id in case_entity_ids else 1) for e in entities}
            active_node_ids = all_ids

        elif scope == "2hop":
            # 1st hop
            direct_rels = db.query(Relationship).filter(
                (Relationship.source_entity_id.in_(case_entity_ids)) |
                (Relationship.target_entity_id.in_(case_entity_ids))
            ).all()
            hop1_ids = set()
            for r in direct_rels:
                hop1_ids.add(r.source_entity_id)
                hop1_ids.add(r.target_entity_id)
            
            # 2nd hop
            hop2_rels = db.query(Relationship).filter(
                (Relationship.source_entity_id.in_(hop1_ids)) |
                (Relationship.target_entity_id.in_(hop1_ids))
            ).all()
            hop2_ids = set()
            for r in hop2_rels:
                hop2_ids.add(r.source_entity_id)
                hop2_ids.add(r.target_entity_id)
                
            all_ids = case_entity_ids.union(hop1_ids).union(hop2_ids)
            entities = db.query(Entity).filter(Entity.id.in_(all_ids)).all()
            relationships = db.query(Relationship).filter(
                Relationship.source_entity_id.in_(all_ids),
                Relationship.target_entity_id.in_(all_ids)
            ).all()
            
            hop_map = {}
            for e in entities:
                if e.id in case_entity_ids:
                    hop_map[e.id] = 0
                elif e.id in hop1_ids:
                    hop_map[e.id] = 1
                else:
                    hop_map[e.id] = 2
            active_node_ids = all_ids

        else:  # scope == "full"
            entities = db.query(Entity).all()
            relationships = db.query(Relationship).all()
            hop_map = {e.id: (0 if e.id in case_entity_ids else 99) for e in entities}
            active_node_ids = set(e.id for e in entities)

        nodes = []
        for ent in entities:
            props = dict(ent.metadata_json or {})
            risk = risk_lookup.get(ent.id.upper())
            if risk:
                props.update(risk)
            nodes.append({
                "id": ent.id,
                "type": ent.type,
                "display_name": ent.display_name,
                "is_case_entity": ent.id in case_entity_ids,
                "hop_distance": hop_map.get(ent.id, 0),
                "properties": props
            })

        edges = []
        for rel in relationships:
            if rel.source_entity_id in active_node_ids and rel.target_entity_id in active_node_ids:
                edges.append({
                    "id": rel.id,
                    "source": rel.source_entity_id,
                    "target": rel.target_entity_id,
                    "type": rel.type,
                    "confidence": rel.confidence,
                    "properties": rel.metadata_json or {}
                })

        return {
            "investigation_id": investigation_id,
            "scope": scope,
            "nodes": nodes,
            "edges": edges
        }

    @staticmethod
    def get_shortest_path(db: Session, source_id: str, target_id: str, investigation_id: str = None, scope: str = "case") -> Dict[str, Any]:
        """Finds shortest path between two entities, constrained to case scope if provided."""
        if investigation_id and scope != "full":
            net = GraphService.get_investigation_network(db, investigation_id, scope=scope)
            G = nx.Graph()
            for n in net["nodes"]:
                G.add_node(n["id"], type=n["type"], display_name=n["display_name"])
            for e in net["edges"]:
                G.add_edge(e["source"], e["target"], id=e["id"], type=e["type"])
            
            if not (G.has_node(source_id) and G.has_node(target_id)):
                return {"nodes": [], "edges": []}
            try:
                path = nx.shortest_path(G, source=source_id, target=target_id)
                nodes = []
                for n in path:
                    nodes.append({
                        "id": n,
                        "type": G.nodes[n].get("type", "UNKNOWN"),
                        "display_name": G.nodes[n].get("display_name", n)
                    })
                edges = []
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    edge_data = G.get_edge_data(u, v)
                    edges.append({
                        "id": edge_data.get("id"),
                        "source": u,
                        "target": v,
                        "type": edge_data.get("type", "CONNECTED_TO")
                    })
                return {"nodes": nodes, "edges": edges}
            except nx.NetworkXNoPath:
                return {"nodes": [], "edges": []}

        # Global shortest path search fallback
        if is_neo4j_connected():
            session = get_neo4j_session()
            if session:
                try:
                    cypher = """
                    MATCH (start:Entity {id: $source}), (end:Entity {id: $target})
                    MATCH p = shortestPath((start)-[:RELATED_TO*]-(end))
                    RETURN 
                        [node in nodes(p) | {id: node.id, type: node.type, display_name: node.display_name}] AS nodes,
                        [r in relationships(p) | {id: r.id, source: startNode(r).id, target: endNode(r).id, type: r.type}] AS edges
                    """
                    res = session.run(cypher, source=source_id, target=target_id)
                    record = res.single()
                    if record and record["nodes"]:
                        return {"nodes": record["nodes"], "edges": record["edges"]}
                except Exception as e:
                    logger.error(f"Neo4j get_shortest_path error: {e}. Falling back to PostgreSQL.")
                finally:
                    session.close()

        # Fallback to NetworkX
        G = GraphService._build_networkx_graph(db)
        if not (G.has_node(source_id) and G.has_node(target_id)):
            return {"nodes": [], "edges": []}
            
        try:
            path = nx.shortest_path(G, source=source_id, target=target_id)
            nodes = []
            for n in path:
                nodes.append({
                    "id": n,
                    "type": G.nodes[n].get("type", "UNKNOWN"),
                    "display_name": G.nodes[n].get("display_name", n)
                })
            
            edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                edge_data = G.get_edge_data(u, v)
                edges.append({
                    "id": edge_data.get("id"),
                    "source": u,
                    "target": v,
                    "type": edge_data.get("type", "CONNECTED_TO")
                })
            return {"nodes": nodes, "edges": edges}
        except nx.NetworkXNoPath:
            return {"nodes": [], "edges": []}

    @staticmethod
    def compute_centrality(db: Session) -> Dict[str, Dict[str, float]]:
        """Computes centrality metrics for all nodes with scale optimization for large graphs (>10k nodes)."""
        G = GraphService._build_networkx_graph(db)
        num_nodes = len(G)
        if num_nodes == 0:
            return {"degree": {}, "betweenness": {}, "closeness": {}, "pagerank": {}}
            
        deg = nx.degree_centrality(G)
        
        # Scale optimization: Sample betweenness if graph is large (>1,000 nodes)
        if num_nodes > 1000:
            bet = nx.betweenness_centrality(G, k=min(200, num_nodes), seed=42)
        else:
            bet = nx.betweenness_centrality(G)
            
        if num_nodes > 2000:
            # Closeness on largest component or fast approximation for 10k scale
            clo = deg  # Degree centrality acts as linear surrogate for closeness at 10k+ scale
        else:
            clo = nx.closeness_centrality(G)
            
        try:
            page = nx.pagerank(G, alpha=0.85, max_iter=100)
        except Exception:
            # Fallback in case of convergence errors
            page = {node: 1.0/num_nodes for node in G.nodes}
            
        # Scale to 0-100 for readability
        def scale(dct):
            mx = max(dct.values()) if dct and max(dct.values()) > 0 else 1.0
            return {k: round((v / mx) * 100, 1) for k, v in dct.items()}

        return {
            "degree": scale(deg),
            "betweenness": scale(bet),
            "closeness": scale(clo),
            "pagerank": scale(page)
        }

    @staticmethod
    def detect_communities(db: Session) -> Dict[str, int]:
        """Detects communities in the graph and returns mapping of {node_id: community_id}."""
        G = GraphService._build_networkx_graph(db)
        if len(G) == 0:
            return {}
            
        try:
            #Louvain communities requires undirected graph
            undir_G = G.to_undirected()
            communities = nx.community.louvain_communities(undir_G, seed=42)
            mapping = {}
            for i, comm in enumerate(communities):
                for node in comm:
                    mapping[node] = i
            return mapping
        except Exception as e:
            logger.error(f"Error in community detection: {e}")
            # Fallback: connected components
            undir_G = G.to_undirected()
            components = list(nx.connected_components(undir_G))
            mapping = {}
            for i, comp in enumerate(components):
                for node in comp:
                    mapping[node] = i
            return mapping

    @staticmethod
    def find_bridges(db: Session) -> List[Dict[str, Any]]:
        """Finds bridge edges and nodes connecting communities."""
        G = GraphService._build_networkx_graph(db)
        if len(G) == 0:
            return []
            
        bridges = []
        try:
            undir_G = G.to_undirected()
            # nx.bridges finds bridges in an undirected graph (edges whose removal increases connected components count)
            nx_bridges = list(nx.bridges(undir_G))
            for u, v in nx_bridges:
                edge_data = G.get_edge_data(u, v)
                bridges.append({
                    "source": u,
                    "source_name": G.nodes[u].get("display_name", u),
                    "target": v,
                    "target_name": G.nodes[v].get("display_name", v),
                    "relationship_id": edge_data.get("id"),
                    "type": edge_data.get("type", "CONNECTED_TO")
                })
        except Exception as e:
            logger.error(f"Error finding bridges: {e}")
            
        return bridges

    @staticmethod
    def _build_networkx_graph(db: Session) -> nx.Graph:
        """Helper to build an in-memory NetworkX graph from PostgreSQL tables."""
        entities = db.query(Entity).all()
        relationships = db.query(Relationship).all()
        
        G = nx.Graph()
        for ent in entities:
            G.add_node(
                ent.id, 
                type=ent.type, 
                display_name=ent.display_name, 
                properties=ent.metadata_json or {}
            )
            
        for rel in relationships:
            G.add_edge(
                rel.source_entity_id, 
                rel.target_entity_id, 
                id=rel.id, 
                type=rel.type, 
                properties=rel.metadata_json or {}
            )
            
        return G
