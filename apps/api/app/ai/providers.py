# apps/api/app/ai/providers.py
import os
import json
import re
from typing import Dict, Any, Optional, List

class LLMProvider:
    @classmethod
    def generate_text(cls, prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.7) -> str:
        """
        Generate text response from an LLM.
        Supports Gemini (default), Claude, and OpenAI.
        Falls back gracefully if keys are missing.
        """
        # Try Gemini API (using new google-genai or legacy google-generativeai)
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_api_key)
                
                # Combine system instructions and prompt if using models that don't support system_instruction directly
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config={"temperature": temperature}
                )
                
                # Use system_instruction if provided
                if system_instruction:
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        generation_config={"temperature": temperature},
                        system_instruction=system_instruction
                    )
                    
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Gemini LLM call failed: {e}. Trying OpenAI...")

        # Try OpenAI API
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_api_key)
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=temperature
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI LLM call failed: {e}.")

        # Try Anthropic API
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_api_key)
                messages = [{"role": "user", "content": prompt}]
                
                kwargs = {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 4000,
                    "temperature": temperature,
                    "messages": messages
                }
                if system_instruction:
                    kwargs["system"] = system_instruction
                    
                response = client.messages.create(**kwargs)
                return response.content[0].text
            except Exception as e:
                print(f"Anthropic LLM call failed: {e}.")

        # Static Offline Fallback mock responses (ensures local app works without active internet/API keys)
        return cls._get_mock_fallback_response(prompt)

    @classmethod
    def generate_json(cls, prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Generate a JSON response from an LLM.
        Enforces JSON output and parses it safely.
        """
        json_instruction = (
            "\n\nCRITICAL: Your response MUST be a single, valid JSON object. "
            "Do not include any introductory or concluding text. "
            "Do not use markdown code block wrappers (like ```json ... ```) in your output, "
            "just return raw JSON."
        )
        
        full_system = (system_instruction or "") + json_instruction
        
        # We can also add JSON formatting hint to the prompt
        full_prompt = prompt
        
        raw_response = cls.generate_text(full_prompt, system_instruction=full_system, temperature=temperature)
        
        # Clean response text in case markdown wrappers were included anyway
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith("```"):
            # Remove ```json and ```
            cleaned_response = re.sub(r"^```(?:json)?\n", "", cleaned_response)
            cleaned_response = re.sub(r"\n```$", "", cleaned_response)
            cleaned_response = cleaned_response.strip()
            
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM JSON output. Error: {e}. Raw response: {raw_response}")
            # Attempt regex extraction of anything between { }
            match = re.search(r"(\{.*\})", cleaned_response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            # Return a default fallback dict
            return {"error": "Failed to parse LLM response", "raw_content": raw_response}

    @staticmethod
    def _get_mock_fallback_response(prompt: str) -> str:
        """Fallback mock responses based on prompt keywords to keep local dev functional offline."""
        prompt_lower = prompt.lower()
        if "report" in prompt_lower or "coaching" in prompt_lower or "synthesis" in prompt_lower or "committee" in prompt_lower:
            return json.dumps({
                "recommendation": "hire",
                "readiness_score": 82.0,
                "dimension_scores": {"knowledge": 85, "communication": 90, "problem_solving": 80, "leadership": 75},
                "strengths": ["Clear articulation of tech concepts", "Strong fundamentals in SQL"],
                "weaknesses": ["Needs more detail in STAR results section"],
                "knowledge_gaps": ["No direct experience with large-scale pub/sub architectures"],
                "suggested_improvements": ["Focus on outlining concrete metrics for achievements"],
                "study_plan": [{"topic": "System Design: Scaling Databases", "resources": ["Designing Data-Intensive Applications"]}],
                "star_critique": "Your answer was good but lacked a clear 'Result' metric. You mentioned you 'improved dashboard speed' but didn't quantify it."
            })
        elif "parse" in prompt_lower and "resume" in prompt_lower:
            return json.dumps({
                "personal_info": {"name": "Jane Candidate", "email": "jane@example.com", "phone": "123-456-7890"},
                "education": [{"degree": "B.S. Computer Science", "school": "State University", "grad_year": "2024"}],
                "experience": [{"title": "Software Engineer Intern", "company": "Tech Corp", "duration": "3 months", "description": "Developed features using React and Python."}],
                "projects": [{"name": "E-Commerce Platform", "description": "Built a modular shopping cart app in Node.js."}],
                "skills": ["Python", "JavaScript", "React", "FastAPI", "SQL"],
                "achievements": ["Dean's List 2022-2024"]
            })
        elif "job" in prompt_lower and "description" in prompt_lower:
            return json.dumps({
                "role_title": "Full Stack Developer",
                "seniority": "Junior/Mid",
                "required_skills": ["React", "Node.js", "PostgreSQL", "TypeScript"],
                "preferred_skills": ["Docker", "AWS", "Python"],
                "responsibilities": ["Build responsive UI components", "Design database schemas", "Optimize APIs"],
                "company_expectations": ["Collaborative team player", "Enthusiasm for clean code"]
            })
        elif "research" in prompt_lower or "company" in prompt_lower:
            return json.dumps({
                "name": "Google",
                "industry": "Technology",
                "mission": "To organize the world's information and make it universally accessible and useful.",
                "values": ["Focus on the user", "Fast is better than slow", "Democracy on the web works"],
                "interview_process": "Typically 1 recruiter screen, 1 technical screen, and 4-5 on-site loops focusing on coding, system design, and Googlyness.",
                "recent_news": "Accelerating research in artificial intelligence and quantum computing."
            })
        elif "interview_engine" in prompt_lower or "next" in prompt_lower:
            return json.dumps({
                "action": "new_question",
                "question": "Can you walk me through a complex coding project that you are particularly proud of? What was the architecture and why did you choose it?",
                "difficulty": "medium",
                "target_dimension": "knowledge",
                "rationale": "Transitioning from greeting to projects discussion."
            })
        elif "score" in prompt_lower or "scoring" in prompt_lower:
            return json.dumps({
                "scores": [
                    {"dimension": "knowledge", "score": 85.0, "rationale": "Demonstrates clear understanding of backend architecture and databases."},
                    {"dimension": "communication", "score": 90.0, "rationale": "Very clear, structured answers with good pacing."}
                ]
            })
        
        return "I understand your response. Let's proceed with the next step of the interview process. Could you elaborate on your experience?"
