FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN mkdir -p /app/data

ENV TUTORING_DB=/app/data/tutoring.db
ENV TUTORING_HOST=0.0.0.0
ENV TUTORING_PORT=5000
ENV DOCKER_ENV=1

EXPOSE 5000

CMD ["python", "launcher.py"]
