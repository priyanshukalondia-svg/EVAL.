# apps/api/app/api/interviews.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import InterviewStartRequest, InterviewSessionResponse, AnswerRequest, InterviewTurnResponse
from app.models.models import InterviewSession, InterviewTurn, CandidateProfile
from app.services.profile import CandidateProfileService
from app.services.interview_engine.engine import InterviewEngine
from app.services.scoring import ScoringService
from app.services.reporting import ReportGenerationService
from typing import List

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

@router.post("/session", response_model=InterviewSessionResponse)
def start_interview_session(req: InterviewStartRequest, db: Session = Depends(get_db)):
    """
    Initialize interview session, generate candidate profile knowledge graph,
    and output initial AI greeting turn.
    """
    # Verify profile or compile new one
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == req.user_id,
        CandidateProfile.resume_id == req.resume_id,
        CandidateProfile.jd_id == req.jd_id
    ).first()
    
    if not profile:
        try:
            # Look up company id from JD
            from app.models.models import JobDescription
            jd = db.query(JobDescription).filter(JobDescription.id == req.jd_id).first()
            company_id = jd.company_id if jd else None
            
            profile = CandidateProfileService.build_candidate_profile(
                db=db,
                user_id=req.user_id,
                resume_id=req.resume_id,
                jd_id=req.jd_id,
                company_id=company_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to build candidate profile: {str(e)}")
            
    # Start session
    try:
        session = InterviewEngine.start_session(
            db=db,
            user_id=req.user_id,
            profile_id=profile.id,
            role_track=req.role_track,
            mode=req.mode
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")

@router.post("/session/{session_id}/answer")
def submit_answer(
    session_id: str,
    req: AnswerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit candidate answer. The engine computes the next question.
    Scoring runs asynchronously in background tasks.
    """
    # 1. Process candidate answer and get next AI question
    try:
        result = InterviewEngine.process_candidate_answer(
            db=db,
            session_id=session_id,
            answer_text=req.answer
        )
        
        # 2. Score candidate's turn in background
        # Find the candidate turn we just saved (which is index before the new AI turn)
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        turns = sorted(session.turns, key=lambda x: x.turn_index)
        candidate_turn = turns[-2] # AI turn is the last one (-1), candidate turn is before it (-2)
        
        # Dispatch evaluation async
        background_tasks.add_task(ScoringService.score_turn, db, candidate_turn.id)
        
        # 3. If interview completed, trigger report generation in background
        if result["status"] == "completed":
            background_tasks.add_task(ReportGenerationService.generate_report, db, session_id)
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")

@router.get("/session/{session_id}/history", response_model=List[InterviewTurnResponse])
def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """Fetch sorted transcript of the interview session."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return sorted(session.turns, key=lambda x: x.turn_index)

@router.post("/session/{session_id}/finalize")
def finalize_session(session_id: str, db: Session = Depends(get_db)):
    """Manually finalize and close interview session, compiling the final report."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
        
    import datetime
    session.status = "completed"
    session.ended_at = datetime.datetime.utcnow()
    db.commit()
    
    try:
        report = ReportGenerationService.generate_report(db, session_id)
        return {"status": "completed", "report_id": report.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
