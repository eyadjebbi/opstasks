FROM node:22-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app/ ./app/
COPY --from=frontend-builder /frontend/dist ./frontend/

ENV DATABASE_URL=sqlite:////data/opstasks.db
ENV FRONTEND_DIR=/app/frontend
ENV ENABLE_DEMO_FAULTS=true
ENV DEMO_SLOW_DELAY_SECONDS=3

EXPOSE 8000
CMD ["uvicorn", "app.localstack_main:app", "--host", "0.0.0.0", "--port", "8000"]
