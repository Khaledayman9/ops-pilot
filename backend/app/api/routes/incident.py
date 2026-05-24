from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.schemas.incident import IncidentRequest, IncidentResponse
from app.services.incident_service import IncidentService

router = APIRouter()


@router.post("/analyze", response_model=IncidentResponse)
async def analyze_incident(
    request: IncidentRequest,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    return await IncidentService(db).analyze(request)