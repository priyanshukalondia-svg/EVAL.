# apps/api/app/services/profile.py
from sqlalchemy.orm import Session
from app.models.models import Resume, JobDescription, Company, CandidateProfile
from app.ai.providers import LLMProvider

class CandidateProfileService:
    @classmethod
    def build_candidate_profile(
        cls, db: Session, user_id: str, resume_id: str, jd_id: str, company_id: str = None
    ) -> CandidateProfile:
        """
        Synthesize resume, JD, and company research into a knowledge graph.
        Analyzes skill gaps, project claims, and maps cultural points.
        """
        # Fetch components
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
        
        company_name = "Target Company"
        company_details = ""
        
        if company_id:
            company = db.query(Company).filter(Company.id == company_id).first()
            if company:
                company_name = company.name
                company_details = f"Company: {company.name}\n"
                for entry in company.research_entries:
                    company_details += f"- {entry.category.upper()}: {entry.content[:300]}...\n"

        if not resume or not jd:
            raise ValueError("Resume and Job Description are required to build a candidate profile.")

        # Ask LLM to compile knowledge graph
        system_instruction = (
            "You are a Senior Technical Recruiter and Talent Architect. Your task is to perform "
            "deep matching analysis and output a structured candidate profile knowledge graph."
        )
        
        prompt = f"""
        Conduct a matching analysis between the candidate's resume and the job description.
        If company information is available, map how the candidate's projects align with the company's principles.
        
        Candidate Resume:
        {resume.raw_text}
        
        Job Description:
        {jd.raw_text}
        
        Company Research:
        {company_details}
        
        Generate a JSON knowledge graph with the following structure:
        - match_percentage: Integer (0-100) representing overall suitability
        - skills_matched: List of strings (skills appearing in both resume and JD)
        - skills_missing: List of strings (skills in JD missing or weak in resume)
        - cultural_alignment: A concise paragraph outlining culture fit and alignment with principles
        - experience_relevance: Evaluation of job titles, duration, and seniority match
        - project_deep_dives: List of {{project_name, claim, suggestion_for_probing}} where 'claim' represents an impressive resume bullet, and 'suggestion_for_probing' is what the interviewer should ask to verify authenticity.
        - recommended_focus_areas: List of {{topic, reason, suggested_questions (list of strings)}} targeting potential weak spots, missing experiences, or performance claims.
        """
        
        knowledge_graph = LLMProvider.generate_json(prompt, system_instruction=system_instruction)
        
        # Save to DB
        profile = CandidateProfile(
            user_id=user_id,
            resume_id=resume_id,
            jd_id=jd_id,
            company_id=company_id,
            knowledge_graph=knowledge_graph
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        return profile
