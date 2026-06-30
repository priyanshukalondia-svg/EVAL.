# apps/api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.api import resumes, job_descriptions, interviews, reports, admin

app = FastAPI(
    title="AI Recruitment & Interview Platform API",
    description="Backend API for managing resumes, job descriptions, adaptive interviews, scoring, and coaching reports.",
    version="1.0.0"
)

# Enable CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database tables on application startup
@app.on_event("startup")
def on_startup():
    print("Initializing Database tables...")
    init_db()
    print("Database initialization complete.")

# Register API Routers
app.include_router(resumes.router)
app.include_router(job_descriptions.router)
app.include_router(interviews.router)
app.include_router(reports.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AI Recruitment & Interview Platform API",
        "documentation": "/docs"
    }
