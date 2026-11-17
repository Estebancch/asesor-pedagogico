"""Informe integral del aprendizaje: consolida todos los laboratorios de las dos
cohortes. Los números (promedios, niveles, evolución, brechas) los calcula el
backend; el modelo de IA solo redacta la síntesis y el plan a partir de ellos."""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..models import Usuario
from . import mapa as servicio_mapa
from .consolidado import nota_de, vigentes
from .ia import ErrorIA, generar_estructurado, obtener_proveedor
from .ia.simulado import Simulado
from .rubricas import Rubrica
from .taxonomia import etiqueta_dominio

UMBRAL_BRECHA = 3.5


class AccionPlan(BaseModel):
    objetivo: str = Field(description="Meta concreta y medible")
    acciones: list[str] = Field(description="Actividades específicas que debe hacer el estudiante")
    recursos: list[str] = Field(default_factory=list, description="Tipos de recursos o temas a estudiar (sin inventar URL)")
    plazo: str = ""
    indicador: str = Field(default="", description="Cómo sabrá que lo logró")


class NarrativaInforme(BaseModel):
    resumen_ejecutivo: str
    competencias_adquiridas: list[str]
    conocimientos_aplicados: list[str]
    evolucion: str = Field(description="Lectura de la evolución entre laboratorios y entre cohortes")
    oportunidades: list[str]
    plan: list[AccionPlan]


SISTEMA_INFORME = (
    "Eres un asesor pedagógico. A partir de los datos consolidados (ya calculados y validados por el sistema) redacta en "
    "español un informe integral de aprendizaje para un estudiante de un curso de Inteligencia Artificial. No inventes "
    "notas, laboratorios ni temas: usa solo lo que aparece en los datos. No recalcules promedios. El plan de "
    "fortalecimiento debe atacar las brechas listadas, con acciones concretas y realizables en pocas semanas. "
    "El plan nunca queda vacío: si no hay brechas, propone profundizar en la competencia o los temas con menor puntaje y "
    "completar los laboratorios sin evaluar. Escribe los decimales con coma (4,5). "
    "No incluyas direcciones web. Tutea al estudiante. Responde solo con el JSON del esquema.")


def _n(t: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()).strip()


def consolidar(db: Session, estudiante: Usuario, alcance: str = "publicadas") -> dict:
    labs, comp_acum, brechas = [], {}, []
    aprendio, aplico = [], []
    for lab, entrega, ev in vigentes(db, estudiante.id, alcance):
        fila = {"laboratorio_id": lab.id, "titulo": lab.titulo, "cohorte": lab.cohorte.numero, "cohorte_nombre": lab.cohorte.nombre,
                "orden": lab.orden, "etiqueta": f"C{lab.cohorte.numero}·L{lab.orden}", "fecha": lab.fecha.isoformat() if lab.fecha else None,
                "entregado": entrega is not None, "evaluacion_id": ev.id if ev else None, "estado": ev.estado if ev else None,
                "nota": None, "nivel": None, "resumen": "", "competencias": [], "fortalezas": [], "debilidades": []}
        if ev:
            nota = nota_de(ev)
            rub = Rubrica.model_validate(ev.rubrica_version.contenido)
            fila.update({"nota": nota, "nivel": etiqueta_dominio(nota), "resumen": ev.resultado.get("resumen", ""),
                         "competencias": ev.calculo.get("por_competencia", []),
                         "fortalezas": ev.resultado.get("fortalezas", [])[:4], "debilidades": ev.resultado.get("debilidades", [])[:4],
                         "modelo": f"{ev.proveedor}/{ev.modelo}", "rubrica_version": ev.rubrica_version.version})
            aprendio += [(lab.titulo, x) for x in ev.resultado.get("que_aprendio", [])[:3]]
            aplico += [(lab.titulo, x) for x in ev.resultado.get("como_lo_aplico", [])[:3]]
            for c in fila["competencias"]:
                a = comp_acum.setdefault(_n(c["competencia"]), {"nombre": c["competencia"], "suma": 0.0, "peso": 0.0, "serie": []})
                a["suma"] += c["puntaje"] * c["peso"]
                a["peso"] += c["peso"]
                a["serie"].append({"etiqueta": fila["etiqueta"], "laboratorio": lab.titulo, "cohorte": lab.cohorte.numero, "puntaje": c["puntaje"]})
            criterios = {c["criterio_id"]: c for c in ev.resultado.get("criterios", [])}
            for d in ev.calculo.get("desglose", []):
                if d["puntaje"] < UMBRAL_BRECHA:
                    comp = next((c.nombre for c in rub.competencias if c.id == d["competencia_id"]), "")
                    brechas.append({"tipo": "criterio", "nombre": d["criterio"], "competencia": comp, "puntaje": d["puntaje"],
                                    "nivel": d["nivel"], "laboratorio": lab.titulo, "etiqueta": fila["etiqueta"],
                                    "debilidades": criterios.get(d["criterio_id"], {}).get("debilidades", [])[:3],
                                    "recomendaciones": criterios.get(d["criterio_id"], {}).get("recomendaciones", [])[:3]})
        labs.append(fila)

    evaluados = [l for l in labs if l["nota"] is not None]
    notas = [l["nota"] for l in evaluados]
    promedio = round(sum(notas) / len(notas), 2) if notas else None
    por_cohorte = {}
    for n in sorted({l["cohorte"] for l in labs}):
        ns = [l["nota"] for l in evaluados if l["cohorte"] == n]
        por_cohorte[str(n)] = round(sum(ns) / len(ns), 2) if ns else None
    competencias = sorted(({"nombre": a["nombre"], "puntaje": round(a["suma"] / a["peso"], 2), "nivel": etiqueta_dominio(a["suma"] / a["peso"]),
                            "laboratorios": len(a["serie"]), "serie": a["serie"]} for a in comp_acum.values() if a["peso"] > 0),
                          key=lambda c: -c["puntaje"])
    # Tendencia: pendiente de la recta de mínimos cuadrados sobre las notas en orden cronológico
    pendiente = None
    if len(notas) >= 2:
        n = len(notas)
        mx, my = (n - 1) / 2, sum(notas) / n
        den = sum((i - mx) ** 2 for i in range(n))
        pendiente = round(sum((i - mx) * (y - my) for i, y in enumerate(notas)) / den, 3) if den else 0.0
    c1, c2 = por_cohorte.get("1"), por_cohorte.get("2")
    delta = round(c2 - c1, 2) if c1 is not None and c2 is not None else None
    if pendiente is None:
        texto_t = "Aún no hay suficientes laboratorios evaluados para describir una tendencia."
    else:
        sentido = "ascendente" if pendiente > 0.05 else "descendente" if pendiente < -0.05 else "estable"
        texto_t = f"Tendencia {sentido} ({pendiente:+.2f} puntos por laboratorio).".replace(".", ",", 1)
        if delta is not None:
            texto_t += f" Entre cohortes el promedio pasó de {c1:.2f} a {c2:.2f} ({delta:+.2f}).".replace(".", ",", 3)
    mapa = servicio_mapa.construir(db, estudiante, alcance)
    temas = sorted(({"nombre": n["nombre"], "dominio": n["dominio"], "nivel": n["dominio_etiqueta"],
                     "laboratorios": len(n["laboratorios"]), "aspectos": n["aspectos"][:3]}
                    for n in mapa["nodos"] if n["tipo"] == "tema"), key=lambda t: -(t["dominio"] or 0))
    for c in competencias:
        if c["puntaje"] < UMBRAL_BRECHA:
            brechas.append({"tipo": "competencia", "nombre": c["nombre"], "competencia": c["nombre"], "puntaje": c["puntaje"],
                            "nivel": c["nivel"], "laboratorio": "", "etiqueta": "", "debilidades": [], "recomendaciones": []})
    brechas.sort(key=lambda b: (b["puntaje"], b["tipo"]))
    return {
        "estudiante": {"id": estudiante.id, "nombre": estudiante.nombre, "codigo": estudiante.codigo, "email": estudiante.email},
        "alcance": alcance, "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_laboratorios": len(labs), "entregados": sum(1 for l in labs if l["entregado"]), "evaluados": len(evaluados),
        "promedio": promedio, "nivel_global": etiqueta_dominio(promedio), "promedio_por_cohorte": por_cohorte,
        "laboratorios": labs, "competencias": competencias, "temas": temas,
        "evolucion": [{"etiqueta": l["etiqueta"], "titulo": l["titulo"], "cohorte": l["cohorte"], "nota": l["nota"]} for l in evaluados],
        "tendencia": {"pendiente": pendiente, "delta_cohortes": delta, "texto": texto_t},
        "tendencia_texto": texto_t, "brechas": brechas[:12],
        "aprendizajes": [{"laboratorio": a, "texto": b} for a, b in aprendio[:12]],
        "aplicaciones": [{"laboratorio": a, "texto": b} for a, b in aplico[:12]],
    }


def redactar(db: Session, datos: dict) -> tuple[dict, str]:
    """Devuelve (narrativa, modelo). Si el proveedor falla, se usa una redacción
    determinista para que el informe siempre pueda generarse."""
    import json
    compacto = {k: datos[k] for k in ("promedio", "nivel_global", "promedio_por_cohorte", "total_laboratorios", "evaluados",
                                      "competencias", "temas", "tendencia_texto", "brechas", "aprendizajes", "aplicaciones")}
    compacto["laboratorios"] = [{k: l[k] for k in ("etiqueta", "titulo", "nota", "nivel", "resumen", "fortalezas", "debilidades")}
                                for l in datos["laboratorios"] if l["nota"] is not None]
    contexto = {"tarea": "informe", "datos": compacto}
    proveedor, cfg = obtener_proveedor(db)
    try:
        obj, _ = generar_estructurado(proveedor, NarrativaInforme, sistema=SISTEMA_INFORME,
                                      usuario="Datos consolidados del estudiante (JSON):\n" + json.dumps(compacto, ensure_ascii=False),
                                      contexto=contexto)
        return obj.model_dump(), f"{cfg['proveedor']}/{cfg['modelo']}"
    except ErrorIA as e:
        obj, _ = generar_estructurado(Simulado(modelo="heuristico-v1"), NarrativaInforme, sistema="", usuario="", contexto=contexto)
        d = obj.model_dump()
        d["aviso"] = f"La redacción con IA no estuvo disponible ({str(e)[:160]}); se usó una síntesis automática."
        return d, "simulado/heuristico-v1"


# --- PDF ----------------------------------------------------------------------------------

def a_pdf(datos: dict, narrativa: dict | None, modelo: str = "") -> bytes:
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.graphics.widgets.markers import makeMarker
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    tinta, acento, gris = colors.HexColor("#14323A"), colors.HexColor("#0B6E69"), colors.HexColor("#5B6B6E")
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Title"], textColor=tinta, fontSize=20, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], textColor=acento, fontSize=13, spaceBefore=14, spaceAfter=6)
    p = ParagraphStyle("p", parent=base["BodyText"], fontSize=9.5, leading=13.5, textColor=tinta)
    chico = ParagraphStyle("chico", parent=p, fontSize=8, textColor=gris)
    celda = ParagraphStyle("celda", parent=p, fontSize=8.5, leading=11)

    def P(t, estilo=p):
        return Paragraph(escape(str(t)), estilo)

    def tabla(filas, anchos, cabecera=True):
        t = Table(filas, colWidths=anchos, repeatRows=1 if cabecera else 0)
        estilo = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3D4")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
        if cabecera:
            estilo += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EFEF")), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
        t.setStyle(TableStyle(estilo))
        return t

    est = datos["estudiante"]
    fmt = lambda x: "—" if x is None else f"{x:.1f}".replace(".", ",")  # noqa: E731
    cuerpo = [P("Informe integral del aprendizaje", h1),
              P(f"{est['nombre']}" + (f" · código {est['codigo']}" if est.get("codigo") else ""), p),
              P(f"Curso de Inteligencia Artificial, cohortes 1 y 2 · generado el {datos['generado_en'][:10]} · "
                f"alcance: evaluaciones {'publicadas' if datos['alcance'] == 'publicadas' else 'publicadas, aprobadas y preliminares'}", chico),
              Spacer(1, 8)]
    resumen = [[P("Promedio general", chico), P("Nivel", chico), P("Laboratorios evaluados", chico), P("Cohorte 1", chico), P("Cohorte 2", chico)],
               [P(fmt(datos["promedio"]), h2), P(datos["nivel_global"], h2), P(f"{datos['evaluados']} de {datos['total_laboratorios']}", h2),
                P(fmt(datos["promedio_por_cohorte"].get("1")), h2), P(fmt(datos["promedio_por_cohorte"].get("2")), h2)]]
    cuerpo.append(tabla(resumen, [3.4 * cm] * 5, cabecera=False))
    if narrativa:
        cuerpo += [P("Síntesis", h2), P(narrativa.get("resumen_ejecutivo", ""))]
        if narrativa.get("aviso"):
            cuerpo.append(P(narrativa["aviso"], chico))
    cuerpo.append(P("Valoraciones por laboratorio", h2))
    filas = [["Cohorte", "Laboratorio", "Nota", "Nivel", "Estado"]]
    for l in datos["laboratorios"]:
        filas.append([P(l["cohorte_nombre"], celda), P(l["titulo"], celda), fmt(l["nota"]), l["nivel"] or "—",
                      (l["estado"] or ("sin evaluar" if l["entregado"] else "sin entrega")).capitalize()])
    cuerpo.append(tabla(filas, [2.6 * cm, 8.2 * cm, 1.5 * cm, 2.2 * cm, 2.5 * cm]))

    ev = datos["evolucion"]
    if len(ev) >= 2:
        cuerpo.append(P("Evolución del aprendizaje", h2))
        d = Drawing(480, 150)
        lp = LinePlot()
        lp.x, lp.y, lp.width, lp.height = 30, 25, 430, 105
        lp.data = [[(i + 1, e["nota"]) for i, e in enumerate(ev)]]
        lp.lines[0].strokeColor, lp.lines[0].strokeWidth = acento, 2
        lp.lines[0].symbol = makeMarker("FilledCircle")
        lp.lines[0].symbol.fillColor, lp.lines[0].symbol.size = acento, 5
        lp.yValueAxis.valueMin, lp.yValueAxis.valueMax, lp.yValueAxis.valueStep = 0, 5, 1
        lp.xValueAxis.valueMin, lp.xValueAxis.valueMax, lp.xValueAxis.valueStep = 0.5, len(ev) + 0.5, 1
        lp.xValueAxis.labelTextFormat = lambda v: ev[int(round(v)) - 1]["etiqueta"] if 1 <= round(v) <= len(ev) else ""
        lp.xValueAxis.labels.fontSize = lp.yValueAxis.labels.fontSize = 7
        d.add(lp)
        d.add(String(30, 138, "Nota (0,0 a 5,0) por laboratorio, en orden cronológico", fontSize=7.5, fillColor=gris))
        cuerpo += [d, P((narrativa or {}).get("evolucion") or datos["tendencia"]["texto"])]
    if datos["competencias"]:
        cuerpo.append(P("Competencias y niveles de dominio", h2))
        filas = [["Competencia", "Puntaje", "Nivel", "Laboratorios"]]
        filas += [[P(c["nombre"], celda), fmt(c["puntaje"]), c["nivel"], str(c["laboratorios"])] for c in datos["competencias"]]
        cuerpo.append(tabla(filas, [10.3 * cm, 2 * cm, 2.4 * cm, 2.3 * cm]))
    if narrativa:
        for titulo, clave in (("Competencias adquiridas", "competencias_adquiridas"), ("Conocimientos aplicados", "conocimientos_aplicados"),
                              ("Oportunidades de fortalecimiento", "oportunidades")):
            if narrativa.get(clave):
                cuerpo.append(P(titulo, h2))
                cuerpo += [P("• " + x) for x in narrativa[clave]]
    if datos["brechas"]:
        cuerpo.append(P("Brechas identificadas", h2))
        filas = [["Aspecto", "Puntaje", "Laboratorio", "Qué mejorar"]]
        for b in datos["brechas"]:
            filas.append([P(b["nombre"], celda), fmt(b["puntaje"]), P(b["laboratorio"] or "Varias entregas", celda),
                          P("; ".join(b["debilidades"] or b["recomendaciones"]) or "—", celda)])
        cuerpo.append(tabla(filas, [4.8 * cm, 1.5 * cm, 4 * cm, 6.7 * cm]))
    if narrativa and narrativa.get("plan"):
        cuerpo.append(P("Plan personalizado de fortalecimiento", h2))
        for i, a in enumerate(narrativa["plan"], 1):
            cuerpo.append(P(f"{i}. {a['objetivo']}", ParagraphStyle("b", parent=p, fontName="Helvetica-Bold", spaceBefore=6)))
            cuerpo += [P("• " + x) for x in a.get("acciones", [])]
            extra = " · ".join(x for x in (("Recursos: " + ", ".join(a["recursos"])) if a.get("recursos") else "",
                                            ("Plazo: " + a["plazo"]) if a.get("plazo") else "",
                                            ("Indicador: " + a["indicador"]) if a.get("indicador") else "") if x)
            if extra:
                cuerpo.append(P(extra, chico))
    cuerpo += [Spacer(1, 14), P("Trazabilidad: las notas se calculan en el servidor con las ponderaciones de cada rúbrica; "
                                "las valoraciones fueron generadas con asistencia de IA" + (f" ({modelo})" if modelo else "") +
                                " y están sujetas a revisión y aprobación docente. Cada evaluación conserva evidencias, versión "
                                "de rúbrica, modelo y resultados de pruebas.", chico)]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                      title="Informe integral del aprendizaje", author="Asesor Pedagógico Inteligente").build(cuerpo)
    return buf.getvalue()
