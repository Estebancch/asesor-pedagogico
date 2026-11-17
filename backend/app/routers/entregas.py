"""Portafolio académico (entregas por estudiante y laboratorio) y evaluaciones."""
from __future__ import annotations

import copy
import hashlib
import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer
from sqlalchemy.orm.attributes import flag_modified

from ..config import obtener_ajustes
from ..db import SesionLocal, obtener_db
from ..deps import auditar, docente_o_admin, es_docente, usuario_actual
from ..models import (Archivo, Auditoria, Cohorte, Config, Entrega, Evaluacion, Laboratorio,
                      Usuario, ahora)
from ..services import evaluacion as motor
from ..services.extraccion import RE_GITHUB
from ..services.rubricas import Rubrica
from .academico import rubrica_vigente

router = APIRouter(prefix="/api", tags=["portafolio y evaluación"])
RE_URL = re.compile(r"^https?://[^\s]{4,290}$")


def preliminar_visible(db: Session) -> bool:
    fila = db.get(Config, "proyecto")
    return bool(fila and fila.valor.get("estudiante_ve_preliminar"))


def _arch(a: Archivo | None) -> dict | None:
    return {"id": a.id, "nombre": a.nombre, "tamano": a.tamano, "sha256": a.sha256[:16]} if a else None


def _eval_resumen(ev: Evaluacion, u: Usuario, ver_prelim: bool) -> dict:
    visible = es_docente(u) or ev.estado == "publicada" or (ver_prelim and ev.estado in ("preliminar", "aprobada"))
    d = {"id": ev.id, "estado": ev.estado, "creado_en": ev.creado_en.isoformat(), "progreso": ev.progreso,
         "modelo": f"{ev.proveedor}/{ev.modelo}" if ev.proveedor else "", "rubrica_version": ev.rubrica_version.version,
         "visible": visible, "error": ev.error if (es_docente(u) or ev.estado == "error") else ""}
    if visible:
        d["nota"] = ev.nota_final if ev.nota_final is not None else ev.nota_preliminar
        d["alertas"] = len(ev.resultado.get("alertas", [])) + sum(len(c.get("alertas", [])) for c in ev.resultado.get("criterios", []))
    return d


def _entrega(e: Entrega, u: Usuario, ver_prelim: bool) -> dict:
    return {"id": e.id, "laboratorio_id": e.laboratorio_id, "laboratorio": e.laboratorio.titulo,
            "cohorte": e.laboratorio.cohorte.numero, "cohorte_nombre": e.laboratorio.cohorte.nombre,
            "estudiante": {"id": e.estudiante.id, "nombre": e.estudiante.nombre, "codigo": e.estudiante.codigo},
            "numero": e.numero, "creado_en": e.creado_en.isoformat(), "comentario": e.comentario,
            "informe": _arch(e.informe), "codigo": _arch(e.codigo), "repo_url": e.repo_url, "repo_commit": e.repo_commit,
            "video_url": e.video_url, "presentacion": _arch(e.presentacion), "presentacion_url": e.presentacion_url,
            "rubrica_version": {"id": e.rubrica_version.id, "version": e.rubrica_version.version} if e.rubrica_version else None,
            "evaluaciones": [_eval_resumen(x, u, ver_prelim) for x in e.evaluaciones]}


def _autorizar_entrega(e: Entrega | None, u: Usuario) -> Entrega:
    if not e:
        raise HTTPException(404, "Entrega no encontrada.")
    if not es_docente(u) and e.estudiante_id != u.id:
        raise HTTPException(403, "Esta entrega pertenece a otro estudiante.")
    return e


async def _guardar(db: Session, f: UploadFile | None, u: Usuario, extensiones: tuple[str, ...], firma: bytes | None, que: str) -> Archivo | None:
    if f is None or not f.filename:
        return None
    datos = await f.read()
    limite = obtener_ajustes().max_upload_mb
    if len(datos) > limite * 1024 * 1024:
        raise HTTPException(413, f"{que}: el archivo supera {limite} MB.")
    if not f.filename.lower().endswith(extensiones):
        raise HTTPException(422, f"{que}: se espera un archivo {' o '.join(extensiones)}.")
    if firma and not datos.startswith(firma):
        raise HTTPException(422, f"{que}: el contenido no corresponde a un archivo {extensiones[0]} válido.")
    a = Archivo(nombre=f.filename[-200:], mime=f.content_type or "application/octet-stream", tamano=len(datos),
                sha256=hashlib.sha256(datos).hexdigest(), contenido=datos, subido_por=u.id)
    db.add(a)
    db.flush()
    return a


@router.post("/laboratorios/{lid}/entregas", status_code=201)
async def crear_entrega(lid: int, informe: UploadFile | None = File(None), codigo: UploadFile | None = File(None),
                        presentacion: UploadFile | None = File(None), repo_url: str = Form(""), video_url: str = Form(""),
                        presentacion_url: str = Form(""), comentario: str = Form(""), estudiante_id: int | None = Form(None),
                        u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    lab = db.get(Laboratorio, lid)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado.")
    estudiante = u
    if es_docente(u):
        estudiante = db.get(Usuario, estudiante_id) if estudiante_id else None
        if not estudiante or estudiante.rol != "estudiante":
            raise HTTPException(422, "Indica a qué estudiante pertenece la entrega.")
    repo_url, video_url, presentacion_url = repo_url.strip(), video_url.strip(), presentacion_url.strip()
    if repo_url and not RE_GITHUB.match(repo_url):
        raise HTTPException(422, "El repositorio debe ser una URL pública de GitHub: https://github.com/usuario/repositorio")
    for etiqueta, url in (("video", video_url), ("presentación", presentacion_url)):
        if url and not RE_URL.match(url):
            raise HTTPException(422, f"El enlace de {etiqueta} no es una URL válida.")
    a_inf = await _guardar(db, informe, u, (".pdf",), b"%PDF", "Informe")
    a_cod = await _guardar(db, codigo, u, (".zip",), b"PK", "Código")
    a_pre = await _guardar(db, presentacion, u, (".pptx", ".pdf"), None, "Presentación")
    if not a_inf:
        raise HTTPException(422, "Falta el informe en PDF.")
    if not a_cod and not repo_url:
        raise HTTPException(422, "Falta el código fuente: sube un ZIP o indica el repositorio de GitHub.")
    vig = rubrica_vigente(lab)
    n = len(db.scalars(select(Entrega.id).where(Entrega.laboratorio_id == lid, Entrega.estudiante_id == estudiante.id)).all())
    e = Entrega(laboratorio_id=lid, estudiante_id=estudiante.id, numero=n + 1, rubrica_version_id=vig.id if vig else None,
                informe_id=a_inf.id, codigo_id=a_cod.id if a_cod else None, repo_url=repo_url, video_url=video_url,
                presentacion_id=a_pre.id if a_pre else None, presentacion_url=presentacion_url, comentario=comentario.strip()[:2000])
    db.add(e)
    db.flush()
    auditar(db, u, "entrega_creada", "entrega", e.id, {"laboratorio": lab.titulo, "intento": e.numero,
                                                        "informe_sha256": a_inf.sha256, "codigo_sha256": a_cod.sha256 if a_cod else None})
    db.commit()
    return _entrega(e, u, preliminar_visible(db))


@router.get("/entregas")
def listar_entregas(laboratorio_id: int | None = None, estudiante_id: int | None = None,
                    u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    q = select(Entrega).order_by(Entrega.id.desc())
    if not es_docente(u):
        q = q.where(Entrega.estudiante_id == u.id)
    elif estudiante_id:
        q = q.where(Entrega.estudiante_id == estudiante_id)
    if laboratorio_id:
        q = q.where(Entrega.laboratorio_id == laboratorio_id)
    vp = preliminar_visible(db)
    return [_entrega(e, u, vp) for e in db.scalars(q.limit(500))]


@router.get("/entregas/{eid}")
def ver_entrega(eid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    return _entrega(_autorizar_entrega(db.get(Entrega, eid), u), u, preliminar_visible(db))


@router.delete("/entregas/{eid}")
def borrar_entrega(eid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    e = _autorizar_entrega(db.get(Entrega, eid), u)
    if any(x.estado in ("aprobada", "publicada") for x in e.evaluaciones) and u.rol != "admin":
        raise HTTPException(409, "La entrega ya tiene una evaluación aprobada; se conserva por trazabilidad.")
    auditar(db, u, "entrega_eliminada", "entrega", e.id, {"laboratorio": e.laboratorio.titulo, "estudiante": e.estudiante.email})
    db.delete(e)
    db.commit()
    return {"ok": True}


@router.get("/archivos/{aid}")
def descargar(aid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    a = db.get(Archivo, aid, options=[undefer(Archivo.contenido)])
    if not a:
        raise HTTPException(404, "Archivo no encontrado.")
    if not es_docente(u):
        propio = db.scalars(select(Entrega.id).where(
            Entrega.estudiante_id == u.id,
            (Entrega.informe_id == aid) | (Entrega.codigo_id == aid) | (Entrega.presentacion_id == aid))).first()
        if not propio:
            raise HTTPException(403, "No tienes acceso a este archivo.")
    nombre = re.sub(r'[^\w.\- ]', "_", a.nombre)
    return Response(a.contenido, media_type=a.mime, headers={
        "Content-Disposition": f'attachment; filename="{nombre}"', "X-Content-Type-Options": "nosniff"})


@router.get("/portafolio")
def portafolio(estudiante_id: int | None = None, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    """Trabajos de las cohortes 1 y 2 organizados por laboratorio para un estudiante."""
    if es_docente(u):
        est = db.get(Usuario, estudiante_id) if estudiante_id else None
        if not est:
            raise HTTPException(422, "Indica el estudiante.")
    else:
        est = u
    vp = preliminar_visible(db)
    cohortes = []
    for c in db.scalars(select(Cohorte).order_by(Cohorte.numero)):
        labs = []
        for lab in c.laboratorios:
            ents = db.scalars(select(Entrega).where(Entrega.laboratorio_id == lab.id, Entrega.estudiante_id == est.id)
                              .order_by(Entrega.id.desc())).all()
            vig = rubrica_vigente(lab)
            labs.append({"id": lab.id, "orden": lab.orden, "titulo": lab.titulo, "fecha": lab.fecha.isoformat() if lab.fecha else None,
                         "rubrica": {"id": vig.id, "version": vig.version} if vig else None,
                         "entregas": [_entrega(e, u, vp) for e in ents]})
        cohortes.append({"id": c.id, "numero": c.numero, "nombre": c.nombre, "periodo": c.periodo, "laboratorios": labs})
    return {"estudiante": {"id": est.id, "nombre": est.nombre, "codigo": est.codigo, "email": est.email}, "cohortes": cohortes}


@router.get("/portafolio/matriz")
def matriz(u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    """Vista docente: estudiantes × laboratorios con el estado de cada entrega."""
    labs = [{"id": l.id, "titulo": l.titulo, "cohorte": c.numero, "orden": l.orden, "etiqueta": f"C{c.numero}·L{l.orden}"}
            for c in db.scalars(select(Cohorte).order_by(Cohorte.numero)) for l in c.laboratorios]
    filas = []
    for est in db.scalars(select(Usuario).where(Usuario.rol == "estudiante", Usuario.activo.is_(True)).order_by(Usuario.nombre)):
        celdas = {}
        for e in db.scalars(select(Entrega).where(Entrega.estudiante_id == est.id).order_by(Entrega.id)):
            ev = e.evaluaciones[-1] if e.evaluaciones else None
            celdas[str(e.laboratorio_id)] = {
                "entrega_id": e.id, "evaluacion_id": ev.id if ev else None, "estado": ev.estado if ev else "sin_evaluar",
                "nota": (ev.nota_final if ev.nota_final is not None else ev.nota_preliminar) if ev else None}
        filas.append({"estudiante": {"id": est.id, "nombre": est.nombre, "codigo": est.codigo}, "celdas": celdas})
    return {"laboratorios": labs, "filas": filas}


# --- evaluaciones -------------------------------------------------------------------------------

class SolicitudEvaluacion(BaseModel):
    forzar: bool = False


class AjusteCriterio(BaseModel):
    nivel_id: str | None = None
    puntaje_manual: float | None = Field(default=None, ge=0, le=5)
    quitar_puntaje_manual: bool = False
    justificacion: str | None = None
    recomendaciones: list[str] | None = None
    comentario: str = Field(default="", max_length=1000, description="Motivo del ajuste (queda en la auditoría)")


class AjusteGeneral(BaseModel):
    observacion_docente: str | None = None
    resumen: str | None = None
    recomendaciones: list[str] | None = None
    que_fortalecer: list[str] | None = None


def _autorizar_eval(db: Session, vid: int, u: Usuario, escritura: bool = False) -> Evaluacion:
    ev = db.get(Evaluacion, vid)
    if not ev:
        raise HTTPException(404, "Evaluación no encontrada.")
    if es_docente(u):
        return ev
    if escritura or ev.entrega.estudiante_id != u.id:
        raise HTTPException(403, "No tienes permiso sobre esta evaluación.")
    return ev


@router.post("/entregas/{eid}/evaluar", status_code=202)
def evaluar(eid: int, datos: SolicitudEvaluacion, tareas: BackgroundTasks, u: Usuario = Depends(usuario_actual),
            db: Session = Depends(obtener_db)):
    e = _autorizar_entrega(db.get(Entrega, eid), u)
    vig = rubrica_vigente(e.laboratorio)
    if not vig:
        raise HTTPException(409, "El laboratorio no tiene una rúbrica validada. El docente debe corregirla y validarla antes de evaluar.")
    if not (e.laboratorio.descripcion.strip() and e.laboratorio.objetivos.strip()):
        raise HTTPException(409, "Al laboratorio le falta la descripción o los objetivos; son necesarios para evaluar.")
    if any(x.estado in ("en_cola", "procesando") for x in e.evaluaciones):
        raise HTTPException(409, "Ya hay una evaluación en curso para esta entrega.")
    if not es_docente(u) and any(x.estado in ("aprobada", "publicada") for x in e.evaluaciones):
        raise HTTPException(409, "Esta entrega ya fue revisada por el docente. Sube una nueva entrega para volver a evaluarte.")
    e.rubrica_version_id = vig.id
    ev = Evaluacion(entrega_id=e.id, rubrica_version_id=vig.id, estado="en_cola", progreso="En cola", creado_por=u.id)
    db.add(ev)
    db.flush()
    auditar(db, u, "evaluacion_solicitada", "evaluacion", ev.id, {"entrega": e.id, "rubrica_version": vig.version, "forzar": datos.forzar})
    db.commit()
    tareas.add_task(motor.ejecutar, ev.id, SesionLocal, datos.forzar and es_docente(u))
    return {"id": ev.id, "estado": ev.estado}


def _detalle(ev: Evaluacion, u: Usuario, db: Session) -> dict:
    e = ev.entrega
    visible = es_docente(u) or ev.estado == "publicada" or (preliminar_visible(db) and ev.estado in ("preliminar", "aprobada"))
    d = {"id": ev.id, "estado": ev.estado, "progreso": ev.progreso, "error": ev.error, "creado_en": ev.creado_en.isoformat(),
         "visible": visible, "es_preliminar": ev.estado in ("preliminar", "aprobada"),
         "entrega": {"id": e.id, "numero": e.numero, "informe": _arch(e.informe), "codigo": _arch(e.codigo),
                     "repo_url": e.repo_url, "repo_commit": e.repo_commit, "video_url": e.video_url,
                     "presentacion": _arch(e.presentacion), "presentacion_url": e.presentacion_url},
         "laboratorio": {"id": e.laboratorio.id, "titulo": e.laboratorio.titulo, "cohorte": e.laboratorio.cohorte.nombre},
         "estudiante": {"id": e.estudiante.id, "nombre": e.estudiante.nombre, "codigo": e.estudiante.codigo}}
    if not visible:
        return d
    rv = ev.rubrica_version
    d.update({
        "nota": ev.nota_final if ev.nota_final is not None else ev.nota_preliminar,
        "nota_preliminar": ev.nota_preliminar, "nota_final": ev.nota_final,
        "resultado": ev.resultado, "calculo": ev.calculo, "verificacion": ev.verificacion,
        "observacion_docente": ev.observacion_docente,
        "rubrica": {"id": rv.id, "version": rv.version, "hash": rv.hash, "contenido": rv.contenido},
        "trazabilidad": {
            "proveedor": ev.proveedor, "modelo": ev.modelo, "parametros": ev.parametros, "prompt_version": ev.prompt_version,
            "hash_evidencias": ev.hash_evidencias, "clave_reproducibilidad": ev.clave_reproducibilidad,
            "rubrica_version": rv.version, "rubrica_hash": rv.hash, "evidencias": ev.evidencias, "uso": ev.uso,
            "duracion_s": ev.duracion_s, "aprobado_en": ev.aprobado_en.isoformat() if ev.aprobado_en else None,
            "publicado_en": ev.publicado_en.isoformat() if ev.publicado_en else None,
        }})
    return d


@router.get("/evaluaciones")
def cola(estado: str | None = None, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    q = select(Evaluacion).order_by(Evaluacion.id.desc()).limit(300)
    if estado:
        q = q.where(Evaluacion.estado.in_(estado.split(",")))
    salida = []
    for ev in db.scalars(q):
        e = ev.entrega
        salida.append({"id": ev.id, "estado": ev.estado, "creado_en": ev.creado_en.isoformat(),
                       "nota": ev.nota_final if ev.nota_final is not None else ev.nota_preliminar,
                       "estudiante": e.estudiante.nombre, "laboratorio": e.laboratorio.titulo,
                       "cohorte": e.laboratorio.cohorte.numero, "modelo": f"{ev.proveedor}/{ev.modelo}",
                       "alertas": len(ev.resultado.get("alertas", [])) + sum(len(c.get("alertas", [])) for c in ev.resultado.get("criterios", [])),
                       "error": ev.error[:200]})
    return salida


@router.get("/evaluaciones/{vid}")
def ver_evaluacion(vid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    return _detalle(_autorizar_eval(db, vid, u), u, db)


@router.get("/evaluaciones/{vid}/fuente")
def ver_fuente(vid: int, id: str, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    """Texto de una fuente de evidencia tal como se analizó (para comprobar una cita)."""
    ev = _autorizar_eval(db, vid, u)
    if not es_docente(u) and ev.estado != "publicada" and not preliminar_visible(db):
        raise HTTPException(403, "La evaluación aún no está publicada.")
    textos = db.scalar(select(Evaluacion.evidencias_texto).where(Evaluacion.id == vid)) or {}
    if id not in textos:
        raise HTTPException(404, "Fuente no encontrada en las evidencias de esta evaluación.")
    meta = next((f for f in ev.evidencias.get("fuentes", []) if f["id"] == id), {})
    return {"id": id, "titulo": meta.get("titulo", id), "tipo": meta.get("tipo", ""), "texto": textos[id]}


@router.get("/evaluaciones/{vid}/auditoria")
def auditoria_eval(vid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    filas = db.scalars(select(Auditoria).where(Auditoria.entidad == "evaluacion", Auditoria.entidad_id == vid).order_by(Auditoria.id))
    return [{"id": a.id, "accion": a.accion, "usuario": a.usuario.nombre if a.usuario else "sistema",
             "detalle": a.detalle, "creado_en": a.creado_en.isoformat()} for a in filas]


def _editable(ev: Evaluacion) -> None:
    if ev.estado not in ("preliminar", "aprobada"):
        raise HTTPException(409, "Solo se ajustan evaluaciones preliminares o aprobadas. Reabre la evaluación si ya está publicada.")


@router.patch("/evaluaciones/{vid}/criterios/{criterio_id}")
def ajustar_criterio(vid: int, criterio_id: str, datos: AjusteCriterio, u: Usuario = Depends(docente_o_admin),
                     db: Session = Depends(obtener_db)):
    ev = _autorizar_eval(db, vid, u, escritura=True)
    _editable(ev)
    rubrica = Rubrica.model_validate(ev.rubrica_version.contenido)
    res = copy.deepcopy(dict(ev.resultado))
    crit = next((c for c in res.get("criterios", []) if c["criterio_id"] == criterio_id), None)
    if crit is None:
        raise HTTPException(404, "Criterio no encontrado en esta evaluación.")
    antes = {k: crit.get(k) for k in ("nivel_id", "puntaje_manual", "justificacion", "recomendaciones")}
    if datos.nivel_id is not None:
        if datos.nivel_id not in {n.id for n in rubrica.niveles}:
            raise HTTPException(422, "El nivel no existe en la rúbrica.")
        crit["nivel_id"], crit["puntaje_manual"] = datos.nivel_id, None
    if datos.puntaje_manual is not None:
        crit["puntaje_manual"] = round(datos.puntaje_manual, 2)
    if datos.quitar_puntaje_manual:
        crit["puntaje_manual"] = None
    if datos.justificacion is not None:
        crit["justificacion"] = datos.justificacion.strip()
    if datos.recomendaciones is not None:
        crit["recomendaciones"] = [r.strip() for r in datos.recomendaciones if r.strip()]
    despues = {k: crit.get(k) for k in antes}
    cambios = {k: {"antes": antes[k], "despues": despues[k]} for k in antes if antes[k] != despues[k]}
    if not cambios:
        return _detalle(ev, u, db)
    if ("nivel_id" in cambios or "puntaje_manual" in cambios) and not datos.comentario.strip():
        raise HTTPException(422, "Explica brevemente el motivo del ajuste de la valoración; queda en el registro de auditoría.")
    crit["ajuste_docente"] = {"por": u.nombre, "en": ahora().isoformat(), "comentario": datos.comentario.strip(),
                              "nivel_ia": crit.get("nivel_ia")}
    nota_antes = ev.nota_final if ev.nota_final is not None else ev.nota_preliminar
    ev.resultado = res
    flag_modified(ev, "resultado")
    motor.recalcular(ev, rubrica)
    auditar(db, u, "criterio_ajustado", "evaluacion", ev.id, {
        "criterio": crit["nombre"], "cambios": cambios, "comentario": datos.comentario.strip(),
        "nota_antes": nota_antes, "nota_despues": ev.calculo["nota"]})
    db.commit()
    return _detalle(ev, u, db)


@router.patch("/evaluaciones/{vid}")
def ajustar_general(vid: int, datos: AjusteGeneral, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    ev = _autorizar_eval(db, vid, u, escritura=True)
    _editable(ev)
    cambios = datos.model_dump(exclude_none=True)
    res = copy.deepcopy(dict(ev.resultado))
    if "observacion_docente" in cambios:
        ev.observacion_docente = cambios.pop("observacion_docente").strip()
    for k, v in cambios.items():
        res[k] = [x.strip() for x in v if x.strip()] if isinstance(v, list) else v.strip()
    ev.resultado = res
    flag_modified(ev, "resultado")
    auditar(db, u, "retroalimentacion_editada", "evaluacion", ev.id, {"campos": sorted(datos.model_dump(exclude_none=True))})
    db.commit()
    return _detalle(ev, u, db)


def _transicion(vid: int, u: Usuario, db: Session, desde: tuple[str, ...], hacia: str, accion: str) -> dict:
    ev = _autorizar_eval(db, vid, u, escritura=True)
    if ev.estado not in desde:
        raise HTTPException(409, f"La evaluación está en estado «{ev.estado}»; esta acción no aplica.")
    if hacia in ("aprobada", "publicada"):
        if ev.calculo.get("criterios_pendientes"):
            raise HTTPException(409, "Hay criterios sin valorar. Asígnales un nivel antes de aprobar.")
        if ev.estado == "preliminar":
            ev.aprobado_por, ev.aprobado_en = u.id, ahora()
        ev.nota_final = ev.calculo.get("nota")
    if hacia == "publicada":
        ev.publicado_en = ahora()
    if hacia == "preliminar":
        ev.nota_final, ev.publicado_en, ev.aprobado_en, ev.aprobado_por = None, None, None, None
        ev.nota_preliminar = ev.calculo.get("nota")
    anterior, ev.estado = ev.estado, hacia
    auditar(db, u, accion, "evaluacion", ev.id, {"de": anterior, "a": hacia, "nota": ev.calculo.get("nota")})
    db.commit()
    return _detalle(ev, u, db)


@router.post("/evaluaciones/{vid}/aprobar")
def aprobar(vid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    return _transicion(vid, u, db, ("preliminar",), "aprobada", "evaluacion_aprobada")


@router.post("/evaluaciones/{vid}/publicar")
def publicar(vid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    return _transicion(vid, u, db, ("preliminar", "aprobada"), "publicada", "evaluacion_publicada")


@router.post("/evaluaciones/{vid}/reabrir")
def reabrir(vid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    return _transicion(vid, u, db, ("aprobada", "publicada"), "preliminar", "evaluacion_reabierta")


@router.delete("/evaluaciones/{vid}")
def borrar_evaluacion(vid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    ev = _autorizar_eval(db, vid, u, escritura=True)
    if ev.estado == "publicada":
        raise HTTPException(409, "Una evaluación publicada no se elimina; reábrela primero.")
    auditar(db, u, "evaluacion_eliminada", "evaluacion", ev.id, {"estado": ev.estado, "nota": ev.nota_preliminar})
    db.delete(ev)
    db.commit()
    return {"ok": True}


