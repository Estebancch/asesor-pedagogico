from __future__ import annotations

import logging
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import obtener_ajustes
from .db import Base, SesionLocal, engine
from .models import Cohorte, Config, Evaluacion, Usuario
from .routers import academico, admin, analitica, auth, entregas
from .security import hash_password
from .services.sandbox import proteger_proceso_servidor

log = logging.getLogger("asesor")


def inicializar() -> None:
    """Crea tablas, el administrador inicial y las dos cohortes del curso."""
    aj = obtener_ajustes()
    Base.metadata.create_all(engine)
    with SesionLocal() as db:
        if not db.scalars(select(Usuario).where(Usuario.rol == "admin")).first():
            clave = aj.admin_password
            if not clave:
                # Sin ADMIN_PASSWORD: clave fija solo en desarrollo; aleatoria (visible una vez en el log) en producción.
                clave = "Cambiar1234" if aj.entorno != "produccion" else secrets.token_urlsafe(12) + "9a"
                log.warning("ADMIN_PASSWORD no está definida: se creó %s con la clave temporal «%s». Cámbiala.", aj.admin_email, clave)
            db.add(Usuario(nombre=aj.admin_nombre, email=aj.admin_email.lower(), password_hash=hash_password(clave), rol="admin"))
        if not db.scalars(select(Cohorte)).first():
            db.add_all([Cohorte(numero=1, nombre="Corte 1"), Cohorte(numero=2, nombre="Corte 2")])
        # Instalaciones anteriores usaban «cohorte» (el término del enunciado); la interfaz ahora dice «corte».
        for c in db.scalars(select(Cohorte)):
            if c.nombre == f"Cohorte {c.numero}":
                c.nombre = f"Corte {c.numero}"
        fila = db.get(Config, "proyecto")
        if fila and isinstance(fila.valor, dict):
            cambios = (("las cohortes 1 y 2", "los cortes 1 y 2"), ("las dos cohortes", "los dos cortes"))
            def corregir(v):
                if isinstance(v, str):
                    for viejo, nuevo in cambios:
                        v = v.replace(viejo, nuevo)
                    return v
                return [corregir(x) for x in v] if isinstance(v, list) else v
            nuevo = {k: corregir(v) for k, v in fila.valor.items()}
            if nuevo != fila.valor:
                fila.valor = nuevo
        # Evaluaciones que quedaron a medias por un reinicio del servidor
        for ev in db.scalars(select(Evaluacion).where(Evaluacion.estado.in_(("en_cola", "procesando")))):
            ev.estado, ev.progreso = "error", ""
            ev.error = "La evaluación se interrumpió por un reinicio del servidor. Vuelve a solicitarla."
        db.commit()
    from .seed import sembrar, sembrar_equipo
    sembrar_equipo()
    if aj.seed_demo:
        # En segundo plano: el servidor queda disponible mientras se generan los datos de demostración.
        threading.Thread(target=sembrar, name="seed-demo", daemon=True).start()


@asynccontextmanager
async def ciclo(app: FastAPI):
    proteger_proceso_servidor()
    inicializar()
    yield


app = FastAPI(title="Asesor Pedagógico Inteligente", version="1.0.0", lifespan=ciclo,
              description="API de evaluación, retroalimentación y fortalecimiento de competencias en IA.")

_aj = obtener_ajustes()
if _aj.cors_origenes:
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _aj.cors_origenes.split(",") if o.strip()],
                       allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.url.path.startswith("/api/") and "Cache-Control" not in resp.headers:
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(RequestValidationError)
async def error_validacion(_: Request, exc: RequestValidationError):
    errores = exc.errors()
    mensaje = "; ".join(str(e.get("msg", "")).replace("Value error, ", "") for e in errores[:3]) or "Datos no válidos."
    return JSONResponse({"detail": mensaje}, status_code=422)


for r in (auth.router, academico.router, entregas.router, analitica.router, admin.router):
    app.include_router(r)


@app.get("/api/salud", tags=["sistema"])
def salud():
    return {"estado": "ok"}


@app.api_route("/api/{resto:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_no_encontrada(resto: str):
    raise HTTPException(404, "Ruta de API no encontrada.")


# --- frontend compilado (SPA) -------------------------------------------------------------------
_dist = Path(_aj.frontend_dist)
if (_dist / "index.html").exists():
    if (_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def spa(ruta: str):
        archivo = (_dist / ruta).resolve()
        if ruta and archivo.is_file() and _dist.resolve() in archivo.parents:
            return FileResponse(archivo)
        return FileResponse(_dist / "index.html", headers={"Cache-Control": "no-cache"})
