from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.postgres import get_db
from app.schemas.incident import IncidentRequest, IncidentResponse
from app.services.incident_service import IncidentService

router = APIRouter()


@router.post(
    "/analyze",
    response_model=IncidentResponse,
    summary="Run synchronous incident analysis (non-streaming)",
)
async def analyze_incident(
    request: IncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncidentResponse:
    return await IncidentService(db).analyze(request, user_id=str(current_user.id))
