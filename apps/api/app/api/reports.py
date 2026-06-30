# apps/api/app/api/reports.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import ReportResponse, CoachResponse
from app.models.models import InterviewReport
from app.services.coaching import CoachingService

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/session/{session_id}", response_model=ReportResponse)
def get_session_report(session_id: str, db: Session = Depends(get_db)):
    """Fetch compiled executive report for a completed session."""
    report = db.query(InterviewReport).filter(InterviewReport.session_id == session_id).first()
    if not report:
        raise HTTPException(
            status_code=404, 
            detail="Report not found. The interview might still be in progress or scoring is being finalized."
        )
    return report

@router.get("/turn/{turn_id}/coach", response_model=CoachResponse)
def get_turn_coaching(turn_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed Career Coach analysis and STAR rewrite for a specific answer."""
    try:
        coaching = CoachingService.get_turn_coaching(db, turn_id)
        if "error" in coaching:
            raise HTTPException(status_code=404, detail=coaching["error"])
        return coaching
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate coaching suggestions: {str(e)}")
