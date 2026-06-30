# apps/api/app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, InterviewSession, QuestionBank, QuestionEmbedding, InterviewReport
from app.db.vector_store import VectorStore
from typing import Dict, Any, List

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """Retrieve system-wide dashboard statistics and usage analytics."""
    total_users = db.query(User).count()
    total_sessions = db.query(InterviewSession).count()
    completed_sessions = db.query(InterviewSession).filter(InterviewSession.status == "completed").count()
    
    # Recommendation breakdown
    reports = db.query(InterviewReport).all()
    recommendation_counts = {}
    total_readiness = 0.0
    for r in reports:
        recommendation_counts[r.recommendation] = recommendation_counts.get(r.recommendation, 0) + 1
        total_readiness += r.readiness_score
        
    avg_readiness = total_readiness / len(reports) if reports else 0.0
    
    # List of recent sessions
    recent_sessions = db.query(InterviewSession).order_by(InterviewSession.started_at.desc()).limit(10).all()
    session_list = []
    for s in recent_sessions:
        session_list.append({
            "id": s.id,
            "email": s.user.email,
            "role_track": s.role_track,
            "status": s.status,
            "started_at": s.started_at,
            "readiness_score": s.report.readiness_score if s.report else None,
            "recommendation": s.report.recommendation if s.report else None
        })
        
    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "average_readiness_score": avg_readiness,
        "recommendation_distribution": recommendation_counts,
        "recent_sessions": session_list
    }

@router.post("/seed-questions")
def seed_questions(db: Session = Depends(get_db)):
    """Seed the database question bank with high-quality standard questions for various tracks."""
    # Check if questions already exist
    existing_count = db.query(QuestionBank).count()
    if existing_count > 0:
        return {"message": "Question bank is already seeded.", "seeded_count": existing_count}
        
    seed_data = [
        # SWE Technical Questions
        {
            "category": "technical_round",
            "subcategory": "databases",
            "text": "What is the difference between SQL and NoSQL databases, and how do you decide which one to use for a high-traffic e-commerce system?",
            "difficulty": "medium",
            "role_track": "swe",
            "tags": ["sql", "nosql", "system_design"]
        },
        {
            "category": "technical_round",
            "subcategory": "performance",
            "text": "How do you identify and resolve database performance bottlenecks, such as slow-running queries and high CPU utilization?",
            "difficulty": "hard",
            "role_track": "swe",
            "tags": ["indexing", "caching", "optimization"]
        },
        {
            "category": "coding_round",
            "subcategory": "algorithms",
            "text": "Explain how you would write a function to detect if a linked list contains a cycle, and describe the time and space complexity of your solution.",
            "difficulty": "medium",
            "role_track": "swe",
            "tags": ["pointers", "complexity", "algorithms"]
        },
        # Data Analyst Questions
        {
            "category": "technical_round",
            "subcategory": "sql_aggregations",
            "text": "How do window functions like ROW_NUMBER() and DENSE_RANK() work in SQL, and when would you prefer them over standard GROUP BY aggregations?",
            "difficulty": "medium",
            "role_track": "data_analyst",
            "tags": ["sql", "window_functions", "aggregations"]
        },
        {
            "category": "case_study",
            "subcategory": "dashboard_design",
            "text": "Imagine an executive reports that their sales dashboard shows a 20% drop in revenue this week. Walk me through your steps to audit the data and locate the root cause.",
            "difficulty": "hard",
            "role_track": "data_analyst",
            "tags": ["root_cause", "dashboard", "storytelling"]
        },
        # Product Manager Questions
        {
            "category": "case_study",
            "subcategory": "prioritization",
            "text": "If you were the Product Manager for Google Photos, and your team is debating between building a new collaborative sharing album feature or improving AI search search-speed, how would you prioritize?",
            "difficulty": "hard",
            "role_track": "pm",
            "tags": ["prioritization", "frameworks", "metrics"]
        },
        # UI/UX Designer Questions
        {
            "category": "technical_round",
            "subcategory": "design_system",
            "text": "How do you establish a design system from scratch, and how do you ensure visual consistency and accessibility (WCAG compliance) across diverse components?",
            "difficulty": "medium",
            "role_track": "ui_ux_designer",
            "tags": ["design_systems", "accessibility", "components"]
        },
        # Behavioral / STAR Questions
        {
            "category": "behavioral_round",
            "subcategory": "conflict",
            "text": "Describe a situation where you had a significant technical disagreement with a team member. How did you handle it and what was the outcome?",
            "difficulty": "medium",
            "role_track": "swe",
            "tags": ["teamwork", "conflict_resolution", "behavioral"]
        },
        {
            "category": "behavioral_round",
            "subcategory": "ownership",
            "text": "Tell me about a time when you took on a task or project outside your direct scope of responsibility. What was your motivation and what did you achieve?",
            "difficulty": "easy",
            "role_track": "swe",
            "tags": ["ownership", "initiative", "behavioral"]
        }
    ]
    
    seeded_count = 0
    for q in seed_data:
        try:
            q_model = QuestionBank(
                category=q["category"],
                subcategory=q["subcategory"],
                text=q["text"],
                difficulty=q["difficulty"],
                role_track=q["role_track"],
                tags=q["tags"]
            )
            db.add(q_model)
            db.commit()
            db.refresh(q_model)
            
            # Compute embedding for question matching
            emb = VectorStore.get_embedding(q["text"])
            db.add(QuestionEmbedding(question_id=q_model.id, embedding=emb))
            db.commit()
            seeded_count += 1
        except Exception as e:
            db.rollback()
            print(f"Failed to seed question: {q['text']}. Error: {e}")
            
    return {"message": "Questions seeded successfully.", "seeded_count": seeded_count}
