"""Proveedor «simulado»: heurístico, determinista y sin red.

NO es un modelo de IA. Existe para (1) probar la plataforma de extremo a
extremo sin clave de API, (2) las pruebas automáticas y (3) tener datos de
demostración. La interfaz lo rotula siempre como «modo simulado»."""
from __future__ import annotations

import re
import unicodedata

from ..taxonomia import TEMAS
from .base import ProveedorIA, RespuestaIA

VACIAS = set("""para como este esta estos estas donde cuando sobre entre desde hasta tiene tienen cada todo toda todos
todas pero porque aunque mediante segun dentro fuera ademas tambien solo sola muy mas menos bien mal nivel criterio
criterios estudiante estudiantes laboratorio trabajo forma manera parte partes debe deben puede pueden hace hacen
presenta evidencia evidencias aplica aplicacion correcta correctamente adecuada adecuadamente completa clara claro
ningun ninguna alguna algunos algunas uso usa usar""".split())


def _n(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def _claves(texto: str) -> list[str]:
    vistas, out = set(), []
    for p in re.findall(r"[a-z0-9_\*\-]{4,}", _n(texto)):
        if p not in VACIAS and p not in vistas:
            vistas.add(p)
            out.append(p)
    return out[:14]


class Simulado(ProveedorIA):
    nombre = "simulado"

    def generar_json(self, *, sistema, usuario, esquema, adjuntos=None, contexto=None) -> RespuestaIA:
        ctx = contexto or {}
        tarea = ctx.get("tarea")
        if tarea == "evaluacion":
            datos = self._evaluar(ctx)
        elif tarea == "informe":
            datos = self._informe(ctx)
        else:
            datos = {}
        return RespuestaIA(texto="", datos=datos, modelo="heuristico-v1",
                           uso={"tokens_entrada": 0, "tokens_salida": 0, "tokens_total": 0})

    # ------------------------------------------------------------------------
    def _evaluar(self, ctx: dict) -> dict:
        rub, fuentes, ver = ctx["rubrica"], ctx["fuentes"], ctx.get("verificacion", {})
        niveles = sorted(rub["niveles"], key=lambda n: -n["puntaje"])
        lineas = []  # (fuente, linea original, normalizada)
        for fid, texto in fuentes.items():
            if fid.startswith("verificacion:"):
                continue
            for ln in texto.splitlines():
                s = ln.strip()
                if 25 <= len(s) <= 400:
                    lineas.append((fid, s, _n(s)))
        todo = _n("\n".join(fuentes.values()))
        sint = ver.get("sintaxis", {}).get("estado")
        prue = ver.get("pruebas", {})
        criterios = []
        for c in rub["criterios"]:
            desc_top = (c.get("descriptores") or {}).get(niveles[0]["id"], "") if niveles else ""
            claves = _claves(f"{c['nombre']} {c.get('descripcion', '')} {desc_top}")
            presentes = [k for k in claves if k in todo]
            cobertura = len(presentes) / max(len(claves), 1)
            idx = 0 if cobertura >= 0.6 else 1 if cobertura >= 0.4 else 2 if cobertura >= 0.2 else 3
            nombre_n = _n(c["nombre"] + " " + c.get("descripcion", ""))
            debil, fuerte = [], []
            if re.search(r"prueba|test|verificaci", nombre_n):
                if prue.get("estado") == "ok":
                    idx = min(idx, 1)
                    fuerte.append(f"Las {prue.get('total', 0)} pruebas unitarias se ejecutaron y pasaron en el sandbox.")
                elif prue.get("estado") in ("falla", "error"):
                    idx = max(idx, 2)
                    debil.append(f"Hay pruebas que no pasan ({prue.get('fallidas', 0)} fallidas, {prue.get('errores', 0)} con error).")
                elif prue.get("estado") == "sin_pruebas":
                    idx = max(idx, 3)
                    debil.append("La entrega no incluye pruebas unitarias.")
            if re.search(r"codigo|implement|funcional|program|algoritm", nombre_n) and sint == "falla":
                idx = max(idx, 2)
                debil.append("El código tiene errores de sintaxis: no se puede ejecutar tal como se entregó.")
            idx = min(idx, len(niveles) - 1)
            puntuadas = sorted(((sum(1 for k in presentes if k in ln_n), -len(s), fid, s) for fid, s, ln_n in lineas),
                               reverse=True)
            citas = []
            usadas: set[str] = set()
            for pts, _, fid, s in puntuadas:
                if pts == 0 or len(citas) >= 2:
                    break
                if s in usadas:
                    continue
                usadas.add(s)
                citas.append({"fuente": fid, "cita": s[:240],
                              "explicacion": "Fragmento que trata lo que pide el criterio (coincidencia de términos)."})
            if not citas:
                debil.append("No se encontró en la entrega un fragmento que responda directamente a este criterio.")
            if cobertura >= 0.4:
                fuerte.append("La entrega aborda los elementos centrales del criterio: " + ", ".join(presentes[:5]) + ".")
            else:
                faltan = [k for k in claves if k not in presentes][:4]
                if faltan:
                    debil.append("No se evidencian con claridad: " + ", ".join(faltan) + ".")
            criterios.append({
                "criterio_id": c["id"], "nivel_id": niveles[idx]["id"],
                "justificacion": (f"Valoración heurística (modo simulado): la entrega cubre {round(cobertura * 100)} % de los "
                                  f"términos clave del criterio, lo que corresponde al nivel «{niveles[idx]['nombre']}». "
                                  "Un modelo de IA real analizaría el contenido, no solo los términos."),
                "evidencias": citas, "fortalezas": fuerte, "debilidades": debil,
                "recomendaciones": ([f"Refuerza «{c['nombre']}»: documenta y demuestra con un ejemplo ejecutable lo que pide el descriptor del nivel más alto."]
                                    if idx > 0 else ["Mantén este nivel y explica las decisiones de diseño que tomaste."]),
                "confianza": "baja",
            })
        temas = []
        ids_crit = [c["id"] for c in rub["criterios"]]
        puntuados = []
        for tid, (cat, nombre, claves, _) in TEMAS.items():
            n = sum(todo.count(_n(k)) for k in claves)
            distintos = [k for k in claves if _n(k) in todo]
            if len(distintos) >= 3 or (len(distintos) >= 2 and n >= 6):
                puntuados.append((len(distintos), n, tid, cat, nombre, distintos))
        for _, _, tid, cat, nombre, distintos in sorted(puntuados, reverse=True)[:5]:
            temas.append({"tema_id": tid, "nombre": nombre, "categoria": cat, "conceptos": distintos[:6],
                          "criterios_relacionados": ids_crit,
                          "aprendizaje_evidenciado": "La entrega trabaja este tema: aparecen " + ", ".join(distintos[:4]) + ".",
                          "aspectos_a_profundizar": [f"Explicar con tus palabras cuándo conviene usar {nombre.lower()} y sus límites."],
                          "relacionados": []})
        debiles = [c for c in criterios if c["debilidades"]]
        return {
            "resumen": "Resultado generado en modo simulado (sin modelo de IA). Sirve para comprobar el flujo; configura un proveedor real para obtener un análisis pedagógico.",
            "que_aprendio": [t["aprendizaje_evidenciado"] for t in temas[:3]] or ["No se identificaron temas con suficiente evidencia."],
            "como_lo_aplico": ["Implementó la solución en " + ", ".join(ver.get("lenguajes", {}).keys()) + "." if ver.get("lenguajes") else "No se encontró código para analizar."],
            "que_fortalecer": [d for c in debiles for d in c["debilidades"]][:5] or ["Profundizar la justificación de las decisiones técnicas."],
            "criterios": criterios,
            "fortalezas_generales": [f for c in criterios for f in c["fortalezas"]][:4],
            "debilidades_generales": [d for c in criterios for d in c["debilidades"]][:4],
            "recomendaciones_personalizadas": [r for c in criterios for r in c["recomendaciones"]][:5],
            "temas": temas,
        }

    def _informe(self, ctx: dict) -> dict:
        d = ctx["datos"]
        n = lambda x: f"{x:.1f}".replace(".", ",")  # noqa: E731
        comps = sorted(d.get("competencias", []), key=lambda c: -c["puntaje"])
        brechas = d.get("brechas", [])
        evaluados, total = d.get("evaluados", 0), d.get("total_laboratorios", 0)
        plan = []
        for b in brechas[:5]:
            plan.append({"objetivo": f"Subir «{b['nombre']}» de {n(b['puntaje'])} a por lo menos 4,0",
                         "acciones": (b.get("recomendaciones") or ["Rehacer el laboratorio aplicando la retroalimentación recibida."])[:3],
                         "recursos": ["Material del curso sobre el tema", "Sesión de asesoría con el docente"],
                         "plazo": "3 semanas", "indicador": "Nueva entrega evaluada en nivel Alto o Superior"})
        if total > evaluados:
            plan.append({"objetivo": f"Completar los {total - evaluados} laboratorios que aún no tienen evaluación publicada",
                         "acciones": ["Entregar informe y código de cada laboratorio pendiente.",
                                      "Incluir pruebas unitarias para que la verificación técnica cuente como evidencia."],
                         "recursos": ["Enunciado y rúbrica de cada laboratorio"], "plazo": "Antes del cierre del periodo",
                         "indicador": f"{total} de {total} laboratorios evaluados"})
        if not brechas and comps:
            menor = comps[-1]
            plan.append({"objetivo": f"Profundizar en «{menor['nombre']}», tu competencia con menor puntaje ({n(menor['puntaje'])})",
                         "acciones": ["Revisar los criterios de esa competencia que no llegaron al nivel más alto y rehacer esa parte.",
                                      "Explicar por escrito las decisiones técnicas, no solo el resultado."],
                         "recursos": ["Retroalimentación por criterio de cada laboratorio"], "plazo": "4 semanas",
                         "indicador": "Todos los criterios de la competencia en el nivel más alto de la rúbrica"})
        return {
            "resumen_ejecutivo": (f"Informe generado en modo simulado. Promedio general {n(d.get('promedio') or 0)} sobre 5,0 en "
                                  f"{evaluados} de {total} laboratorios evaluados."),
            "competencias_adquiridas": [f"{c['nombre']}: nivel {c['nivel']} ({n(c['puntaje'])})" for c in comps if c["puntaje"] >= 4.0][:6],
            "conocimientos_aplicados": [t["nombre"] for t in d.get("temas", [])][:8],
            "evolucion": d.get("tendencia_texto", ""),
            "oportunidades": [f"{b['nombre']} ({n(b['puntaje'])})" for b in brechas[:6]],
            "plan": plan,
        }
