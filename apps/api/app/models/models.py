# apps/api/app/models/models.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime, JSON, Numeric, Float
from sqlalchemy.orm import relationship
from app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="candidate") # "candidate" | "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    job_descriptions = relationship("JobDescription", back_populates="user", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String(1024), nullable=True)
    file_type = Column(String(10), nullable=True) # "pdf" | "docx" | "txt"
    raw_text = Column(Text, nullable=True)
    parsed_json = Column(JSON, nullable=True) # Full parsed profile
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="resumes")
    entities = relationship("ResumeEntity", back_populates="resume", cascade="all, delete-orphan")
    candidate_profiles = relationship("CandidateProfile", back_populates="resume", cascade="all, delete-orphan")


class ResumeEntity(Base):
    __tablename__ = "resume_entities"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False) # "education"|"experience"|"project"|"skill"|"certification"
    content = Column(JSON, nullable=False) # Entity details
    embedding = Column(JSON, nullable=True) # Serialized float list [0.1, -0.2, ...]
    
    resume = relationship("Resume", back_populates="entities")


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    industry = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job_descriptions = relationship("JobDescription", back_populates="company")
    research_entries = relationship("CompanyResearch", back_populates="company", cascade="all, delete-orphan")
    candidate_profiles = relationship("CandidateProfile", back_populates="company")


class CompanyResearch(Base):
    __tablename__ = "company_research"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False) # "mission"|"values"|"leadership_principles"|"interview_process"|"news"
    content = Column(Text, nullable=False)
    source_url = Column(String(1024), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="research_entries")


class JobDescription(Base):
    __tablename__ = "job_descriptions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(20), nullable=False) # "pdf" | "text" | "url"
    raw_text = Column(Text, nullable=True)
    parsed_json = Column(JSON, nullable=True)
    role_title = Column(String(255), nullable=False)
    seniority = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="job_descriptions")
    company = relationship("Company", back_populates="job_descriptions")
    requirements = relationship("JdRequirement", back_populates="jd", cascade="all, delete-orphan")
    candidate_profiles = relationship("CandidateProfile", back_populates="jd", cascade="all, delete-orphan")


class JdRequirement(Base):
    __tablename__ = "jd_requirements"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    jd_id = Column(String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(100), nullable=False) # "required_skill"|"preferred_skill"|"responsibility"|"keyword"
    value = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)
    
    jd = relationship("JobDescription", back_populates="requirements")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    jd_id = Column(String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    knowledge_graph = Column(JSON, nullable=False) # Structured graph data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resume = relationship("Resume", back_populates="candidate_profiles")
    jd = relationship("JobDescription", back_populates="candidate_profiles")
    company = relationship("Company", back_populates="candidate_profiles")
    interview_sessions = relationship("InterviewSession", back_populates="candidate_profile", cascade="all, delete-orphan")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_profile_id = Column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String(20), default="text") # "text" | "voice"
    status = Column(String(50), default="in_progress") # "in_progress" | "completed" | "abandoned"
    role_track = Column(String(100), nullable=False) # e.g. "swe" | "data_analyst" | "pm"
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="interview_sessions")
    candidate_profile = relationship("CandidateProfile", back_populates="interview_sessions")
    turns = relationship("InterviewTurn", back_populates="session", cascade="all, delete-orphan")
    report = relationship("InterviewReport", back_populates="session", uselist=False, cascade="all, delete-orphan")


class InterviewTurn(Base):
    __tablename__ = "interview_turns"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    turn_index = Column(Integer, nullable=False)
    speaker = Column(String(20), nullable=False) # "ai" | "candidate"
    stage = Column(String(100), nullable=False) # e.g. "greeting" | "behavioral"
    content = Column(Text, nullable=False)
    question_bank_id = Column(String(36), ForeignKey("question_bank.id", ondelete="SET NULL"), nullable=True)
    engine_meta = Column(JSON, nullable=True) # difficulty, topic tags, STAR flags, sentiment, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("InterviewSession", back_populates="turns")
    question_bank = relationship("QuestionBank", back_populates="turns")
    scores = relationship("TurnScore", back_populates="turn", cascade="all, delete-orphan")


class QuestionBank(Base):
    __tablename__ = "question_bank"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100), nullable=True)
    text = Column(Text, nullable=False)
    difficulty = Column(String(50), nullable=False) # "easy" | "medium" | "hard" | "expert"
    role_track = Column(String(100), nullable=False)
    tags = Column(JSON, nullable=True)
    
    turns = relationship("InterviewTurn", back_populates="question_bank")
    embeddings = relationship("QuestionEmbedding", back_populates="question", cascade="all, delete-orphan")


class QuestionEmbedding(Base):
    __tablename__ = "question_embeddings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    question_id = Column(String(36), ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False)
    embedding = Column(JSON, nullable=False)
    
    question = relationship("QuestionBank", back_populates="embeddings")


class TurnScore(Base):
    __tablename__ = "turn_scores"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    turn_id = Column(String(36), ForeignKey("interview_turns.id", ondelete="CASCADE"), nullable=False)
    dimension = Column(String(100), nullable=False) # e.g. "knowledge", "communication", "STAR"
    score = Column(Float, nullable=False) # 0.0 to 100.0
    rationale = Column(Text, nullable=True)
    
    turn = relationship("InterviewTurn", back_populates="scores")


class InterviewReport(Base):
    __tablename__ = "interview_reports"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    recommendation = Column(String(50), nullable=False) # "strong_hire" | "hire" | "lean_hire" | "lean_no_hire" | "no_hire" | "strong_no_hire"
    dimension_scores = Column(JSON, nullable=False) # Map of dimensions to aggregate scores
    strengths = Column(JSON, nullable=False) # List of strengths
    weaknesses = Column(JSON, nullable=False) # List of weaknesses
    knowledge_gaps = Column(JSON, nullable=False) # List of knowledge gaps
    suggested_improvements = Column(JSON, nullable=False) # List of actions
    study_plan = Column(JSON, nullable=False) # Study curriculum
    readiness_score = Column(Float, nullable=False) # 0.0 to 100.0
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("InterviewSession", back_populates="report")
