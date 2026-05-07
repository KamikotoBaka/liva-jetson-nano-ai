# --- STAGE 1: Frontend bauen ---
FROM node:18-slim AS frontend-build
WORKDIR /app/frontend
COPY vite-project/package*.json ./
RUN npm install
COPY vite-project/ ./
# Erzeugt den 'dist' oder 'build' Ordner
RUN npm run build

# --- STAGE 2: Backend & Ausführung ---
FROM python:3.10-slim
WORKDIR /app

# System-Tools für Audio und Netzwerk
RUN apt-get update && apt-get install -y ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*

# Python Libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den gesamten Projekt-Ordner kopieren
COPY . .

# Den fertigen React-Build in einen Ordner schieben, den FastAPI kennt
# (Stelle sicher, dass dein FastAPI 'static' nutzt, wie im vorigen Schritt erklärt)
COPY --from=frontend-build /app/frontend/dist /app/static

# Der Startbefehl für den Jetson (Linux-Syntax)
# Wir nutzen 0.0.0.0, damit der Container erreichbar ist
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]