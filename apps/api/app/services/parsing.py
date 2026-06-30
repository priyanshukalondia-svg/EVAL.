# apps/api/app/services/parsing.py
import io
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from pypdf import PdfReader
from app.models.models import Resume, ResumeEntity
from app.db.vector_store import VectorStore
from app.ai.providers import LLMProvider

class ResumeParsingService:
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extract plain text from PDF bytes."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            raise ValueError("Failed to parse PDF file.")

    @classmethod
    def parse_resume_to_json(cls, text: str) -> Dict[str, Any]:
        """Use LLM to parse raw resume text into structured JSON."""
        system_instruction = (
            "You are a professional resume parsing engine. Your job is to extract raw resume text "
            "into a clean, structured JSON format. "
            "Do not truncate or omit experience. Extract as many detailed descriptions as possible."
        )
        
        prompt = f"""
        Extract the following structured sections from this resume text:
        1. personal_info: {{name, email, phone, location, linkedin, github}}
        2. education: list of {{degree, school, field_of_study, grad_year, gpa}}
        3. experience: list of {{title, company, location, duration, description_bullets (list of strings), technologies (list of strings)}}
        4. projects: list of {{name, description, technologies (list of strings), url}}
        5. skills: list of strings (technical skills, tools, languages)
        6. achievements: list of strings
        7. certifications: list of strings

        Resume Text:
        {text}
        """
        
        return LLMProvider.generate_json(prompt, system_instruction=system_instruction)

    @classmethod
    def process_and_save_resume(
        cls, db: Session, user_id: str, file_name: str, file_bytes: bytes, file_type: str
    ) -> Resume:
        """Parses the uploaded file, extracts entities, computes embeddings, and saves to database."""
        # 1. Extract text
        if file_type == "pdf":
            raw_text = cls.extract_text_from_pdf(file_bytes)
        else:
            # Handle txt/docx (as text)
            raw_text = file_bytes.decode("utf-8", errors="ignore")
            
        # 2. Parse text to JSON
        parsed_json = cls.parse_resume_to_json(raw_text)
        
        # 3. Create Resume record
        resume = Resume(
            user_id=user_id,
            file_url=file_name,
            file_type=file_type,
            raw_text=raw_text,
            parsed_json=parsed_json,
            version=1
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        
        # 4. Extract and embed individual entities for Vector search
        cls._create_resume_entities(db, resume.id, parsed_json)
        
        return resume

    @classmethod
    def _create_resume_entities(cls, db: Session, resume_id: str, parsed_json: Dict[str, Any]):
        """Helper to create and embed ResumeEntity records for each item in the parsed resume."""
        # Process education
        for edu in parsed_json.get("education", []):
            content_str = f"Education: {edu.get('degree')} in {edu.get('field_of_study')} from {edu.get('school')} (Graduated: {edu.get('grad_year')})"
            embedding = VectorStore.get_embedding(content_str)
            db.add(ResumeEntity(
                resume_id=resume_id,
                category="education",
                content=edu,
                embedding=embedding
            ))
            
        # Process experience
        for exp in parsed_json.get("experience", []):
            bullets = " ".join(exp.get("description_bullets", []))
            content_str = f"Experience: {exp.get('title')} at {exp.get('company')} during {exp.get('duration')}. Details: {bullets}"
            embedding = VectorStore.get_embedding(content_str)
            db.add(ResumeEntity(
                resume_id=resume_id,
                category="experience",
                content=exp,
                embedding=embedding
            ))
            
        # Process projects
        for proj in parsed_json.get("projects", []):
            content_str = f"Project: {proj.get('name')}. Description: {proj.get('description')}. Technologies: {', '.join(proj.get('technologies', []))}"
            embedding = VectorStore.get_embedding(content_str)
            db.add(ResumeEntity(
                resume_id=resume_id,
                category="project",
                content=proj,
                embedding=embedding
            ))
            
        # Process skills (bulk or individual)
        skills = parsed_json.get("skills", [])
        if skills:
            content_str = f"Skills: {', '.join(skills)}"
            embedding = VectorStore.get_embedding(content_str)
            db.add(ResumeEntity(
                resume_id=resume_id,
                category="skill",
                content={"skills": skills},
                embedding=embedding
            ))
            
        db.commit()
