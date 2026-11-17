"""Informe integral del aprendizaje y mapa mental de competencias."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import obtener_db
from ..deps import auditar, es_docente, usuario_actual
from ..models import Informe, Usuario
from ..services import informe as srv_informe
from ..services import mapa as srv_mapa

router = APIRouter(prefix="/api", tags=["informe y mapa"])


def _estudiante(db: Session, sid: int, u: Usuario) -> Usuario:
    if not es_docente(u) and sid != u.id:
        raise HTTPException(403, "Solo puedes consultar tu propio informe.")
    est = db.get(Usuario, sid)
    if not est or est.rol != "estudiante":
        raise HTTPException(404, "Estudiante no encontrado.")
    return est


def _alcance(alcance: str, u: Usuario) -> str:
    # El estudiante solo ve lo que el docente publicó.
    return alcance if (es_docente(u) and alcance in ("publicadas", "todas")) else "publicadas"


def _ultimo(db: Session, sid: int, alcance: str) -> Informe | None:
    return db.scalars(select(Informe).where(Informe.estudiante_id == sid, Informe.alcance == alcance).order_by(Informe.id.desc())).first()


@router.get("/informes/{sid}")
def ver_informe(sid: int, alcance: str = "publicadas", u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    est = _estudiante(db, sid, u)
    alcance = _alcance(alcance, u)
    datos = srv_informe.consolidar(db, est, alcance)
    guardado = _ultimo(db, sid, alcance)
    narrativa, desactualizada = None, False
    if guardado:
        narrativa = guardado.contenido.get("narrativa")
        desactualizada = guardado.contenido.get("huella") != _huella(datos)
    return {"datos": datos, "narrativa": narrativa, "narrativa_modelo": guardado.modelo if guardado else "",
            "narrativa_generada_en": guardado.creado_en.isoformat() if guardado else None,
            "narrativa_desactualizada": desactualizada}


def _huella(datos: dict) -> str:
    return "|".join(f"{l['evaluacion_id']}:{l['nota']}" for l in datos["laboratorios"])


@router.post("/informes/{sid}/generar")
def generar_informe(sid: int, alcance: str = "publicadas", u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    est = _estudiante(db, sid, u)
    alcance = _alcance(alcance, u)
    datos = srv_informe.consolidar(db, est, alcance)
    if not datos["evaluados"]:
        raise HTTPException(409, "Aún no hay laboratorios evaluados" + (" y publicados" if alcance == "publicadas" else "") +
                            " para consolidar un informe.")
    narrativa, modelo = srv_informe.redactar(db, datos)
    db.add(Informe(estudiante_id=sid, alcance=alcance, contenido={"narrativa": narrativa, "huella": _huella(datos)}, modelo=modelo))
    auditar(db, u, "informe_generado", "informe", sid, {"alcance": alcance, "modelo": modelo, "promedio": datos["promedio"]})
    db.commit()
    return ver_informe(sid, alcance, u, db)


@router.get("/informes/{sid}/pdf")
def pdf_informe(sid: int, alcance: str = "publicadas", u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    est = _estudiante(db, sid, u)
    alcance = _alcance(alcance, u)
    datos = srv_informe.consolidar(db, est, alcance)
    guardado = _ultimo(db, sid, alcance)
    pdf = srv_informe.a_pdf(datos, guardado.contenido.get("narrativa") if guardado else None, guardado.modelo if guardado else "")
    nombre = re.sub(r"[^A-Za-z0-9]+", "_", est.nombre).strip("_") or "estudiante"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="informe_integral_{nombre}.pdf"'})


@router.get("/mapa/{sid}")
def ver_mapa(sid: int, alcance: str = "publicadas", cohorte: int | None = None, u: Usuario = Depends(usuario_actual),
             db: Session = Depends(obtener_db)):
    est = _estudiante(db, sid, u)
    return srv_mapa.construir(db, est, _alcance(alcance, u), cohorte if cohorte in (1, 2) else None)
