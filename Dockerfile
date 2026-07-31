# -- Stage 1: Build frontend --
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# -- Stage 2: Run backend --
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /frontend/dist ./static

RUN mkdir -p /app/data

# Copy pre-seeded database into the image
COPY data/tutoring.db /app/data/tutoring.db

ENV TUTORING_DB=/app/data/tutoring.db
ENV TUTORING_HOST=0.0.0.0
ENV TUTORING_PORT=5000
ENV DOCKER_ENV=1

EXPOSE 5000

CMD ["python", "launcher.py"]
