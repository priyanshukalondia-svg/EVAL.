# apps/api/app/services/research.py
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Company, CompanyResearch
from app.ai.providers import LLMProvider

class CompanyResearchService:
    @staticmethod
    def search_web(query: str, max_results: int = 4) -> str:
        """Search the web for a query using DuckDuckGo. Falls back to empty string on error."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                snippets = []
                for idx, r in enumerate(results):
                    snippets.append(f"Source [{idx+1}]: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
                return "\n".join(snippets)
        except Exception as e:
            print(f"DuckDuckGo search error for query '{query}': {e}")
            return ""

    @classmethod
    def research_company(cls, db: Session, company_name: str) -> Company:
        """Research a company using web queries, summarize with LLM, and cache in DB."""
        # 1. Check if company already researched
        existing_company = db.query(Company).filter(Company.name.ilike(company_name)).first()
        if existing_company:
            # Check if research is fresh (e.g. less than 7 days old)
            # For this MVP, we return it directly if it exists.
            return existing_company
            
        # 2. Gather web content
        queries = {
            "mission": f"{company_name} company mission values culture",
            "leadership": f"{company_name} leadership principles",
            "process": f"{company_name} interview process glassdoor",
            "news": f"{company_name} recent news business model products"
        }
        
        web_content = ""
        for key, q in queries.items():
            snippets = cls.search_web(q)
            if snippets:
                web_content += f"\n--- WEB SEARCH RESULTS FOR: {key.upper()} ---\n{snippets}\n"
                
        # 3. Use LLM to summarize and structure the research
        system_instruction = (
            f"You are an expert corporate researcher. Summarize public information about '{company_name}' "
            "into clear, factual descriptions of their Mission, Values, Leadership Principles, Interview Process, "
            "Recent News, Competitors, and Business Model. Use only public information. If no web content is available, "
            "rely on your baseline knowledge of this company."
        )
        
        prompt = f"""
        Analyze the following web research content (if any) and compile a structured report for '{company_name}'.
        Web Content:
        {web_content}
        
        Provide your report as a JSON object containing keys:
        - name: The canonical name of the company
        - industry: Main industry category
        - mission: A summary of their mission and purpose
        - values: Key corporate values
        - leadership_principles: Structured leadership principles or core guidelines (e.g., customer obsession, ownership)
        - interview_process: Typical rounds and expectations (e.g., screening, coding, behavioral)
        - news: Recent news highlights
        - competitors: Main competitors in the market
        - business_model: How they make money and core products
        """
        
        research_json = LLMProvider.generate_json(prompt, system_instruction=system_instruction)
        
        # 4. Save to Database
        company = Company(
            name=research_json.get("name", company_name),
            industry=research_json.get("industry", "Unknown"),
            metadata_json={
                "competitors": research_json.get("competitors", []),
                "business_model": research_json.get("business_model", "")
            }
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        
        # Save research sub-entries
        categories = ["mission", "values", "leadership_principles", "interview_process", "news"]
        for cat in categories:
            content = research_json.get(cat)
            if isinstance(content, list):
                content = "\n".join([f"- {item}" for item in content])
            elif isinstance(content, dict):
                content = "\n".join([f"{k}: {v}" for k, v in content.items()])
                
            if content:
                db.add(CompanyResearch(
                    company_id=company.id,
                    category=cat,
                    content=str(content),
                    source_url="Web Search Summary"
                ))
                
        db.commit()
        return company
