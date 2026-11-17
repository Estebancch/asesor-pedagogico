"""Cohortes, laboratorios y rúbricas versionadas."""
from __future__ import annotations

import hashlib
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import obtener_ajustes
from ..db import obtener_db
from ..deps import auditar, docente_o_admin, es_docente, usuario_actual
from ..models import Archivo, Cohorte, Entrega, Evaluacion, Laboratorio, RubricaVersion, Usuario, ahora
from ..services import rubricas as srv
from ..services.ia import ErrorIA, generar_estructurado, obtener_proveedor

router = APIRouter(prefix="/api", tags=["académico"])


class CohorteEntrada(BaseModel):
    numero: int = Field(ge=1, le=20)
    nombre: str = Field(min_length=2, max_length=120)
    periodo: str = ""
    descripcion: str = ""


class LabEntrada(BaseModel):
    cohorte_id: int
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = ""
    objetivos: str = ""
    orden: int = 1
    fecha: date | None = None
    pruebas_docente: str = ""


class LabCambio(BaseModel):
    cohorte_id: int | None = None
    titulo: str | None = None
    descripcion: str | None = None
    objetivos: str | None = None
    orden: int | None = None
    fecha: date | None = None
    pruebas_docente: str | None = None


class RubricaEntrada(BaseModel):
    contenido: srv.Rubrica | None = None
    desde_version: int | None = None


def rubrica_vigente(lab: Laboratorio) -> RubricaVersion | None:
    validadas = [r for r in lab.rubricas if r.estado == "validada"]
    return validadas[-1] if validadas else None


def _rv(r: RubricaVersion, completo: bool = True) -> dict:
    d = {"id": r.id, "laboratorio_id": r.laboratorio_id, "version": r.version, "estado": r.estado, "origen": r.origen,
         "interpretada_por": r.interpretada_por, "hash": r.hash, "creado_en": r.creado_en.isoformat(),
         "validada_en": r.validada_en.isoformat() if r.validada_en else None,
         "archivo": {"id": r.archivo.id, "nombre": r.archivo.nombre} if r.archivo else None,
         "errores": sum(1 for i in r.inconsistencias if i["severidad"] == "error"),
         "advertencias": sum(1 for i in r.inconsistencias if i["severidad"] == "advertencia"),
         "titulo": r.contenido.get("titulo", ""), "criterios": len(r.contenido.get("criterios", []))}
    if completo:
        d.update({"contenido": r.contenido, "inconsistencias": r.inconsistencias})
    return d


def _lab(lab: Laboratorio, db: Session, u: Usuario, detalle: bool = False) -> dict:
    vig = rubrica_vigente(lab)
    d = {"id": lab.id, "cohorte_id": lab.cohorte_id, "cohorte": lab.cohorte.nombre, "cohorte_numero": lab.cohorte.numero,
         "orden": lab.orden, "titulo": lab.titulo, "fecha": lab.fecha.isoformat() if lab.fecha else None,
         "tiene_descripcion": bool(lab.descripcion.strip() and lab.objetivos.strip()),
         "rubrica": {"id": vig.id, "version": vig.version} if vig else None,
         "rubrica_borradores": sum(1 for r in lab.rubricas if r.estado == "borrador")}
    if es_docente(u):
        d["entregas"] = db.scalar(select(func.count(func.distinct(Entrega.estudiante_id))).where(Entrega.laboratorio_id == lab.id)) or 0
        d["por_revisar"] = db.scalar(select(func.count(Evaluacion.id)).join(Entrega).where(
            Entrega.laboratorio_id == lab.id, Evaluacion.estado.in_(("preliminar", "aprobada")))) or 0
    else:
        e = db.scalars(select(Entrega).where(Entrega.laboratorio_id == lab.id, Entrega.estudiante_id == u.id).order_by(Entrega.id.desc())).first()
        d["mi_entrega"] = None
        if e:
            ev = e.evaluaciones[-1] if e.evaluaciones else None
            pub = next((x for x in reversed(e.evaluaciones) if x.estado == "publicada"), None)
            d["mi_entrega"] = {"id": e.id, "numero": e.numero, "creado_en": e.creado_en.isoformat(),
                               "estado_evaluacion": ev.estado if ev else None,
                               "nota": pub.nota_final if pub else None, "evaluacion_publicada_id": pub.id if pub else None}
    if detalle:
        d.update({"descripcion": lab.descripcion, "objetivos": lab.objetivos,
                  "rubrica_vigente": _rv(vig) if vig else None})
        if es_docente(u):
            d["pruebas_docente"] = lab.pruebas_docente
            d["rubricas"] = [_rv(r, completo=False) for r in lab.rubricas]
    return d


@router.get("/cohortes")
def cohortes(u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    return [{"id": c.id, "numero": c.numero, "nombre": c.nombre, "periodo": c.periodo, "descripcion": c.descripcion,
             "laboratorios": [_lab(l, db, u) for l in c.laboratorios]}
            for c in db.scalars(select(Cohorte).order_by(Cohorte.numero))]


@router.post("/cohortes", status_code=201)
def crear_cohorte(datos: CohorteEntrada, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    if db.scalars(select(Cohorte).where(Cohorte.numero == datos.numero)).first():
        raise HTTPException(409, f"Ya existe la cohorte {datos.numero}.")
    c = Cohorte(**datos.model_dump())
    db.add(c)
    db.commit()
    return {"id": c.id}


@router.patch("/cohortes/{cid}")
def modificar_cohorte(cid: int, datos: CohorteEntrada, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    c = db.get(Cohorte, cid)
    if not c:
        raise HTTPException(404, "Cohorte no encontrada.")
    otra = db.scalars(select(Cohorte).where(Cohorte.numero == datos.numero, Cohorte.id != cid)).first()
    if otra:
        raise HTTPException(409, f"Ya existe la cohorte {datos.numero}.")
    for k, v in datos.model_dump().items():
        setattr(c, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/cohortes/{cid}")
def borrar_cohorte(cid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    c = db.get(Cohorte, cid)
    if not c:
        raise HTTPException(404, "Cohorte no encontrada.")
    if c.laboratorios:
        raise HTTPException(409, "La cohorte tiene laboratorios. Elimínalos o muévelos antes de borrarla.")
    db.delete(c)
    db.commit()
    return {"ok": True}


@router.post("/laboratorios", status_code=201)
def crear_lab(datos: LabEntrada, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    if not db.get(Cohorte, datos.cohorte_id):
        raise HTTPException(404, "Cohorte no encontrada.")
    lab = Laboratorio(**datos.model_dump())
    db.add(lab)
    db.flush()
    auditar(db, u, "laboratorio_creado", "laboratorio", lab.id)
    db.commit()
    return {"id": lab.id}


def _obtener_lab(db: Session, lid: int) -> Laboratorio:
    lab = db.get(Laboratorio, lid)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado.")
    return lab


@router.get("/laboratorios/{lid}")
def ver_lab(lid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    return _lab(_obtener_lab(db, lid), db, u, detalle=True)


@router.patch("/laboratorios/{lid}")
def modificar_lab(lid: int, datos: LabCambio, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    lab = _obtener_lab(db, lid)
    for k, v in datos.model_dump(exclude_unset=True).items():
        setattr(lab, k, v)
    auditar(db, u, "laboratorio_modificado", "laboratorio", lab.id, {"campos": sorted(datos.model_dump(exclude_unset=True))})
    db.commit()
    return {"ok": True}


@router.delete("/laboratorios/{lid}")
def borrar_lab(lid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    lab = _obtener_lab(db, lid)
    if lab.entregas:
        raise HTTPException(409, "El laboratorio tiene entregas; no se puede borrar para no perder la trazabilidad.")
    db.delete(lab)
    db.commit()
    return {"ok": True}


# --- rúbricas ---------------------------------------------------------------------------------

def _guardar_borrador(db: Session, lab: Laboratorio, r: srv.Rubrica, u: Usuario, origen: str,
                      archivo_id: int | None = None, modelo: str = "") -> RubricaVersion:
    srv.completar_ids(r)
    version = (max((x.version for x in lab.rubricas), default=0)) + 1
    rv = RubricaVersion(laboratorio_id=lab.id, version=version, estado="borrador", contenido=r.model_dump(),
                        inconsistencias=[i.model_dump() for i in srv.validar(r)], hash=srv.hash_rubrica(r),
                        origen=origen, archivo_id=archivo_id, interpretada_por=modelo, creado_por=u.id)
    db.add(rv)
    db.flush()
    auditar(db, u, "rubrica_borrador_creado", "rubrica", rv.id, {"version": version, "origen": origen})
    return rv


@router.get("/laboratorios/{lid}/rubricas")
def listar_rubricas(lid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    return [_rv(r, completo=False) for r in _obtener_lab(db, lid).rubricas]


@router.post("/laboratorios/{lid}/rubricas", status_code=201)
def crear_rubrica(lid: int, datos: RubricaEntrada, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    lab = _obtener_lab(db, lid)
    if datos.contenido is not None:
        r, origen = datos.contenido, "manual"
    elif datos.desde_version is not None:
        base = db.get(RubricaVersion, datos.desde_version)
        if not base or base.laboratorio_id != lab.id:
            raise HTTPException(404, "Versión de rúbrica no encontrada.")
        r, origen = srv.Rubrica.model_validate(base.contenido), f"copia de v{base.version}"
    else:
        r, origen = srv.plantilla_base(), "plantilla"
        r.titulo = f"Rúbrica — {lab.titulo}"
    rv = _guardar_borrador(db, lab, r, u, origen)
    db.commit()
    return _rv(rv)


@router.post("/laboratorios/{lid}/rubricas/archivo", status_code=201)
async def cargar_rubrica(lid: int, archivo: UploadFile = File(...), u: Usuario = Depends(docente_o_admin),
                         db: Session = Depends(obtener_db)):
    """Carga un archivo de rúbrica (PDF, DOCX, XLSX, CSV, MD, TXT o JSON), lo
    interpreta y crea un borrador con sus inconsistencias para corregir."""
    lab = _obtener_lab(db, lid)
    datos = await archivo.read()
    if len(datos) > obtener_ajustes().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "El archivo supera el tamaño máximo permitido.")
    nombre = archivo.filename or "rubrica"
    try:
        contenido = srv.extraer_contenido(nombre, datos)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, f"No se pudo leer el archivo ({type(e).__name__}). Formatos admitidos: PDF, DOCX, XLSX, CSV, MD, TXT, JSON.")
    arch = Archivo(nombre=nombre, mime=archivo.content_type or "application/octet-stream", tamano=len(datos),
                   sha256=hashlib.sha256(datos).hexdigest(), contenido=datos, subido_por=u.id)
    db.add(arch)
    db.flush()
    r, origen, modelo, notas = None, "archivo", "", []
    if contenido.json_directo is not None:
        try:
            r, origen = srv.Rubrica.model_validate(contenido.json_directo), "archivo JSON"
        except Exception:  # noqa: BLE001
            notas.append("El JSON no tiene la estructura de rúbrica de la plataforma; se intentó interpretarlo como texto.")
    if r is None:
        proveedor, cfg = obtener_proveedor(db)
        if cfg["proveedor"] != "simulado" and contenido.texto.strip():
            try:
                obj, _ = generar_estructurado(
                    proveedor, srv.RubricaInterpretadaIA, sistema=srv.SISTEMA_RUBRICA,
                    usuario="Transcribe esta rúbrica:\n\n" + contenido.texto[:60_000], contexto={"tarea": "rubrica"})
                r, origen, modelo = srv.desde_ia(obj), "interpretada con IA", f"{cfg['proveedor']}/{cfg['modelo']}"
            except ErrorIA as e:
                notas.append(f"La interpretación con IA no estuvo disponible ({str(e)[:140]}); se usó el lector de tablas.")
    if r is None:
        for tabla in sorted(contenido.tablas, key=len, reverse=True):
            r = srv.desde_tabla(tabla, titulo=nombre.rsplit(".", 1)[0])
            if r:
                origen = "lector de tablas"
                break
    if r is None:
        r, origen = srv.plantilla_base(), "plantilla (archivo no interpretable)"
        notas.append("No se pudo reconocer la estructura de la rúbrica en el archivo. Se creó una plantilla para "
                     "completarla a mano. Con un modelo de IA configurado se interpretan también rúbricas en texto libre.")
    if not r.titulo:
        r.titulo = f"Rúbrica — {lab.titulo}"
    r.notas_interpretacion = notas + r.notas_interpretacion
    rv = _guardar_borrador(db, lab, r, u, origen, arch.id, modelo)
    db.commit()
    return _rv(rv)


def _obtener_rv(db: Session, rid: int) -> RubricaVersion:
    rv = db.get(RubricaVersion, rid)
    if not rv:
        raise HTTPException(404, "Rúbrica no encontrada.")
    return rv


@router.get("/rubricas/{rid}")
def ver_rubrica(rid: int, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    rv = _obtener_rv(db, rid)
    if not es_docente(u) and rv.estado != "validada":
        raise HTTPException(403, "Esta rúbrica aún no está publicada.")
    return _rv(rv)


@router.post("/rubricas/comprobar")
def comprobar(r: srv.Rubrica, u: Usuario = Depends(docente_o_admin)):
    """Valida una rúbrica sin guardarla (para el editor)."""
    inc = srv.validar(r)
    return {"inconsistencias": [i.model_dump() for i in inc], "suma_ponderaciones": round(sum(c.ponderacion for c in r.criterios), 2),
            "lista_para_validar": not srv.tiene_errores(inc)}


@router.put("/rubricas/{rid}")
def guardar_rubrica(rid: int, r: srv.Rubrica, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    rv = _obtener_rv(db, rid)
    if rv.estado != "borrador":
        raise HTTPException(409, "Una versión validada no se modifica: crea una nueva versión a partir de ella.")
    srv.completar_ids(r)
    rv.contenido, rv.hash = r.model_dump(), srv.hash_rubrica(r)
    rv.inconsistencias = [i.model_dump() for i in srv.validar(r)]
    db.commit()
    return _rv(rv)


@router.post("/rubricas/{rid}/normalizar")
def normalizar(rid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    rv = _obtener_rv(db, rid)
    if rv.estado != "borrador":
        raise HTTPException(409, "Solo se pueden normalizar borradores.")
    r = srv.normalizar_ponderaciones(srv.Rubrica.model_validate(rv.contenido))
    rv.contenido, rv.hash = r.model_dump(), srv.hash_rubrica(r)
    rv.inconsistencias = [i.model_dump() for i in srv.validar(r)]
    auditar(db, u, "rubrica_ponderaciones_normalizadas", "rubrica", rv.id)
    db.commit()
    return _rv(rv)


@router.post("/rubricas/{rid}/validar")
def validar(rid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    """Fija la versión: a partir de aquí es inmutable y puede usarse para evaluar."""
    rv = _obtener_rv(db, rid)
    r = srv.Rubrica.model_validate(rv.contenido)
    inc = srv.validar(r)
    rv.inconsistencias = [i.model_dump() for i in inc]
    if srv.tiene_errores(inc):
        db.commit()
        raise HTTPException(422, "La rúbrica tiene inconsistencias que impiden evaluar. Corrígelas y vuelve a intentarlo.")
    rv.estado, rv.validada_en = "validada", ahora()
    auditar(db, u, "rubrica_validada", "rubrica", rv.id, {"version": rv.version, "hash": rv.hash})
    db.commit()
    return _rv(rv)


@router.delete("/rubricas/{rid}")
def borrar_rubrica(rid: int, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    rv = _obtener_rv(db, rid)
    if rv.estado != "borrador":
        raise HTTPException(409, "Las versiones validadas se conservan para la trazabilidad de las evaluaciones.")
    db.delete(rv)
    db.commit()
    return {"ok": True}
