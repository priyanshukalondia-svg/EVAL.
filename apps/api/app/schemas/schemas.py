# apps/api/app/schemas/schemas.py
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResumeResponse(BaseModel):
    id: str
    user_id: str
    file_url: Optional[str]
    file_type: Optional[str]
    parsed_json: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class JdRequest(BaseModel):
    user_id: str
    raw_text: Optional[str] = None
    jd_url: Optional[str] = None
    company_name: str
    role_title: str
    seniority: Optional[str] = None

class JdResponse(BaseModel):
    id: str
    user_id: str
    company_id: Optional[str]
    role_title: str
    seniority: Optional[str]
    parsed_json: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class InterviewStartRequest(BaseModel):
    user_id: str
    resume_id: str
    jd_id: str
    role_track: str # "swe" | "data_analyst" | "pm" | "ui_ux_designer"
    mode: Optional[str] = "text" # "text" | "voice"

class InterviewSessionResponse(BaseModel):
    id: str
    user_id: str
    candidate_profile_id: str
    role_track: str
    mode: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AnswerRequest(BaseModel):
    answer: str

class InterviewTurnResponse(BaseModel):
    id: str
    session_id: str
    turn_index: int
    speaker: str
    stage: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TurnScoreResponse(BaseModel):
    dimension: str
    score: float
    rationale: Optional[str]
    
    class Config:
        from_attributes = True

class TurnScoreDetailResponse(BaseModel):
    turn_id: str
    scores: List[TurnScoreResponse]
    star_evaluation: Optional[Dict[str, Any]]

class ReportResponse(BaseModel):
    id: str
    session_id: str
    recommendation: str
    dimension_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    knowledge_gaps: List[str]
    suggested_improvements: List[str]
    study_plan: List[Dict[str, Any]]
    readiness_score: float
    generated_at: datetime
    
    class Config:
        from_attributes = True

class CoachResponse(BaseModel):
    liked: str
    disliked: str
    ideal_structure: str
    better_wording: str
    rewritten_star: str
