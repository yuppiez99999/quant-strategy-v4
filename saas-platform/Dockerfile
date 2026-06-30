# ---- Frontend Build Stage ----
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY package.json package-lock.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# ---- Backend Stage ----
FROM python:3.11-slim AS backend
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./static

# Copy quant strategy modules
COPY ../quant_modules/ ./quant_modules/
COPY ../engine/ ./engine/
COPY ../utils/ ./utils/
COPY ../config/ ./config/

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
