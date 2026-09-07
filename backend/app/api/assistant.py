from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, AuditLog
from backend.app.schemas.schemas import AssistantRequest, AssistantResponse
from backend.app.services.ai_assistant import AIAssistantService

router = APIRouter(prefix="/api/assistant", tags=["AI Investigator Assistant"])

read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])

@router.post("", response_model=AssistantResponse)
def ask_assistant(
    req: AssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    try:
        response_data = AIAssistantService.answer_question(
            db, req.question, req.context_entity_id
        )
        
        # Log to audit logs
        log = AuditLog(
            user_id=current_user.id,
            action="ask_ai_assistant",
            resource=f"query:{req.question[:50]}...",
            result="SUCCESS",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running assistant pipeline: {e}"
        )
