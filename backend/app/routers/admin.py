"""Presentación del proyecto, equipo, configuración de IA y estado del sistema."""
from __future__ import annotations

import hashlib
import platform

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, undefer

from ..config import MODELOS_POR_DEFECTO, URLS_POR_DEFECTO, obtener_ajustes
from ..db import obtener_db
from ..deps import auditar, docente_o_admin, solo_admin
from ..models import Archivo, Auditoria, Config, Entrega, Evaluacion, Integrante, Usuario
from ..services import ia as srv_ia
from ..services.ia import ErrorIA
from ..services.ia.base import esquema_plano

router = APIRouter(prefix="/api", tags=["proyecto y administración"])

PROYECTO_DEFECTO = {
    "titulo": "Asesor Pedagógico Inteligente",
    "lema": "Evaluación, retroalimentación y fortalecimiento de competencias en Inteligencia Artificial",
    "institucion": "Universidad de Manizales · Ingeniería de Sistemas y Telecomunicaciones · Profundización I: Inteligencia Artificial",
    "abstract": (
        "Asesor Pedagógico Inteligente es una plataforma web que ayuda a los estudiantes a autoevaluar y fortalecer las "
        "competencias adquiridas en los laboratorios de las cohortes 1 y 2 del curso de Inteligencia Artificial. Recibe la "
        "descripción del laboratorio, su rúbrica y la solución del estudiante (informe PDF y código), verifica el código "
        "en un entorno aislado y usa un modelo de IA con salida estructurada para valorar cada criterio citando evidencia "
        "concreta. La nota de 0,0 a 5,0 la calcula el servidor con las ponderaciones de la rúbrica, y ninguna valoración "
        "se publica sin la revisión y aprobación del docente."),
    "objetivos": [
        "Identificar qué aprendió cada estudiante, cómo lo aplicó y qué debe fortalecer en cada laboratorio.",
        "Ofrecer evaluaciones consistentes, explicables y trazables, sujetas a validación docente.",
        "Consolidar el aprendizaje de las dos cohortes en un informe integral y un mapa mental de competencias.",
    ],
    "funcionalidades": [
        "Portafolio por estudiante y laboratorio con informe PDF, código (ZIP o GitHub), video y presentación opcionales.",
        "Gestión de rúbricas con versiones, detección de inconsistencias y corrección antes de evaluar.",
        "Evaluación por criterio con citas verificadas, fortalezas, debilidades y recomendaciones personalizadas.",
        "Verificación técnica en sandbox: sintaxis, análisis estático y pruebas unitarias sin acceso a red.",
        "Informe integral descargable en PDF y mapa mental interactivo de temáticas de IA.",
        "Revisión docente con ajuste, aprobación, publicación y registro de auditoría.",
    ],
    "tecnologias": [
        "FastAPI + Pydantic (backend y validación de salidas de IA)", "SQLAlchemy con PostgreSQL o SQLite",
        "React + Vite + Tailwind CSS", "React Flow (mapa mental) y Recharts (gráficas)",
        "Gemini, Claude, OpenAI u Ollama mediante una capa de proveedores configurable",
        "Sandbox con seccomp, límites de recursos y audit hooks de Python", "Docker y Render para el despliegue",
    ],
    "aportes": [
        "La IA elige niveles; el backend calcula la nota: el número nunca depende de un cálculo libre del modelo.",
        "Cada cita del modelo se comprueba contra la evidencia y se marca como verificada, parcial o no verificada.",
        "Reglas objetivas en la rúbrica: una verificación técnica fallida puede limitar el nivel de un criterio.",
        "Trazabilidad completa: evidencias, versión de rúbrica, modelo, pruebas, justificaciones y ajustes docentes.",
    ],
    "estudiante_ve_preliminar": False,
}


class ProyectoEntrada(BaseModel):
    titulo: str | None = None
    lema: str | None = None
    institucion: str | None = None
    abstract: str | None = None
    objetivos: list[str] | None = None
    funcionalidades: list[str] | None = None
    tecnologias: list[str] | None = None
    aportes: list[str] | None = None
    estudiante_ve_preliminar: bool | None = None


class IntegranteEntrada(BaseModel):
    nombre: str = Field(min_length=2, max_length=160)
    rol: str = ""
    descripcion: str = ""
    enlace: str = ""
    orden: int = 1


def proyecto(db: Session) -> dict:
    fila = db.get(Config, "proyecto")
    return {**PROYECTO_DEFECTO, **(fila.valor if fila else {})}


def _integrante(i: Integrante) -> dict:
    return {"id": i.id, "nombre": i.nombre, "rol": i.rol, "descripcion": i.descripcion, "enlace": i.enlace, "orden": i.orden,
            "foto": f"/api/publico/foto/{i.id}?v={i.foto_id}" if i.foto_id else None}


@router.get("/publico/proyecto")
def proyecto_publico(db: Session = Depends(obtener_db)):
    aj = obtener_ajustes()
    cfg = srv_ia.config_ia(db)
    p = proyecto(db)
    p.pop("estudiante_ve_preliminar", None)
    return {"proyecto": p, "equipo": [_integrante(i) for i in db.scalars(select(Integrante).order_by(Integrante.orden, Integrante.id))],
            "registro_abierto": aj.registro_abierto, "modo_simulado": cfg["proveedor"] == "simulado",
            "demo": aj.seed_demo}


@router.get("/publico/foto/{iid}")
def foto(iid: int, db: Session = Depends(obtener_db)):
    i = db.get(Integrante, iid)
    a = db.get(Archivo, i.foto_id, options=[undefer(Archivo.contenido)]) if i and i.foto_id else None
    if not a:
        raise HTTPException(404, "Sin foto.")
    return Response(a.contenido, media_type=a.mime, headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"})


@router.get("/proyecto")
def ver_proyecto(u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    return proyecto(db)


@router.put("/proyecto")
def guardar_proyecto(datos: ProyectoEntrada, u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    fila = db.get(Config, "proyecto")
    valor = {**(fila.valor if fila else {}), **datos.model_dump(exclude_none=True)}
    if fila:
        fila.valor = valor
    else:
        db.add(Config(clave="proyecto", valor=valor))
    auditar(db, u, "proyecto_editado", "config", None, {"campos": sorted(datos.model_dump(exclude_none=True))})
    db.commit()
    return proyecto(db)


@router.post("/proyecto/integrantes", status_code=201)
def crear_integrante(datos: IntegranteEntrada, u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    i = Integrante(**datos.model_dump())
    db.add(i)
    db.commit()
    return _integrante(i)


@router.patch("/proyecto/integrantes/{iid}")
def modificar_integrante(iid: int, datos: IntegranteEntrada, u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    i = db.get(Integrante, iid)
    if not i:
        raise HTTPException(404, "Integrante no encontrado.")
    for k, v in datos.model_dump().items():
        setattr(i, k, v)
    db.commit()
    return _integrante(i)


@router.delete("/proyecto/integrantes/{iid}")
def borrar_integrante(iid: int, u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    i = db.get(Integrante, iid)
    if i:
        db.delete(i)
        db.commit()
    return {"ok": True}


FIRMAS_IMAGEN = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG\r\n\x1a\n": "image/png", b"RIFF": "image/webp"}


@router.post("/proyecto/integrantes/{iid}/foto")
async def subir_foto(iid: int, foto: UploadFile = File(...), u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    i = db.get(Integrante, iid)
    if not i:
        raise HTTPException(404, "Integrante no encontrado.")
    datos = await foto.read()
    if len(datos) > 3 * 1024 * 1024:
        raise HTTPException(413, "La foto no debe superar 3 MB.")
    mime = next((m for firma, m in FIRMAS_IMAGEN.items() if datos.startswith(firma)), None)
    if not mime:
        raise HTTPException(422, "La foto debe ser JPG, PNG o WebP.")
    a = Archivo(nombre=(foto.filename or "foto")[-120:], mime=mime, tamano=len(datos),
                sha256=hashlib.sha256(datos).hexdigest(), contenido=datos, subido_por=u.id)
    db.add(a)
    db.flush()
    i.foto_id = a.id
    db.commit()
    return _integrante(i)


# --- configuración de IA ---------------------------------------------------------------------------

class ConfigIAEntrada(BaseModel):
    proveedor: str
    modelo: str = ""
    base_url: str = ""
    temperatura: float | None = Field(default=None, ge=0, le=2)
    multimodal: bool = True
    pasadas_consistencia: int = Field(default=1, ge=1, le=3)
    api_key: str = ""
    borrar_api_key: bool = False


def _cfg_publica(db: Session) -> dict:
    cfg = srv_ia.config_ia(db)
    clave = cfg.pop("_api_key")
    cfg["clave_configurada"] = bool(clave)
    cfg["clave_pista"] = ("…" + clave[-4:]) if len(clave) >= 12 else ""
    cfg["proveedores"] = [
        {"id": "gemini", "nombre": "Google Gemini (nube)", "requiere_clave": True, "modelo_sugerido": MODELOS_POR_DEFECTO["gemini"], "base_url": URLS_POR_DEFECTO["gemini"]},
        {"id": "anthropic", "nombre": "Anthropic Claude (nube)", "requiere_clave": True, "modelo_sugerido": MODELOS_POR_DEFECTO["anthropic"], "base_url": URLS_POR_DEFECTO["anthropic"]},
        {"id": "openai", "nombre": "OpenAI o compatible (nube)", "requiere_clave": True, "modelo_sugerido": "", "base_url": URLS_POR_DEFECTO["openai"]},
        {"id": "ollama", "nombre": "Ollama (modelo local)", "requiere_clave": False, "modelo_sugerido": MODELOS_POR_DEFECTO["ollama"], "base_url": URLS_POR_DEFECTO["ollama"]},
        {"id": "simulado", "nombre": "Modo simulado (sin IA, solo para pruebas)", "requiere_clave": False, "modelo_sugerido": MODELOS_POR_DEFECTO["simulado"], "base_url": ""},
    ]
    return cfg


@router.get("/config/ia")
def ver_config_ia(u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    return _cfg_publica(db)


@router.put("/config/ia")
def guardar_config_ia(datos: ConfigIAEntrada, u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    if datos.proveedor not in srv_ia.CLASES:
        raise HTTPException(422, "Proveedor no reconocido.")
    if datos.base_url and not datos.base_url.startswith(("http://", "https://")):
        raise HTTPException(422, "La URL base debe empezar por http:// o https://")
    d = datos.model_dump()
    if datos.temperatura is None:
        d["temperatura"] = srv_ia.TEMPERATURA_DEFECTO[datos.proveedor]
    srv_ia.guardar_config_ia(db, d)
    auditar(db, u, "config_ia_modificada", "config", None, {"proveedor": datos.proveedor, "modelo": datos.modelo,
                                                            "clave_actualizada": bool(datos.api_key)})
    db.commit()
    return _cfg_publica(db)


class _Eco(BaseModel):
    respuesta: str
    numero: int


@router.post("/config/ia/probar")
def probar_ia(u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    """Hace una llamada mínima con salida estructurada para comprobar clave, modelo y esquema."""
    proveedor, cfg = srv_ia.obtener_proveedor(db)
    if cfg["proveedor"] == "simulado":
        return {"ok": True, "mensaje": "Modo simulado activo: no se usa ningún modelo de IA.", "modelo": cfg["modelo"]}
    try:
        resp = proveedor.generar_json(sistema="Responde solo con JSON válido según el esquema.",
                                      usuario='Devuelve respuesta="conexión correcta" y numero=7.', esquema=esquema_plano(_Eco))
        from ..services.ia.base import extraer_json
        datos = resp.datos if resp.datos is not None else extraer_json(resp.texto)
        _Eco.model_validate(datos)
        return {"ok": True, "mensaje": "El modelo respondió y la salida cumple el esquema.", "modelo": resp.modelo, "uso": resp.uso}
    except (ErrorIA, ValueError) as e:
        return {"ok": False, "mensaje": str(e)[:600]}


@router.get("/config/ia/modelos")
def listar_modelos(u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    proveedor, _ = srv_ia.obtener_proveedor(db)
    try:
        return {"modelos": proveedor.listar_modelos()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo consultar la lista de modelos: {str(e)[:300]}")


@router.get("/config/sistema")
def sistema(u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    aj = obtener_ajustes()
    cfg = srv_ia.config_ia(db)
    return {
        "ia": {"proveedor": cfg["proveedor"], "modelo": cfg["modelo"], "clave": cfg["origen_clave"]},
        "sandbox": {"habilitado": aj.sandbox_habilitado, "tiempo_s": aj.sandbox_timeout_s, "cpu_s": aj.sandbox_cpu_s,
                    "memoria_mb": aj.sandbox_memoria_mb, "red": "permitida" if aj.sandbox_permitir_red else "bloqueada"},
        "base_datos": "PostgreSQL" if aj.database_url.startswith("postgresql") else "SQLite",
        "python": platform.python_version(), "entorno": aj.entorno, "registro_abierto": aj.registro_abierto,
        "totales": {"usuarios": db.scalar(select(func.count(Usuario.id))), "entregas": db.scalar(select(func.count(Entrega.id))),
                    "evaluaciones": db.scalar(select(func.count(Evaluacion.id)))},
    }


@router.get("/auditoria")
def auditoria(limite: int = 200, u: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    filas = db.scalars(select(Auditoria).order_by(Auditoria.id.desc()).limit(min(limite, 1000)))
    return [{"id": a.id, "accion": a.accion, "entidad": a.entidad, "entidad_id": a.entidad_id,
             "usuario": a.usuario.nombre if a.usuario else "sistema", "detalle": a.detalle, "creado_en": a.creado_en.isoformat()} for a in filas]
