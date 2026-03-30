FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /app/requirements.txt

COPY . /app

EXPOSE 8000

# Default: run the FastAPI backend. (docker-compose overrides this for Streamlit)
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]

