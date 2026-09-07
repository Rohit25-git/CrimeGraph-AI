from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User
from backend.app.services.graph_service import GraphService

router = APIRouter(prefix="/api/analytics", tags=["Graph Analytics"])

read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])

@router.get("/centrality")
def get_network_influence(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    centralities = GraphService.compute_centrality(db)
    # Reformat for convenient display: list of dicts sorted by PageRank
    pagerank = centralities.get("pagerank", {})
    betweenness = centralities.get("betweenness", {})
    degree = centralities.get("degree", {})
    closeness = centralities.get("closeness", {})
    
    results = []
    for node_id, pr_score in pagerank.items():
        # Get entity display name
        from backend.app.models.database_models import Entity
        ent = db.query(Entity).filter(Entity.id == node_id).first()
        results.append({
            "entity_id": node_id,
            "display_name": ent.display_name if ent else node_id,
            "type": ent.type if ent else "UNKNOWN",
            "influence_score": pr_score,
            "betweenness_score": betweenness.get(node_id, 0),
            "degree_score": degree.get(node_id, 0),
            "closeness_score": closeness.get(node_id, 0)
        })
        
    # Sort by PageRank score descending
    results.sort(key=lambda x: x["influence_score"], reverse=True)
    return results

@router.get("/communities")
def get_communities(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    comm_mapping = GraphService.detect_communities(db)
    # Group nodes by community id
    communities = {}
    for node_id, comm_id in comm_mapping.items():
        if comm_id not in communities:
            communities[comm_id] = []
            
        from backend.app.models.database_models import Entity
        ent = db.query(Entity).filter(Entity.id == node_id).first()
        communities[comm_id].append({
            "entity_id": node_id,
            "display_name": ent.display_name if ent else node_id,
            "type": ent.type if ent else "UNKNOWN"
        })
        
    return {
        "total_communities": len(communities),
        "communities": communities
    }

@router.get("/bridges")
def get_network_bridges(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    return GraphService.find_bridges(db)

@router.get("/health")
def get_network_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    from backend.app.models.database_models import Entity, Relationship
    import networkx as nx
    
    node_count = db.query(Entity).count()
    edge_count = db.query(Relationship).count()
    
    G = GraphService._build_networkx_graph(db)
    density = nx.density(G) if len(G) > 0 else 0
    avg_degree = sum(dict(G.degree()).values()) / len(G) if len(G) > 0 else 0
    
    # Connected components
    undir_G = G.to_undirected()
    components_count = nx.number_connected_components(undir_G) if len(G) > 0 else 0
    
    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "density": round(density, 4),
        "avg_degree": round(avg_degree, 2),
        "connected_components": components_count
    }

@router.get("/data-quality")
def get_data_quality(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    from backend.app.models.database_models import Entity, Relationship, Document, EntityResolution
    total_docs = db.query(Document).count()
    total_entities = db.query(Entity).count()
    total_rels = db.query(Relationship).count()
    
    low_conf_entities = db.query(Entity).filter(Entity.confidence < 0.7).count()
    low_conf_rels = db.query(Relationship).filter(Relationship.confidence < 0.7).count()
    
    pending_resolutions = db.query(EntityResolution).filter(EntityResolution.status == "PENDING").count()
    merged_resolutions = db.query(EntityResolution).filter(EntityResolution.status == "MERGED").count()
    
    processing_errors = db.query(Document).filter(Document.status == "ERROR").count()
    
    return {
        "total_documents": total_docs,
        "total_entities": total_entities,
        "total_relationships": total_rels,
        "low_confidence_entities": low_conf_entities,
        "low_confidence_relationships": low_conf_rels,
        "pending_resolutions": pending_resolutions,
        "merged_resolutions": merged_resolutions,
        "processing_errors": processing_errors
    }

