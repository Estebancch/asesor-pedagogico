"""Verificación técnica objetiva: sintaxis, análisis estático y pruebas unitarias.
Todo corre dentro del sandbox; aquí solo se orquesta y se interpreta la salida."""
from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter

from ..config import obtener_ajustes
from . import sandbox
from .extraccion import EXT_CODIGO

RE_PRUEBA = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.py)$")
RE_MODULO_FALTANTE = re.compile(r"No module named '([A-Za-z0-9_\.]+)'")


def _lenguajes(archivos: dict[str, bytes]) -> dict[str, int]:
    c: Counter = Counter()
    for ruta in archivos:
        ext = ruta.lower().rsplit(".", 1)[-1] if "." in ruta else ""
        if ext in EXT_CODIGO:
            c[EXT_CODIGO[ext]] += 1
    return dict(c)


def _leer_junit(ruta: str) -> dict | None:
    try:
        raiz = ET.parse(ruta).getroot()
    except (ET.ParseError, OSError):
        return None
    suites = [raiz] if raiz.tag == "testsuite" else list(raiz.iter("testsuite"))
    total = fallidas = errores = omitidas = 0
    detalle = []
    for s in suites:
        for caso in s.iter("testcase"):
            total += 1
            nombre = f"{caso.get('classname', '')}::{caso.get('name', '')}".strip(":")
            estado, mensaje = "aprobada", ""
            for hijo in caso:
                if hijo.tag == "failure":
                    estado, mensaje = "fallida", (hijo.get("message") or hijo.text or "")[:400]
                    fallidas += 1
                elif hijo.tag == "error":
                    estado, mensaje = "error", (hijo.get("message") or hijo.text or "")[:400]
                    errores += 1
                elif hijo.tag == "skipped":
                    estado, mensaje = "omitida", (hijo.get("message") or "")[:200]
                    omitidas += 1
            detalle.append({"nombre": nombre, "resultado": estado, "mensaje": mensaje})
    return {"total": total, "aprobadas": total - fallidas - errores - omitidas, "fallidas": fallidas,
            "errores": errores, "omitidas": omitidas, "detalle": detalle[:200]}


def verificar(archivos: dict[str, bytes], pruebas_docente: str = "") -> dict:
    aj = obtener_ajustes()
    lenguajes = _lenguajes(archivos)
    res: dict = {
        "lenguajes": lenguajes,
        "sintaxis": {"estado": "no_aplica", "archivos_revisados": 0, "errores": []},
        "analisis_estatico": {"estado": "no_aplica", "hallazgos": [], "seguridad": [], "metricas": {}},
        "pruebas": {"estado": "sin_pruebas", "total": 0, "aprobadas": 0, "fallidas": 0, "errores": 0,
                    "omitidas": 0, "detalle": [], "salida": "", "origen": {"estudiante": 0, "docente": False}},
        "sandbox": {"capas": {}, "limites": {}},
        "notas": [],
    }
    analizables = [r for r in archivos if r.lower().endswith((".py", ".ipynb", ".json"))]
    sin_verificador = sorted(l for l in lenguajes if l not in ("python", "notebook"))
    if sin_verificador:
        res["notas"].append("Sin verificador automático para: " + ", ".join(sin_verificador) +
                            ". Estos archivos se evalúan solo de forma conceptual.")
    if not archivos:
        res["notas"].append("No hay código para verificar.")
        return res

    d = sandbox.crear_directorio()
    try:
        sandbox.escribir_archivos(d, archivos)
        # 1) Sintaxis + análisis estático: no ejecuta el código entregado.
        if analizables:
            r = sandbox.ejecutar(d, "analizar", archivos=analizables, timeout_s=min(40, aj.sandbox_timeout_s))
            res["sandbox"] = {"capas": r.capas, "limites": r.limites}
            try:
                with open(os.path.join(d, ".resultado_analisis.json")) as f:
                    an = json.load(f)
            except (OSError, ValueError):
                an = None
            if an is None:
                res["notas"].append("El análisis estático no terminó" +
                                    (" (venció el tiempo)." if r.vencio_tiempo else f": {r.errores[-300:]}"))
            else:
                res["sintaxis"] = {"estado": "falla" if an["sintaxis"] else "ok",
                                   "archivos_revisados": len(analizables), "errores": an["sintaxis"]}
                graves = [h for h in an["hallazgos"] if h.get("tipo") == "error"]
                res["analisis_estatico"] = {
                    "estado": "falla" if graves else ("advertencias" if an["hallazgos"] or an["seguridad"] else "ok"),
                    "hallazgos": an["hallazgos"], "seguridad": an["seguridad"], "metricas": an["metricas"]}
                if not an.get("pyflakes_disponible", True):
                    res["notas"].append("pyflakes no está instalado: el análisis estático se limitó a métricas.")

        # 2) Pruebas unitarias: sí ejecuta código → solo si el sandbox está habilitado.
        pruebas_est = [r for r in archivos if RE_PRUEBA.search(r)]
        hay_docente = bool(pruebas_docente.strip())
        res["pruebas"]["origen"] = {"estudiante": len(pruebas_est), "docente": hay_docente}
        if not (pruebas_est or hay_docente):
            res["pruebas"]["estado"] = "sin_pruebas"
        elif not aj.sandbox_habilitado:
            res["pruebas"]["estado"] = "deshabilitado"
            res["notas"].append("La ejecución de pruebas está deshabilitada por configuración (SANDBOX_HABILITADO=false).")
        else:
            if hay_docente:
                with open(os.path.join(d, "test_docente_asesor.py"), "w", encoding="utf-8") as f:
                    f.write(pruebas_docente)
                if os.geteuid() == 0:
                    os.chown(os.path.join(d, "test_docente_asesor.py"), 65534, 65534)
            r = sandbox.ejecutar(d, "pytest", args=["-q", "-p", "no:cacheprovider", "--maxfail=50", "--tb=short",
                                                   "--junitxml=.resultado_pruebas.xml"])
            res["sandbox"] = {"capas": r.capas, "limites": r.limites}
            junit = _leer_junit(os.path.join(d, ".resultado_pruebas.xml"))
            p = res["pruebas"]
            p["salida"] = (r.salida[-6000:] + ("\n" + r.errores[-1500:] if r.errores.strip() else "")).strip()
            p["duracion_s"] = r.duracion_s
            if r.vencio_tiempo:
                p["estado"] = "error"
                res["notas"].append(f"Las pruebas superaron el tiempo máximo ({r.limites.get('tiempo_pared_s')} s) y se detuvieron.")
            elif junit is None or junit["total"] == 0:
                p["estado"] = "sin_pruebas" if r.codigo_salida == 5 else "error"
                if r.codigo_salida is not None and r.codigo_salida < 0:
                    res["notas"].append("El proceso de pruebas fue detenido por el sandbox al superar un límite de recursos "
                                        f"(CPU {r.limites.get('cpu_s')} s o memoria {r.limites.get('memoria_mb')} MB).")
            else:
                p.update(junit)
                p["estado"] = "ok" if junit["fallidas"] == 0 and junit["errores"] == 0 else "falla"
            faltantes = sorted(set(RE_MODULO_FALTANTE.findall(p["salida"])) - {a.rsplit("/", 1)[-1][:-3] for a in archivos if a.endswith(".py")})
            if faltantes and p["estado"] in ("error", "falla") and p.get("aprobadas", 0) == 0:
                p["estado"] = "no_ejecutable"
                p["dependencias_faltantes"] = faltantes
                res["notas"].append("Las pruebas no pudieron ejecutarse porque el sandbox no tiene instalado: " +
                                    ", ".join(faltantes) + ". No se penaliza; requiere revisión docente.")
    finally:
        sandbox.limpiar(d)
    return res


def falla_regla(verificacion: dict, tipo: str) -> bool | None:
    """True = la verificación falló; False = pasó; None = no aplica / no concluyente."""
    if tipo == "sintaxis":
        e = verificacion.get("sintaxis", {}).get("estado")
        return None if e in (None, "no_aplica") else e == "falla"
    if tipo == "analisis_estatico":
        e = verificacion.get("analisis_estatico", {}).get("estado")
        return None if e in (None, "no_aplica") else e == "falla"
    if tipo == "pruebas":
        e = verificacion.get("pruebas", {}).get("estado")
        if e in ("ok",):
            return False
        if e in ("falla", "error", "sin_pruebas"):
            return True
        return None
    return None


def resumen_texto(v: dict) -> str:
    """Texto compacto que se entrega al modelo como fuente citable."""
    ln = []
    s, a, p = v.get("sintaxis", {}), v.get("analisis_estatico", {}), v.get("pruebas", {})
    ln.append(f"Lenguajes detectados: {v.get('lenguajes') or 'ninguno'}")
    ln.append(f"Sintaxis: {s.get('estado')} ({s.get('archivos_revisados', 0)} archivos revisados)")
    for e in s.get("errores", [])[:10]:
        ln.append(f"  - {e['archivo']}:{e.get('linea', 0)} {e['mensaje']}")
    m = a.get("metricas", {})
    ln.append(f"Análisis estático: {a.get('estado')}. Métricas: {m}")
    for h in a.get("hallazgos", [])[:15]:
        ln.append(f"  - [{h.get('tipo')}] {h['archivo']}:{h.get('linea', 0)} {h['mensaje']}")
    for h in a.get("seguridad", [])[:8]:
        ln.append(f"  - [riesgo] {h['archivo']}:{h.get('linea', 0)} {h['mensaje']}")
    ln.append(f"Pruebas unitarias: {p.get('estado')} — total {p.get('total', 0)}, aprobadas {p.get('aprobadas', 0)}, "
              f"fallidas {p.get('fallidas', 0)}, errores {p.get('errores', 0)} "
              f"(archivos de prueba del estudiante: {p.get('origen', {}).get('estudiante', 0)}, "
              f"pruebas del docente: {'sí' if p.get('origen', {}).get('docente') else 'no'})")
    for d in [x for x in p.get("detalle", []) if x["resultado"] != "aprobada"][:10]:
        ln.append(f"  - {d['nombre']}: {d['resultado']} {d['mensaje'][:160]}")
    for n in v.get("notas", []):
        ln.append("Nota: " + n)
    return "\n".join(ln)
