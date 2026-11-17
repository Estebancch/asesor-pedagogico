"""Consultas compartidas por el informe integral y el mapa mental."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Cohorte, Entrega, Evaluacion, Laboratorio

ESTADOS = {"publicadas": ("publicada",), "todas": ("preliminar", "aprobada", "publicada")}


def vigentes(db: Session, estudiante_id: int, alcance: str = "publicadas", cohorte: int | None = None):
    """Por cada laboratorio (ordenado por cohorte y orden): la última entrega del
    estudiante y su evaluación más reciente dentro del alcance.
    Devuelve [(laboratorio, entrega|None, evaluacion|None)]."""
    estados = ESTADOS.get(alcance, ESTADOS["publicadas"])
    q = select(Laboratorio).join(Cohorte).order_by(Cohorte.numero, Laboratorio.orden, Laboratorio.id)
    if cohorte:
        q = q.where(Cohorte.numero == cohorte)
    salida = []
    for lab in db.scalars(q):
        entregas = db.scalars(select(Entrega).where(Entrega.laboratorio_id == lab.id, Entrega.estudiante_id == estudiante_id)
                              .order_by(Entrega.id.desc())).all()
        entrega = entregas[0] if entregas else None
        evaluacion = None
        for e in entregas:  # la más reciente que tenga una evaluación dentro del alcance
            evaluacion = db.scalars(select(Evaluacion).where(Evaluacion.entrega_id == e.id, Evaluacion.estado.in_(estados))
                                    .order_by(Evaluacion.id.desc())).first()
            if evaluacion:
                entrega = e
                break
        salida.append((lab, entrega, evaluacion))
    return salida


def nota_de(ev: Evaluacion) -> float | None:
    return ev.nota_final if ev.nota_final is not None else ev.nota_preliminar
