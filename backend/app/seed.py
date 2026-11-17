"""Datos de demostración (SEED_DEMO=true). Crea cuentas, laboratorios con rúbrica
validada, entregas y evaluaciones en distintos estados usando el proveedor
simulado, para que la plataforma pueda recorrerse sin clave de API."""
from __future__ import annotations

import hashlib
import io
import logging
import zipfile
from datetime import date
from pathlib import Path

from sqlalchemy import select

from . import seed_datos as D
from .db import SesionLocal
from .models import Archivo, Cohorte, Entrega, Evaluacion, Integrante, Laboratorio, RubricaVersion, Usuario, ahora
from .security import hash_password
from .services import evaluacion as motor
from .services import rubricas as srv_rub

log = logging.getLogger("asesor.seed")

CUENTAS = [
    ("Docente Demo", "docente@demo.edu.co", "Docente2026", "docente", ""),
    ("Laura Gómez (demo)", "laura@demo.edu.co", "Estudiante2026", "estudiante", "20261001"),
    ("Andrés Ríos (demo)", "andres@demo.edu.co", "Estudiante2026", "estudiante", "20261002"),
]


def sembrar_equipo() -> None:
    with SesionLocal() as db:
        if not db.scalars(select(Integrante)).first():
            carpeta = Path(__file__).parent / "equipo"
            for i, (nombre, rol, aporte, foto) in enumerate(D.EQUIPO_PLANTILLA, 1):
                integrante = Integrante(nombre=nombre, rol=rol, orden=i, descripcion=aporte)
                ruta = carpeta / foto
                if foto and ruta.is_file():
                    datos = ruta.read_bytes()
                    integrante.foto_id = _archivo(db, foto, "image/jpeg", datos, None).id
                db.add(integrante)
            db.commit()


def _pdf(titulo: str, autor: str, secciones: list[tuple[str, str]]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    est = getSampleStyleSheet()
    cuerpo = [Paragraph(titulo, est["Title"]), Paragraph(f"Informe de laboratorio — {autor}", est["Normal"]), Spacer(1, 14)]
    for sub, texto in secciones:
        cuerpo += [Paragraph(sub, est["Heading2"]), Paragraph(texto, est["BodyText"]), Spacer(1, 8)]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=letter, title=titulo, author=autor).build(cuerpo)
    return buf.getvalue()


def _zip(archivos: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, texto in sorted(archivos.items()):
            info = zipfile.ZipInfo(nombre, date_time=(2026, 11, 1, 12, 0, 0))  # fecha fija → ZIP reproducible
            z.writestr(info, texto)
    return buf.getvalue()


def _archivo(db, nombre: str, mime: str, datos: bytes, uid: int | None) -> Archivo:
    a = Archivo(nombre=nombre, mime=mime, tamano=len(datos), sha256=hashlib.sha256(datos).hexdigest(), contenido=datos, subido_por=uid)
    db.add(a)
    db.flush()
    return a


def _variante_debil(clave: str) -> dict[str, str]:
    """Entregas con los vacíos típicos: sin pruebas, una prueba que falla o un error de sintaxis."""
    base = dict(D.CODIGO[clave])
    if clave == "busqueda":
        return {"busqueda.py": base["busqueda.py"].split("def manhattan")[0]}
    if clave == "knn":
        base["knn.py"] = base["knn.py"].replace("return aciertos / len(reales)", "return aciertos / (len(reales) + 1)")
        return base
    if clave == "perceptron":
        base["perceptron.py"] = base["perceptron.py"].replace("def predecir(pesos, sesgo, x):", "def predecir(pesos, sesgo, x)")
        return base
    return {k: v for k, v in base.items() if not k.startswith("test_")}


def sembrar() -> None:
    try:
        _sembrar()
    except Exception:  # noqa: BLE001
        log.exception("No se pudieron crear los datos de demostración")


def _sembrar() -> None:
    with SesionLocal() as db:
        if db.scalars(select(Laboratorio)).first():
            return
        usuarios = {}
        for nombre, email, clave, rol, codigo in CUENTAS:
            u = db.scalars(select(Usuario).where(Usuario.email == email)).first()
            if not u:
                u = Usuario(nombre=nombre, email=email, password_hash=hash_password(clave), rol=rol, codigo=codigo)
                db.add(u)
                db.flush()
            usuarios[email] = u
        docente = usuarios["docente@demo.edu.co"]
        cohortes = {c.numero: c for c in db.scalars(select(Cohorte))}
        for n, periodo in ((1, "2026-1"), (2, "2026-2")):
            if n not in cohortes:
                cohortes[n] = Cohorte(numero=n, nombre=f"Cohorte {n}")
                db.add(cohortes[n])
            cohortes[n].periodo = cohortes[n].periodo or periodo
        db.flush()
        labs = {}
        for d in D.LABS:
            lab = Laboratorio(cohorte_id=cohortes[d["cohorte"]].id, orden=d["orden"], titulo=d["titulo"], descripcion=d["descripcion"],
                              objetivos=d["objetivos"], fecha=date.fromisoformat(d["fecha"]))
            db.add(lab)
            db.flush()
            r = srv_rub.Rubrica.model_validate(d["rubrica"])
            db.add(RubricaVersion(laboratorio_id=lab.id, version=1, estado="validada", contenido=r.model_dump(),
                                  inconsistencias=[i.model_dump() for i in srv_rub.validar(r)], hash=srv_rub.hash_rubrica(r),
                                  origen="datos de demostración", creado_por=docente.id, validada_en=ahora()))
            labs[d["clave"]] = lab
        db.commit()

        # (estudiante, laboratorio, variante, estado final de la evaluación | None = sin evaluar)
        plan = [("laura@demo.edu.co", c, "fuerte", "publicada") for c in D.CODIGO]
        plan += [("andres@demo.edu.co", "busqueda", "debil", "publicada"), ("andres@demo.edu.co", "knn", "debil", "publicada"),
                 ("andres@demo.edu.co", "perceptron", "debil", "aprobada"), ("andres@demo.edu.co", "prompts", "debil", "preliminar"),
                 ("andres@demo.edu.co", "agente", "debil", None)]
        pendientes = []
        for email, clave, variante, estado in plan:
            est, lab = usuarios[email], labs[clave]
            rv = lab.rubricas[-1]
            secciones = D.INFORMES[clave] if variante == "fuerte" else D.INFORMES_DEBIL[clave]
            codigo = D.CODIGO[clave] if variante == "fuerte" else _variante_debil(clave)
            inf = _archivo(db, f"informe_{clave}.pdf", "application/pdf", _pdf(lab.titulo, est.nombre, secciones), est.id)
            cod = _archivo(db, f"codigo_{clave}.zip", "application/zip", _zip(codigo), est.id)
            e = Entrega(laboratorio_id=lab.id, estudiante_id=est.id, numero=1, rubrica_version_id=rv.id, informe_id=inf.id,
                        codigo_id=cod.id, comentario="Entrega de demostración.")
            db.add(e)
            db.flush()
            if estado:
                ev = Evaluacion(entrega_id=e.id, rubrica_version_id=rv.id, estado="en_cola", creado_por=docente.id)
                db.add(ev)
                db.flush()
                pendientes.append((ev.id, estado))
        db.commit()

    for ev_id, estado in pendientes:
        motor.ejecutar(ev_id, SesionLocal, simulado=True)
        with SesionLocal() as db:
            ev = db.get(Evaluacion, ev_id)
            if ev.estado != "preliminar" or estado == "preliminar":
                continue
            docente = db.scalars(select(Usuario).where(Usuario.email == "docente@demo.edu.co")).first()
            ev.estado, ev.nota_final, ev.aprobado_por, ev.aprobado_en = estado, ev.calculo["nota"], docente.id, ahora()
            if estado == "publicada":
                ev.publicado_en = ahora()
            db.commit()
    log.info("Datos de demostración creados: %d evaluaciones", len(pendientes))
