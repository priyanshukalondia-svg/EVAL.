# apps/api/app/services/coaching.py
from sqlalchemy.orm import Session
from app.models.models import InterviewTurn
from app.ai.providers import LLMProvider

class CoachingService:
    @classmethod
    def get_turn_coaching(cls, db: Session, turn_id: str) -> dict:
        """
        Analyze a specific candidate answer to provide detailed feedback:
        positives, negatives, structural critiques, alternative wording,
        and a fully rewritten STAR-structured response.
        """
        candidate_turn = db.query(InterviewTurn).filter(InterviewTurn.id == turn_id).first()
        if not candidate_turn or candidate_turn.speaker != "candidate":
            return {"error": "Invalid turn ID or turn speaker is not candidate."}
            
        session = candidate_turn.session
        turns = sorted(session.turns, key=lambda x: x.turn_index)
        
        # Get the question asked
        ai_question = ""
        for t in reversed(turns[:candidate_turn.turn_index]):
            if t.speaker == "ai":
                ai_question = t.content
                break
                
        # Load turn scores
        score_details = []
        for s in candidate_turn.scores:
            score_details.append(f"{s.dimension}: {s.score} ({s.rationale})")
            
        system_instruction = (
            "You are a master career coach and senior technical recruiter. You analyze candidates' answers "
            "and teach them how to structure and present their achievements to stand out."
        )
        
        prompt = f"""
        Provide detailed coaching for this candidate's interview answer.
        
        Role Track: {session.role_track}
        Question Asked: "{ai_question}"
        Candidate's Answer: "{candidate_turn.content}"
        Score Evaluation: {', '.join(score_details)}
        
        Generate a detailed coaching critique in JSON format containing:
        - liked: What the recruiter liked about the answer (confidence, key technical words used, etc.)
        - disliked: What was missing, weak, or could be improved (lack of details, filler words, unstructured flow)
        - ideal_structure: The recommended structure for answering this specific type of question (e.g., STAR, CAR, or technical layering)
        - better_wording: Specific suggestions for alternative phrasing or professional terminology
        - rewritten_star: A rewritten version of their answer. It must use their actual points but organize them into a clean, compelling STAR (Situation, Task, Action, Result) format with professional vocabulary and mock metrics where they didn't provide any.
        
        Return your analysis as a JSON object:
        {{
            "liked": "bulleted description",
            "disliked": "bulleted description",
            "ideal_structure": "explanation",
            "better_wording": "rephrasing suggestions",
            "rewritten_star": "fully fleshed out STAR answer"
        }}
        """
        
        return LLMProvider.generate_json(prompt, system_instruction=system_instruction)
