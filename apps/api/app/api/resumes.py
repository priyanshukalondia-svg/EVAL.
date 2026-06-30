# apps/api/app/api/resumes.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import ResumeResponse
from app.models.models import User, Resume
from app.services.parsing import ResumeParsingService

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    email: str = Form(...),
    full_name: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a resume file (PDF, TXT), parse details, compute vector embeddings,
    and associate it with a user (auto-created if they don't exist).
    """
    # 1. Fetch or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    # Check file extension
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["pdf", "txt"]:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")
        
    try:
        file_bytes = await file.read()
        resume = ResumeParsingService.process_and_save_resume(
            db=db,
            user_id=user.id,
            file_name=filename,
            file_bytes=file_bytes,
            file_type=ext
        )
        return resume
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")

@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    """Fetch parsed resume contents by ID."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume
