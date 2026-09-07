from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User
from backend.app.services.graph_service import GraphService

router = APIRouter(prefix="/api/graph", tags=["Graph Explorer"])

read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])

@router.get("")
def get_full_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    return GraphService.get_full_graph(db)

@router.get("/shortest-path")
def get_shortest_path(
    source: str = Query(..., description="Source entity ID"),
    target: str = Query(..., description="Target entity ID"),
    investigation_id: str = Query(None, description="Optional active investigation ID to constrain path"),
    scope: str = Query("case", pattern="^(case|direct|2hop|full)$", description="Scope of the network: case, direct, 2hop, full"),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    path = GraphService.get_shortest_path(db, source, target, investigation_id=investigation_id, scope=scope)
    if not path or not path.get("nodes"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No path found between {source} and {target}"
        )
    return path
