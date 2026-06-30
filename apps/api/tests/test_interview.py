# apps/api/tests/test_interview.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.models.models import User, Resume, JobDescription, CandidateProfile, InterviewSession, InterviewTurn
from app.services.interview_engine.engine import InterviewEngine
from app.services.scoring import ScoringService
from app.services.reporting import ReportGenerationService

# Setup in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionTesting()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_complete_interview_workflow_offline(db_session):
    """
    Test the entire database model mapping, state machine logic, scoring triggers,
    and report generation workflow in offline fallback mode.
    """
    # 1. Create User
    user = User(email="test@candidate.com", full_name="Test Candidate")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    
    # 2. Add Resume
    resume = Resume(
        user_id=user.id,
        file_url="my_cv.pdf",
        file_type="pdf",
        raw_text="Jane Candidate\nExperience: Software Engineer at Google for 2 years.\nSkills: Python, SQL.",
        parsed_json={
            "personal_info": {"name": "Jane Candidate", "email": "test@candidate.com"},
            "skills": ["Python", "SQL"],
            "experience": [{"title": "Software Engineer", "company": "Google", "duration": "2 years"}]
        }
    )
    db_session.add(resume)
    db_session.commit()
    assert resume.id is not None
    
    # 3. Add Job Description
    jd = JobDescription(
        user_id=user.id,
        role_title="Backend Developer",
        seniority="Mid",
        raw_text="Required: Python, SQL. Experience: 2+ years.",
        parsed_json={
            "required_skills": ["Python", "SQL"],
            "responsibilities": ["Build robust APIs"]
        },
        source="text"
    )
    db_session.add(jd)
    db_session.commit()
    assert jd.id is not None
    
    # 4. Create Profile / Knowledge Graph
    profile = CandidateProfile(
        user_id=user.id,
        resume_id=resume.id,
        jd_id=jd.id,
        knowledge_graph={
            "match_percentage": 90,
            "skills_matched": ["Python", "SQL"],
            "skills_missing": [],
            "project_deep_dives": [],
            "recommended_focus_areas": []
        }
    )
    db_session.add(profile)
    db_session.commit()
    assert profile.id is not None
    
    # 5. Start Interview Session
    session = InterviewEngine.start_session(
        db=db_session,
        user_id=user.id,
        profile_id=profile.id,
        role_track="swe"
    )
    assert session.id is not None
    assert session.status == "in_progress"
    assert len(session.turns) == 1
    assert session.turns[0].speaker == "ai"
    
    # 6. Candidate answers initial question
    result = InterviewEngine.process_candidate_answer(
        db=db_session,
        session_id=session.id,
        answer_text="Hi, I'm Jane. I have been working as a Software Engineer at Google for 2 years, building APIs in Python."
    )
    
    # Check that candidate turn and subsequent AI turn are saved
    assert len(session.turns) == 3 # Greeting (AI) -> Answer (Candidate) -> Next Question (AI)
    assert session.turns[1].speaker == "candidate"
    assert session.turns[2].speaker == "ai"
    
    # 7. Evaluate the candidate's response
    candidate_turn = session.turns[1]
    scores = ScoringService.score_turn(db=db_session, turn_id=candidate_turn.id)
    assert len(scores) > 0
    assert candidate_turn.scores[0].score >= 0.0
    
    # 8. Force complete and Compile Final Report
    report = ReportGenerationService.generate_report(db=db_session, session_id=session.id)
    print("REPORT STRENGTHS:", report.strengths)
    print("REPORT READINESS SCORE:", report.readiness_score)
    print("REPORT RECOMMENDATION:", report.recommendation)
    assert report.id is not None
    assert report.readiness_score > 0.0
    assert len(report.strengths) > 0
    assert len(report.study_plan) > 0
