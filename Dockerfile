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

# 时区统一为东八区，保证 date.today() / datetime.now() 与业务日期一致
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Shanghai

COPY backend/requirements.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} --timeout 120 --retries 5 -r requirements.txt

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
