# apps/api/app/db/vector_store.py
import os
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import ResumeEntity, JdRequirement, QuestionEmbedding, QuestionBank

class VectorStore:
    @staticmethod
    def get_embedding(text: str) -> List[float]:
        """
        Generate embedding for a given text.
        Supports Gemini (default) and OpenAI embedding models.
        Falls back to a deterministic dummy vector if no API keys are found.
        """
        # Try Gemini API (using google-genai or google-generativeai SDK)
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                # We can use google.generativeai or the new google-genai client.
                # Let's import inside to handle potential import/SDK changes.
                import google.generativeai as genai
                genai.configure(api_key=gemini_api_key)
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                return response["embedding"]
            except Exception as e:
                print(f"Gemini embedding failed: {e}. Trying OpenAI...")
                
        # Try OpenAI API
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_api_key)
                response = client.embeddings.create(
                    input=[text],
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"OpenAI embedding failed: {e}.")

        # Deterministic dummy fallback vector (length 1536) for development/offline
        # So the application never crashes even if keys are missing
        dummy_vector = [0.0] * 1536
        # Generate some deterministic values based on characters in text
        for idx, char in enumerate(text[:300]):
            dummy_vector[idx % 1536] += ord(char) / 1000.0
            
        # Normalize the vector so it has norm 1.0 (improves cosine similarity matching)
        norm = math.sqrt(sum(x*x for x in dummy_vector))
        if norm > 0:
            dummy_vector = [x / norm for x in dummy_vector]
            
        return dummy_vector

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute the cosine similarity between two vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(x * y for x, y in zip(v1, v2))
        norm_v1 = math.sqrt(sum(x * x for x in v1))
        norm_v2 = math.sqrt(sum(x * x for x in v2))
        if norm_v1 == 0.0 or norm_v2 == 0.0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2)

    @classmethod
    def search_resume_entities(
        cls, db: Session, resume_id: str, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search resume entities similar to a query."""
        query_vector = cls.get_embedding(query)
        entities = db.query(ResumeEntity).filter(ResumeEntity.resume_id == resume_id).all()
        
        results = []
        for entity in entities:
            if entity.embedding:
                similarity = cls.cosine_similarity(query_vector, entity.embedding)
                results.append({"entity": entity, "similarity": similarity})
                
        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return [{"id": r["entity"].id, "category": r["entity"].category, "content": r["entity"].content, "similarity": r["similarity"]} for r in results[:limit]]

    @classmethod
    def search_jd_requirements(
        cls, db: Session, jd_id: str, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search job description requirements similar to a query."""
        query_vector = cls.get_embedding(query)
        requirements = db.query(JdRequirement).filter(JdRequirement.jd_id == jd_id).all()
        
        results = []
        for req in requirements:
            if req.embedding:
                similarity = cls.cosine_similarity(query_vector, req.embedding)
                results.append({"requirement": req, "similarity": similarity})
                
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return [{"id": r["requirement"].id, "type": r["requirement"].type, "value": r["requirement"].value, "similarity": r["similarity"]} for r in results[:limit]]

    @classmethod
    def search_question_bank(
        cls, db: Session, role_track: str, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search the question bank for questions relevant to a query/topic."""
        query_vector = cls.get_embedding(query)
        embeddings = db.query(QuestionEmbedding).join(QuestionBank).filter(QuestionBank.role_track == role_track).all()
        
        results = []
        for emb in embeddings:
            similarity = cls.cosine_similarity(query_vector, emb.embedding)
            results.append({"question": emb.question, "similarity": similarity})
            
        results.sort(key=lambda x: x["similarity"], reverse=True)
        # Deduplicate by question text
        seen = set()
        dedup_results = []
        for r in results:
            q = r["question"]
            if q.id not in seen:
                seen.add(q.id)
                dedup_results.append({"question": q, "similarity": r["similarity"]})
                
        return dedup_results[:limit]
