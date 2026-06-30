# apps/api/app/services/interview_engine/engine.py
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.models import InterviewSession, InterviewTurn, CandidateProfile, QuestionBank
from app.db.vector_store import VectorStore
from app.ai.providers import LLMProvider

# Configuration mapping roles to their interview stages
STAGES_BY_ROLE = {
    "swe": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "coding_round", 
        "leadership_round", "company_role_fit", "candidate_questions", "closing"
    ],
    "backend_developer": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "coding_round", 
        "leadership_round", "company_role_fit", "candidate_questions", "closing"
    ],
    "frontend_developer": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "coding_round", 
        "leadership_round", "company_role_fit", "candidate_questions", "closing"
    ],
    "full_stack_developer": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "coding_round", 
        "leadership_round", "company_role_fit", "candidate_questions", "closing"
    ],
    "ai_engineer": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "coding_round", 
        "leadership_round", "company_role_fit", "candidate_questions", "closing"
    ],
    "ml_engineer": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "coding_round", 
        "leadership_round", "company_role_fit", "candidate_questions", "closing"
    ],
    "data_analyst": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "case_study", 
        "company_role_fit", "candidate_questions", "closing"
    ],
    "data_scientist": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "case_study", 
        "company_role_fit", "candidate_questions", "closing"
    ],
    "product_manager": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "case_study", "leadership_round", 
        "company_role_fit", "candidate_questions", "closing"
    ],
    "ui_ux_designer": [
        "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
        "behavioral_round", "technical_round", "case_study", 
        "company_role_fit", "candidate_questions", "closing"
    ]
}

DEFAULT_STAGES = [
    "greeting", "icebreaker", "resume_walkthrough", "projects_discussion", 
    "behavioral_round", "technical_round", "company_role_fit", 
    "candidate_questions", "closing"
]

class InterviewEngine:
    @classmethod
    def get_stages_for_role(cls, role_track: str) -> List[str]:
        """Get ordered stages for a given role track."""
        role_key = role_track.lower().replace(" ", "_")
        return STAGES_BY_ROLE.get(role_key, DEFAULT_STAGES)

    @classmethod
    def start_session(
        cls, db: Session, user_id: str, profile_id: str, role_track: str, mode: str = "text"
    ) -> InterviewSession:
        """Initialize a new interview session and generate the initial greeting turn."""
        # 1. Create session record
        session = InterviewSession(
            user_id=user_id,
            candidate_profile_id=profile_id,
            role_track=role_track,
            mode=mode,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # 2. Generate initial greeting turn from AI
        stages = cls.get_stages_for_role(role_track)
        initial_stage = stages[0]
        
        profile = db.query(CandidateProfile).filter(CandidateProfile.id == profile_id).first()
        candidate_name = profile.knowledge_graph.get("personal_info", {}).get("name", "Candidate")
        
        greeting_text = (
            f"Hello {candidate_name}, and welcome! Thank you for taking the time to speak with me today. "
            f"I'm looking forward to discussing your background and exploring your fit for the {role_track} role. "
            "To start off, could you briefly introduce yourself and share what motivated you to apply for this position?"
        )
        
        turn = InterviewTurn(
            session_id=session.id,
            turn_index=0,
            speaker="ai",
            stage=initial_stage,
            content=greeting_text,
            engine_meta={
                "difficulty": "easy",
                "topic": "introduction",
                "stage_index": 0
            }
        )
        db.add(turn)
        db.commit()
        
        return session

    @classmethod
    def process_candidate_answer(
        cls, db: Session, session_id: str, answer_text: str
    ) -> Dict[str, Any]:
        """
        Record candidate's answer and invoke the reasoning loop to decide
        the next interviewer turn (follow-up, next stage, etc.).
        """
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session or session.status != "in_progress":
            raise ValueError("Active session not found.")
            
        # 1. Get previous turns and sort by index
        turns = sorted(session.turns, key=lambda t: t.turn_index)
        last_ai_turn = [t for t in turns if t.speaker == "ai"][-1]
        
        current_stage = last_ai_turn.stage
        current_difficulty = last_ai_turn.engine_meta.get("difficulty", "medium")
        current_stage_index = last_ai_turn.engine_meta.get("stage_index", 0)
        
        # 2. Save candidate's turn
        candidate_turn = InterviewTurn(
            session_id=session_id,
            turn_index=len(turns),
            speaker="candidate",
            stage=current_stage,
            content=answer_text,
            engine_meta={
                "difficulty": current_difficulty,
                "stage_index": current_stage_index
            }
        )
        db.add(candidate_turn)
        db.commit()
        db.refresh(candidate_turn)
        
        # 3. Dynamic Reasoning: Decide the next AI action
        next_ai_turn_index = candidate_turn.turn_index + 1
        stages = cls.get_stages_for_role(session.role_track)
        
        profile = session.candidate_profile
        resume_data = profile.resume.parsed_json
        jd_data = profile.jd.parsed_json
        company_data = profile.company.name if profile.company else "the target company"
        knowledge_graph = profile.knowledge_graph
        
        # Build conversational history for context
        history_str = ""
        for t in sorted(session.turns, key=lambda x: x.turn_index)[-6:]:
            history_str += f"{t.speaker.upper()}: {t.content}\n"
            
        # Determine if we should adjust difficulty based on performance (scoring runs asynchronously,
        # so we check scores of previous turns if available)
        adjusted_difficulty = cls._determine_difficulty(turns)
        
        # Instruct LLM as a Staff Technical Recruiter
        system_instruction = (
            "You are an elite, reasoning-driven interviewer at a top technology company. "
            "You do not read from scripts. Every answer influences your next question. "
            "Probe deep into technical claims. Never accept shallow answers. "
            "Maintain conversational flow. Be supportive but rigorous."
        )
        
        prompt = f"""
        You are interviewing a candidate for the '{session.role_track}' position at '{company_data}'.
        
        Candidate Profile Summary:
        - Skills: {', '.join(knowledge_graph.get('skills_matched', []))}
        - Missing/Weak Skills: {', '.join(knowledge_graph.get('skills_missing', []))}
        - Critical claims to probe: {knowledge_graph.get('project_deep_dives', [])}
        - Focus Areas: {knowledge_graph.get('recommended_focus_areas', [])}
        
        Current Interview Progress:
        - Stage: {current_stage}
        - Difficulty: {adjusted_difficulty}
        - Stages Sequence: {', '.join(stages)}
        - Current Stage Index: {current_stage_index} (out of {len(stages)-1})
        
        Conversation History (last 6 turns):
        {history_str}
        
        Based on the candidate's last answer, choose your next move.
        Determine if you should:
        1. "follow_up": Probe deeper into their last answer (e.g. details of dashboard, tech stack, STAR metrics, conflict resolution, metrics).
        2. "new_question": Ask a new question relevant to the current stage ({current_stage}).
        3. "transition": Move to the next stage of the interview: '{stages[min(current_stage_index+1, len(stages)-1)]}'.
        4. "close": Wrap up the interview (if we are in the closing stage).
        
        Provide your choice as a JSON object:
        {{
            "action": "follow_up" | "new_question" | "transition" | "close",
            "next_stage": "name of stage",
            "next_stage_index": integer_index_of_stage,
            "difficulty": "easy" | "medium" | "hard" | "expert",
            "target_dimension": "knowledge" | "communication" | "problem_solving" | "leadership" | "culture_fit" | "technical_skill" | "none",
            "question": "Your next spoken question or follow-up response.",
            "rationale": "Brief explanation of why you made this conversational move."
        }}
        """
        
        decision = LLMProvider.generate_json(prompt, system_instruction=system_instruction)
        
        # 4. Save and return the next AI turn
        action = decision.get("action", "follow_up")
        next_stage = decision.get("next_stage", current_stage)
        next_stage_index = decision.get("next_stage_index", current_stage_index)
        ai_difficulty = decision.get("difficulty", adjusted_difficulty)
        
        # If LLM indicates transition, update state variables
        if action == "transition" and current_stage_index < len(stages) - 1:
            next_stage_index = current_stage_index + 1
            next_stage = stages[next_stage_index]
            
        if action == "close" or next_stage == "closing":
            session.status = "completed"
            session.ended_at = datetime.utcnow()
            next_stage = "closing"
            next_stage_index = stages.index("closing")
            
        ai_turn = InterviewTurn(
            session_id=session_id,
            turn_index=next_ai_turn_index,
            speaker="ai",
            stage=next_stage,
            content=decision.get("question", "Could you tell me more about that?"),
            engine_meta={
                "difficulty": ai_difficulty,
                "stage_index": next_stage_index,
                "action": action,
                "target_dimension": decision.get("target_dimension", "none"),
                "rationale": decision.get("rationale", "")
            }
        )
        db.add(ai_turn)
        db.commit()
        db.refresh(ai_turn)
        
        return {
            "turn_id": ai_turn.id,
            "speaker": ai_turn.speaker,
            "content": ai_turn.content,
            "stage": ai_turn.stage,
            "difficulty": ai_turn.engine_meta.get("difficulty"),
            "status": session.status
        }

    @staticmethod
    def _determine_difficulty(turns: List[InterviewTurn]) -> str:
        """
        Look at recent scores to adjust difficulty.
        If recent turn scores average > 85, increase difficulty.
        If < 60, decrease difficulty.
        """
        scored_turns = [t for t in turns if t.speaker == "candidate" and t.scores]
        if not scored_turns:
            return "medium"
            
        # Get average score of the last 2 scored candidate answers
        last_scores = []
        for t in scored_turns[-2:]:
            scores_vals = [s.score for s in t.scores]
            if scores_vals:
                last_scores.append(sum(scores_vals) / len(scores_vals))
                
        if not last_scores:
            return "medium"
            
        avg_score = sum(last_scores) / len(last_scores)
        
        # Fetch difficulty of the last turn
        last_diff = scored_turns[-1].engine_meta.get("difficulty", "medium")
        
        if avg_score > 85:
            # Increase difficulty
            diff_levels = ["easy", "medium", "hard", "expert"]
            current_idx = diff_levels.index(last_diff)
            return diff_levels[min(current_idx + 1, len(diff_levels) - 1)]
        elif avg_score < 60:
            # Decrease difficulty
            diff_levels = ["easy", "medium", "hard", "expert"]
            current_idx = diff_levels.index(last_diff)
            return diff_levels[max(current_idx - 1, 0)]
            
        return last_diff
