"""Cálculo de la nota (0,0–5,0). Lo hace SIEMPRE el backend con las
ponderaciones y los puntajes de nivel definidos en la rúbrica; el modelo de IA
solo elige un nivel por criterio y nunca ve ni produce el número final."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .rubricas import Rubrica

FORMULA = "nota = Σ (ponderación_i / 100 × puntaje del nivel asignado al criterio i), redondeada a 1 decimal (mitad hacia arriba)"


def _d(x) -> Decimal:
    return Decimal(str(x))


def calcular(rubrica: Rubrica, criterios: list[dict]) -> dict:
    """`criterios`: [{criterio_id, nivel_id, puntaje_manual?}]"""
    niveles = {n.id: n for n in rubrica.niveles}
    por_id = {c["criterio_id"]: c for c in criterios}
    desglose, total, pendientes = [], Decimal("0"), []
    for c in rubrica.criterios:
        r = por_id.get(c.id, {})
        nivel = niveles.get(r.get("nivel_id") or "")
        manual = r.get("puntaje_manual")
        if manual is not None:
            puntaje = min(max(_d(manual), Decimal("0")), Decimal("5"))
        elif nivel is not None:
            puntaje = _d(nivel.puntaje)
        else:
            puntaje = Decimal("0")
            pendientes.append(c.id)
        aporte = _d(c.ponderacion) * puntaje / Decimal("100")
        total += aporte
        desglose.append({"criterio_id": c.id, "criterio": c.nombre, "competencia_id": c.competencia_id,
                         "ponderacion": c.ponderacion, "nivel_id": nivel.id if nivel else None,
                         "nivel": nivel.nombre if nivel else None, "puntaje": float(puntaje),
                         "origen_puntaje": "ajuste docente" if manual is not None else "nivel de la rúbrica",
                         "aporte": float(aporte.quantize(Decimal("0.0001")))})
    nota = float(min(max(total, Decimal("0")), Decimal("5")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    return {"nota": nota, "suma_exacta": float(total.quantize(Decimal("0.0001"))), "formula": FORMULA,
            "desglose": desglose, "criterios_pendientes": pendientes}


def por_competencia(rubrica: Rubrica, desglose: list[dict]) -> list[dict]:
    """Promedio ponderado por competencia (para informe y mapa)."""
    salida = []
    for comp in rubrica.competencias:
        items = [d for d in desglose if d["competencia_id"] == comp.id]
        peso = sum(d["ponderacion"] for d in items)
        if not items or peso <= 0:
            continue
        puntaje = sum(d["ponderacion"] * d["puntaje"] for d in items) / peso
        salida.append({"competencia_id": comp.id, "competencia": comp.nombre, "peso": round(peso, 2),
                       "puntaje": round(puntaje, 2)})
    return salida
