"""Mapa mental de competencias en IA: se genera automáticamente a partir de los
temas identificados en cada evaluación. El nivel de dominio de cada tema lo
calcula el backend con los criterios de la rúbrica que lo evidencian."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Usuario
from .consolidado import nota_de, vigentes
from .rubricas import slug
from .taxonomia import CATEGORIAS, TEMAS, etiqueta_dominio


def construir(db: Session, estudiante: Usuario, alcance: str = "publicadas", cohorte: int | None = None) -> dict:
    temas: dict[str, dict] = {}
    relaciones: set[tuple[str, str]] = set()
    labs_evaluados = 0
    for lab, entrega, ev in vigentes(db, estudiante.id, alcance, cohorte):
        if not ev:
            continue
        labs_evaluados += 1
        criterios = {c["criterio_id"]: c for c in ev.resultado.get("criterios", [])}
        for t in ev.resultado.get("temas", []):
            tid = t["tema_id"] if t["tema_id"] in TEMAS else "otro:" + slug(t.get("nombre", "tema"))
            nodo = temas.setdefault(tid, {
                "id": "tema:" + tid, "tipo": "tema", "tema_id": tid, "nombre": t["nombre"], "categoria": t["categoria"],
                "laboratorios": [], "evidencias": [], "conceptos": [], "aspectos": [], "_dominios": []})
            citas = []
            for cid in t.get("criterios_relacionados", []):
                for e in criterios.get(cid, {}).get("evidencias", []):
                    if e["estado"] in ("verificada", "parcial") and len(citas) < 2:
                        citas.append({"fuente": e["fuente"], "cita": e["cita"], "criterio": criterios[cid]["nombre"]})
            nodo["laboratorios"].append({"laboratorio_id": lab.id, "titulo": lab.titulo, "cohorte": lab.cohorte.numero,
                                         "cohorte_nombre": lab.cohorte.nombre, "nota": nota_de(ev),
                                         "dominio": t.get("dominio"), "evaluacion_id": ev.id, "estado": ev.estado})
            if t.get("aprendizaje_evidenciado"):
                nodo["evidencias"].append({"laboratorio": lab.titulo, "cohorte": lab.cohorte.numero,
                                           "texto": t["aprendizaje_evidenciado"], "citas": citas})
            for c in t.get("conceptos", []):
                if c and c.lower() not in {x.lower() for x in nodo["conceptos"]}:
                    nodo["conceptos"].append(c)
            for a in t.get("aspectos_a_profundizar", []):
                if a and a not in nodo["aspectos"]:
                    nodo["aspectos"].append(a)
            if t.get("dominio") is not None:
                nodo["_dominios"].append(t["dominio"])
            for r in t.get("relacionados", []):
                if r != tid:
                    relaciones.add(tuple(sorted((tid, r))))
    # Relaciones conceptuales conocidas de la taxonomía (solo entre temas presentes)
    for tid in list(temas):
        for r in TEMAS.get(tid, ("", "", [], []))[3]:
            if r in temas:
                relaciones.add(tuple(sorted((tid, r))))

    nodos, aristas = [], []
    raiz = {"id": "raiz", "tipo": "raiz", "nombre": "Competencias en IA", "subtitulo": estudiante.nombre}
    nodos.append(raiz)
    por_cat: dict[str, list[dict]] = {}
    for t in temas.values():
        doms = t.pop("_dominios")
        t["dominio"] = round(sum(doms) / len(doms), 2) if doms else None
        t["dominio_etiqueta"] = etiqueta_dominio(t["dominio"])
        t["cohortes"] = sorted({l["cohorte"] for l in t["laboratorios"]})
        t["conceptos"] = t["conceptos"][:12]
        t["requiere_profundizacion"] = t["dominio"] is not None and t["dominio"] < 3.5
        por_cat.setdefault(t["categoria"], []).append(t)
    for cat_id, cat_nombre in CATEGORIAS.items():
        hijos = sorted(por_cat.get(cat_id, []), key=lambda x: x["nombre"])
        if not hijos:
            continue
        doms = [h["dominio"] for h in hijos if h["dominio"] is not None]
        dom = round(sum(doms) / len(doms), 2) if doms else None
        nodos.append({"id": "cat:" + cat_id, "tipo": "categoria", "nombre": cat_nombre, "dominio": dom,
                      "dominio_etiqueta": etiqueta_dominio(dom), "temas": len(hijos)})
        aristas.append({"id": f"j:raiz-{cat_id}", "origen": "raiz", "destino": "cat:" + cat_id, "tipo": "jerarquia"})
        for h in hijos:
            nodos.append(h)
            aristas.append({"id": f"j:{cat_id}-{h['tema_id']}", "origen": "cat:" + cat_id, "destino": h["id"], "tipo": "jerarquia"})
    for a, b in sorted(relaciones):
        if a in temas and b in temas:
            aristas.append({"id": f"r:{a}-{b}", "origen": "tema:" + a, "destino": "tema:" + b, "tipo": "relacion"})
    lista = [n for n in nodos if n["tipo"] == "tema"]
    con_dom = [n["dominio"] for n in lista if n["dominio"] is not None]
    return {
        "estudiante": {"id": estudiante.id, "nombre": estudiante.nombre},
        "alcance": alcance, "cohorte": cohorte, "nodos": nodos, "aristas": aristas,
        "resumen": {"laboratorios_evaluados": labs_evaluados, "temas": len(lista),
                    "categorias": len([n for n in nodos if n["tipo"] == "categoria"]),
                    "dominio_promedio": round(sum(con_dom) / len(con_dom), 2) if con_dom else None,
                    "por_profundizar": [n["nombre"] for n in sorted(lista, key=lambda x: x["dominio"] or 9) if n["requiere_profundizacion"]]},
    }
