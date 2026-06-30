# apps/api/app/services/scoring.py
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.models import InterviewTurn, TurnScore
from app.ai.providers import LLMProvider

class ScoringService:
    @classmethod
    def score_turn(cls, db: Session, turn_id: str) -> List[TurnScore]:
        """
        Evaluate a candidate's answer against relevant rubric dimensions.
        Analyzes for STAR behavioral structure and records ratings.
        """
        candidate_turn = db.query(InterviewTurn).filter(InterviewTurn.id == turn_id).first()
        if not candidate_turn or candidate_turn.speaker != "candidate":
            return []

        # Find the question that prompted this answer
        session = candidate_turn.session
        turns = sorted(session.turns, key=lambda x: x.turn_index)
        
        # Get the previous turn (which was the AI's question)
        ai_question = ""
        target_dimension_hint = "none"
        for t in reversed(turns[:candidate_turn.turn_index]):
            if t.speaker == "ai":
                ai_question = t.content
                target_dimension_hint = t.engine_meta.get("target_dimension", "none")
                break

        if not ai_question:
            return []

        # LLM Rubric Scorer System Prompt
        system_instruction = (
            "You are a professional recruiting evaluator. Your job is to analyze a candidate's response "
            "to an interview question and score it fairly and objectively across relevant criteria. "
            "Do not give excessively high scores (e.g., 90+) unless the answer is exceptional. "
            "Identify if behavioral answers follow the STAR (Situation, Task, Action, Result) structure."
        )

        prompt = f"""
        Evaluate the candidate's answer to the following question.
        
        Role Track: {session.role_track}
        Interview Stage: {candidate_turn.stage}
        Question Asked: "{ai_question}"
        Primary Target Dimension: {target_dimension_hint}
        
        Candidate's Answer:
        "{candidate_turn.content}"
        
        Evaluate the response on the following dimensions (select 2-3 most relevant to the question type):
        - knowledge (technical depth, correctness)
        - confidence (pacing, tone, certainty)
        - communication (clarity, structure, conciseness)
        - problem_solving (analytical thinking, structured approach)
        - leadership (ownership, taking initiative)
        - culture_fit (alignment with mission and values)
        - adaptability (handling change, learning from failure)
        - technical_skill (tool expertise, coding concepts)
        
        Also, check for STAR method structural completeness (Situation, Task, Action, Result) if the question was behavioral:
        - situation_provided: true/false
        - task_provided: true/false
        - action_provided: true/false
        - result_provided: true/false
        - star_critique: Short suggestion on how they could have structured their STAR response better.
        
        Return your evaluation as a JSON object:
        {{
            "scores": [
                {{
                    "dimension": "dimension_name",
                    "score": float_value_0_to_100,
                    "rationale": "Why this score was awarded."
                }}
            ],
            "star_evaluation": {{
                "is_behavioral": true/false,
                "structure": {{
                    "situation": true/false,
                    "task": true/false,
                    "action": true/false,
                    "result": true/false
                }},
                "critique": "STAR feedback string"
            }}
        }}
        """

        evaluation = LLMProvider.generate_json(prompt, system_instruction=system_instruction)
        
        # Save scores to DB
        saved_scores = []
        for s in evaluation.get("scores", []):
            score_obj = TurnScore(
                turn_id=candidate_turn.id,
                dimension=s.get("dimension"),
                score=s.get("score", 70.0),
                rationale=s.get("rationale", "")
            )
            db.add(score_obj)
            saved_scores.append(score_obj)
            
        # Save STAR evaluation flags into the turn's engine_meta
        meta = dict(candidate_turn.engine_meta or {})
        meta["star_evaluation"] = evaluation.get("star_evaluation", {})
        candidate_turn.engine_meta = meta
        
        db.commit()
        return saved_scores
