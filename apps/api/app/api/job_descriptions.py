# apps/api/app/api/job_descriptions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import JdRequest, JdResponse
from app.models.models import JobDescription, JdRequirement, User
from app.services.research import CompanyResearchService
from app.db.vector_store import VectorStore
from app.ai.providers import LLMProvider

router = APIRouter(prefix="/api/job-descriptions", tags=["job-descriptions"])

@router.post("/analyze", response_model=JdResponse)
def analyze_job_description(req: JdRequest, db: Session = Depends(get_db)):
    """
    Research target company, analyze job description text into structured JSON,
    generate vector embeddings, and save the JD record.
    """
    # Verify user exists
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    # 1. Research Company
    company = None
    if req.company_name:
        try:
            company = CompanyResearchService.research_company(db, req.company_name)
        except Exception as e:
            print(f"Company research failed for {req.company_name}: {e}")
            # Non-blocking: continue even if search fails
            
    # 2. Extract structured fields from raw JD text
    system_instruction = (
        "You are an expert technical recruiter. Analyze a job description text and extract "
        "required skills, preferred skills, core responsibilities, stack keywords, and expectations."
    )
    
    prompt = f"""
    Analyze the following Job Description for a '{req.role_title}' role.
    
    Job Description Text:
    {req.raw_text}
    
    Extract the details into a JSON object:
    - required_skills: list of strings
    - preferred_skills: list of strings
    - responsibilities: list of strings
    - keywords: list of strings (tech stack, tools, platforms)
    - company_expectations: list of strings (cultural values, work styles)
    """
    
    parsed_json = LLMProvider.generate_json(prompt, system_instruction=system_instruction)
    
    # 3. Create Job Description
    jd = JobDescription(
        user_id=req.user_id,
        company_id=company.id if company else None,
        source="text",
        raw_text=req.raw_text,
        parsed_json=parsed_json,
        role_title=req.role_title,
        seniority=req.seniority or "Mid"
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    
    # 4. Save individual JD requirements & compute embeddings for vector search
    # Process required skills
    for skill in parsed_json.get("required_skills", []):
        embedding = VectorStore.get_embedding(f"Required Skill: {skill}")
        db.add(JdRequirement(jd_id=jd.id, type="required_skill", value=skill, embedding=embedding))
        
    # Process preferred skills
    for skill in parsed_json.get("preferred_skills", []):
        embedding = VectorStore.get_embedding(f"Preferred Skill: {skill}")
        db.add(JdRequirement(jd_id=jd.id, type="preferred_skill", value=skill, embedding=embedding))
        
    # Process responsibilities
    for resp in parsed_json.get("responsibilities", []):
        embedding = VectorStore.get_embedding(f"Responsibility: {resp}")
        db.add(JdRequirement(jd_id=jd.id, type="responsibility", value=resp, embedding=embedding))
        
    db.commit()
    return jd
