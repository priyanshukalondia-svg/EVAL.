# Dockerfile (Root directory)
# Configured specifically for Hugging Face Spaces (100% Free & Card-Free hosting)

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependencies and install
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI backend code into container
COPY apps/api/ .

# Hugging Face Spaces binds containers to port 7860 by default
EXPOSE 7860

# Start FastAPI app on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
