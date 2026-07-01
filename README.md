---
title: Eval API
emoji: 🎙️
colorFrom: gray
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# EVAL. — AI Recruitment & Interview Platform

EVAL. is a production-ready, world-class AI Recruitment & Interview Platform. It conducts realistic, adaptive candidate interviews matching the style and rigor of top-tier organizations (Google, Microsoft, Amazon, Meta, OpenAI, etc.). 

The platform parses candidate resumes, analyzes job descriptions, crawls company websites, constructs a knowledge graph of candidate suitability, conducts adaptive mock interviews with dynamic follow-up questioning, evaluates answers in real-time using recruiter-style rubrics (including STAR method check), and compiles detailed executive feedback and study plans.

---

## 1. System Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Frontend — Next.js 15 / React / TypeScript"]
        UI_Dash[Candidate Dashboard]
        UI_Upload[Resume & JD Dropzones]
        UI_Room[Mock Interview Room]
        UI_Report[Executive Report & Study Plan]
        UI_Coach[AI Coach STAR Replay Room]
        UI_Admin[System Analytics Console]
    end

    subgraph Edge["Edge / API Gateway"]
        Auth[Auth/Clerk Integration Stub]
        CORS[CORS Policy & Rate Limiter]
    end

    subgraph Backend["Backend — FastAPI (Python)"]
        API[REST Routing & Middleware]
        ParseSvc[Resume Parsing Service - PyPDF + LLM]
        ResearchSvc[Company Research Service - Web Scraper + LLM]
        ProfileSvc[Profile Knowledge Graph Synthesizer]
        Engine[Interview State Machine Orchestrator]
        Scoring[Real-Time Rubric Scorer]
        Report[Executive Report Generator]
        Coach[Career Coach Replay Engine]
        Voice[Voice Gateway Interface - TextOnly Stub]
    end

    subgraph AI["AI Layer"]
        LLM[Gemini 1.5 Flash / Claude 3.5 Sonnet / GPT-4o]
        Embedding[Gemini text-embedding-004 / OpenAI text-embedding-3]
    end

    subgraph Storage["Data Store Layer"]
        DB[(SQLite / PostgreSQL Database)]
        VectorDB[(Local Cosine Similarity Index / pgvector)]
    end

    Client --> Edge --> API
    API --> ParseSvc & ResearchSvc & ProfileSvc & Engine & Scoring & Report & Coach
    Engine --> Voice
    ParseSvc & ResearchSvc & ProfileSvc & Engine & Scoring & Report & Coach --> LLM & Embedding
    API --> DB & VectorDB
```

---

## 2. Database Schema & ER Diagram

The platform utilizes a hybrid data layer designed for transparent portability:
- **SQLite** for zero-dependency local development (storing embeddings as serialized arrays in standard tables, performing cosine similarity calculations in Python).
- **PostgreSQL + pgvector** for production deployments.

```mermaid
erDiagram
    USERS ||--o{ RESUMES : owns
    USERS ||--o{ JOB_DESCRIPTIONS : saves
    USERS ||--o{ INTERVIEW_SESSIONS : takes
    USERS ||--o{ CANDIDATE_PROFILES : has

    RESUMES ||--o{ RESUME_ENTITIES : contains
    JOB_DESCRIPTIONS ||--o{ JD_REQUIREMENTS : contains
    COMPANIES ||--o{ JOB_DESCRIPTIONS : posts
    COMPANIES ||--o{ COMPANY_RESEARCH : has

    CANDIDATE_PROFILES ||--o{ INTERVIEW_SESSIONS : informs
    CANDIDATE_PROFILES }o--|| RESUMES : derived_from
    CANDIDATE_PROFILES }o--|| JOB_DESCRIPTIONS : targets

    INTERVIEW_SESSIONS ||--o{ INTERVIEW_TURNS : consists_of
    INTERVIEW_SESSIONS ||--|| INTERVIEW_REPORTS : produces
    INTERVIEW_TURNS ||--o{ TURN_SCORES : scored_by
    INTERVIEW_TURNS }o--o| QUESTION_BANK : may_reference
    QUESTION_BANK ||--o{ QUESTION_EMBEDDINGS : has

    USERS {
        string id PK
        string email
        string full_name
        string role "candidate | admin"
        datetime created_at
    }
    RESUMES {
        string id PK
        string user_id FK
        string file_url
        string file_type "pdf | txt"
        string raw_text
        json parsed_json
        int version
        datetime created_at
    }
    RESUME_ENTITIES {
        string id PK
        string resume_id FK
        string category "education | experience | project | skill"
        json content
        json embedding "serialized float vector"
    }
    COMPANIES {
        string id PK
        string name
        string industry
        json metadata_json
        datetime updated_at
    }
    COMPANY_RESEARCH {
        string id PK
        string company_id FK
        string category "mission | values | principles | interview | news"
        string content
        string source_url
        datetime fetched_at
    }
    JOB_DESCRIPTIONS {
        string id PK
        string user_id FK
        string company_id FK
        string source "text"
        string raw_text
        json parsed_json
        string role_title
        string seniority
        datetime created_at
    }
    JD_REQUIREMENTS {
        string id PK
        string jd_id FK
        string type "required_skill | preferred_skill | responsibility"
        string value
        json embedding "serialized float vector"
    }
    CANDIDATE_PROFILES {
        string id PK
        string user_id FK
        string resume_id FK
        string jd_id FK
        string company_id FK
        json knowledge_graph
        datetime created_at
    }
    INTERVIEW_SESSIONS {
        string id PK
        string user_id FK
        string candidate_profile_id FK
        string mode "text | voice"
        string status "in_progress | completed | abandoned"
        string role_track
        datetime started_at
        datetime ended_at
    }
    INTERVIEW_TURNS {
        string id PK
        string session_id FK
        int turn_index
        string speaker "ai | candidate"
        string stage
        string content
        string question_bank_id FK
        json engine_meta
        datetime created_at
    }
    QUESTION_BANK {
        string id PK
        string category
        string subcategory
        string text
        string difficulty "easy | medium | hard | expert"
        string role_track
        json tags
    }
    QUESTION_EMBEDDINGS {
        string id PK
        string question_id FK
        json embedding "serialized float vector"
    }
    TURN_SCORES {
        string id PK
        string turn_id FK
        string dimension
        float score
        string rationale
    }
    INTERVIEW_REPORTS {
        string id PK
        string session_id FK
        string recommendation
        json dimension_scores
        json strengths
        json weaknesses
        json knowledge_gaps
        json suggested_improvements
        json study_plan
        float readiness_score
        datetime generated_at
    }
```

---

## 3. Folder Structure

```
ai-recruitment-platform/
├── package.json              # Concurrently run dev servers config
├── run.ps1                   # Win PowerShell orchestration script
├── apps/
│   ├── api/                  # FastAPI backend
│   │   ├── requirements.txt  # Python packages
│   │   ├── app/
│   │   │   ├── main.py       # API entrypoint, CORS & startup
│   │   │   ├── api/          # Route handlers
│   │   │   │   ├── admin.py
│   │   │   │   ├── interviews.py
│   │   │   │   ├── job_descriptions.py
│   │   │   │   ├── reports.py
│   │   │   │   └── resumes.py
│   │   │   ├── db/           # Connection & vector store
│   │   │   │   ├── database.py
│   │   │   │   └── vector_store.py
│   │   │   ├── models/       # SQLAlchemy schemas
│   │   │   │   └── models.py
│   │   │   ├── schemas/      # Pydantic schemas
│   │   │   │   └── schemas.py
│   │   │   ├── ai/           # LLM Providers & Fallbacks
│   │   │   │   └── providers.py
│   │   │   └── services/     # Business logic layers
│   │   │       ├── parsing.py
│   │   │       ├── research.py
│   │   │       ├── profile.py
│   │   │       ├── scoring.py
│   │   │       ├── reporting.py
│   │   │       ├── coaching.py
│   │   │       ├── voice/
│   │   │       │   └── gateway.py
│   │   │       └── interview_engine/
│   │   │           └── engine.py
│   │   └── tests/            # Test suite
│   │       └── test_interview.py
│   └── web/                  # Next.js 15 frontend
│       ├── package.json
│       ├── tailwind.config.ts
│       └── src/
│           └── app/
│               ├── globals.css
│               ├── layout.tsx
│               └── page.tsx  # Dashboard & Interview room UI
```

---

## 4. Local Setup and Running

Ensure you have **Python 3.14+** and **Node 24+** installed.

### Step 1: Clone and Configuration
Configure the environment variables in a terminal session or `.env` file (if you have them, otherwise the application will run in **offline fallback mode** using precompiled schemas and mock reasoning results to make development easier):
```bash
# Set either Gemini (Default) or OpenAI / Anthropic key
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"
```

### Step 2: Auto Setup using PowerShell
From the project root directory, run the PowerShell installer:
```powershell
# Run setup script
.\run.ps1 -Action setup
```
This command:
1. Installs root dependencies (`concurrently`).
2. Creates a Python virtual environment in `apps/api/.venv` and installs `requirements.txt`.
3. Installs Next.js dependencies (`lucide-react`, etc.) in `apps/web/node_modules`.

### Step 3: Run Development Servers
Start both servers concurrently:
```powershell
.\run.ps1 -Action dev
```
- **Next.js Web Frontend**: http://localhost:3000
- **FastAPI Backend API**: http://localhost:8000
- **Interactive OpenAPI Docs**: http://localhost:8000/docs

---

## 5. API Documentation

### Resumes Router
- `POST /api/resumes/upload`
  - Upload PDF/TXT resume. Resolves or registers user.
  - Body: Form data (`email`, `full_name`, `file`)
  - Response: `ResumeResponse`
- `GET /api/resumes/{resume_id}`
  - Retrieve parsed resume entities and JSON layout.

### Job Descriptions Router
- `POST /api/job-descriptions/analyze`
  - Research target company name, parse JD criteria, store vectors.
  - Body: JSON `JdRequest`
  - Response: `JdResponse`

### Interviews Router
- `POST /api/interviews/session`
  - Compile profile knowledge graph and start adaptive interview.
  - Body: JSON `InterviewStartRequest`
  - Response: `InterviewSessionResponse`
- `POST /api/interviews/session/{session_id}/answer`
  - Submit candidate response. Returns next AI question. Triggers background scoring tasks.
  - Body: JSON `AnswerRequest`
  - Response: Turn-transition meta dictionary.
- `GET /api/interviews/session/{session_id}/history`
  - Get complete sorted transcript.

### Reports Router
- `GET /api/reports/session/{session_id}`
  - Fetch compiled executive evaluation report.
- `GET /api/reports/turn/{turn_id}/coach`
  - Fetch coach critique, structural warnings, and STAR rewrite for a specific turn.

### Admin Router
- `GET /api/admin/analytics`
  - Fetch total users, session distribution, and activity queue.
- `POST /api/admin/seed-questions`
  - Seed the database question bank (called automatically on mount).

---

## 6. Testing Strategy

We test models, databases, routing, scoring pipelines, and state machine transitions using `pytest`.

### Run tests:
```bash
cd apps/api
.venv\Scripts\activate
pytest tests/
```
The test suite utilizes an in-memory SQLite database instance (`sqlite:///:memory:`) to verify:
1. User registration schema constraint.
2. Resume and JD relationships.
3. Turn-by-turn stage progression within `InterviewEngine` (Greeting -> Answer -> Followup).
4. Run evaluation, validation scoring, and final report generation.

---

## 7. Security Checklist

- [ ] **Data Isolation**: All operations filter records by `user_id` to prevent cross-candidate data leakages.
- [ ] **Input Sanitization**: PDF parser filters out malicious code strings prior to loading them into LLM system prompts.
- [ ] **CORS Settings**: Backend CORS middleware blocks unauthorized clients (restricted in production configuration).
- [ ] **Environment Isolation**: Database credentials, tokens, and LLM API keys are loaded strictly from system variables.
- [ ] **Secure file handling**: PDF reader limits chunk sizes, preventing DoS exhaustion on memory buffers.

---

## 8. Deployment Guide

### Backend (Dockerized on Fly.io/Railway)
1. Add a `Dockerfile` under `apps/api` specifying a python environment:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
   ```
2. Link target environment secrets (`DATABASE_URL` pointing to PostgreSQL with pgvector, API keys).
3. Push to Fly.io or Render.

### Frontend (Vercel)
1. Set the Next.js target environment variable `NEXT_PUBLIC_API_URL` pointing to your deployed API server.
2. Connect root workspace to Vercel repository, set root directory to `apps/web`.
3. Deploy!
