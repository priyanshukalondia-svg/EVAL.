# apps/api/app/services/reporting.py
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.models import InterviewSession, InterviewReport, TurnScore
from app.ai.providers import LLMProvider

class ReportGenerationService:
    @classmethod
    def generate_report(cls, db: Session, session_id: str) -> InterviewReport:
        """
        Compile all scored turns and conversation history into an executive hiring report.
        Includes dimensions, strengths, weaknesses, gaps, and a structured study plan.
        """
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found.")
            
        # 1. Gather all candidate turns and their scores
        candidate_turns = [t for t in session.turns if t.speaker == "candidate"]
        
        # Aggregate scores by dimension
        scores_by_dimension = {}
        history_text = ""
        
        for t in sorted(session.turns, key=lambda x: x.turn_index):
            history_text += f"{t.speaker.upper()} ({t.stage}): {t.content}\n"
            if t.speaker == "candidate":
                for score_record in t.scores:
                    dim = score_record.dimension
                    if dim not in scores_by_dimension:
                        scores_by_dimension[dim] = []
                    scores_by_dimension[dim].append(score_record.score)
                    
        # Calculate raw averages
        avg_scores = {}
        for dim, scores_list in scores_by_dimension.items():
            avg_scores[dim] = sum(scores_list) / len(scores_list) if scores_list else 60.0
            
        # 2. Use LLM to synthesize overall recommendation, strengths, weaknesses, gaps, and study plan
        system_instruction = (
            "You are a Staff Technical Recruiter and Hiring Committee lead. You summarize full "
            "interviews into a rigorous, professional evaluation report for hiring managers."
        )
        
        prompt = f"""
        Conduct a hiring committee synthesis of the following interview session.
        
        Role Track: {session.role_track}
        Candidate Profile Gaps: {session.candidate_profile.knowledge_graph.get('skills_missing', [])}
        Aggregated Scores: {avg_scores}
        
        Complete Interview History:
        {history_text}
        
        Generate a JSON report including:
        - recommendation: "strong_hire" | "hire" | "lean_hire" | "lean_no_hire" | "no_hire" | "strong_no_hire"
        - readiness_score: Overall percentage score (0-100) reflecting their readiness for this specific company and role.
        - strengths: List of 3-4 specific strengths demonstrated during the interview, quoting details.
        - weaknesses: List of 3-4 key areas of weakness or poor structural execution.
        - knowledge_gaps: Specific technical or domain areas they struggled with.
        - suggested_improvements: Actionable advice for candidate development.
        - study_plan: List of study items containing: {{topic, resources (list of strings), action_steps}}
        
        Return your report as a JSON object:
        {{
            "recommendation": "recommendation_string",
            "readiness_score": float_value,
            "strengths": ["strength 1", ...],
            "weaknesses": ["weakness 1", ...],
            "knowledge_gaps": ["gap 1", ...],
            "suggested_improvements": ["improvement 1", ...],
            "study_plan": [
                {{
                    "topic": "topic name",
                    "resources": ["resource 1", ...],
                    "action_steps": "concrete tasks to complete"
                }}
            ]
        }}
        """
        
        report_data = LLMProvider.generate_json(prompt, system_instruction=system_instruction)
        
        # 3. Save report to DB
        # If a report already exists, we overwrite it.
        existing_report = db.query(InterviewReport).filter(InterviewReport.session_id == session_id).first()
        if existing_report:
            db.delete(existing_report)
            db.commit()
            
        report = InterviewReport(
            session_id=session_id,
            recommendation=report_data.get("recommendation", "hire"),
            dimension_scores=avg_scores,
            strengths=report_data.get("strengths", []),
            weaknesses=report_data.get("weaknesses", []),
            knowledge_gaps=report_data.get("knowledge_gaps", []),
            suggested_improvements=report_data.get("suggested_improvements", []),
            study_plan=report_data.get("study_plan", []),
            readiness_score=report_data.get("readiness_score", 70.0)
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
