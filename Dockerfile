# One container: Node builds the React app, Python serves it and the API with uvicorn.

# ---- frontend build
FROM node:22-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- API + static files
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# RapidOCR pulls in opencv-python, which needs these system libraries.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt
COPY backend/ backend/
COPY data/ data/
COPY --from=web /app/frontend/dist frontend/dist

RUN useradd --create-home app && mkdir -p /app/var && chown app /app/var
USER app
ENV DB_PATH=/app/var/udyam.db FRONTEND_DIST=/app/frontend/dist DATA_DIR=/app/data PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips '*'"]
