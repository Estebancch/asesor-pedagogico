# --- 1) Compila el frontend (React + Vite) -----------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2) Backend (FastAPI) que también sirve el frontend compilado -------------------------
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 ENTORNO=produccion
WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-sandbox.txt ./
ARG SANDBOX_EXTRAS=false
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ "$SANDBOX_EXTRAS" = "true" ]; then pip install --no-cache-dir -r requirements-sandbox.txt; fi
COPY backend/app ./app
COPY --from=web /web/dist /app/frontend/dist

# El servidor corre como root DENTRO del contenedor a propósito: así el sandbox puede
# bajar el código de los estudiantes al usuario `nobody`, que no puede leer los archivos
# ni el entorno del servidor. Ver docs/ARQUITECTURA.md, sección «Sandbox».
EXPOSE 8000
# Un solo proceso: las evaluaciones corren en hilos de fondo de este mismo proceso.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
