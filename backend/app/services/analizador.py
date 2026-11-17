"""Análisis de código SIN ejecutarlo: sintaxis (ast), análisis estático
(pyflakes), métricas simples y patrones de riesgo. Corre dentro del sandbox
para que un archivo malicioso (p. ej. anidamiento extremo) no afecte al servidor."""
import ast
import json
import os
import re

PATRONES_RIESGO = [
    (re.compile(r"""(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*["'][A-Za-z0-9_\-\.]{16,}["']"""),
     "Posible credencial escrita en el código"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "Posible clave de API de Google expuesta"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "Posible clave de API expuesta (formato sk-…)"),
    (re.compile(r"\beval\s*\("), "Uso de eval()"),
    (re.compile(r"\bexec\s*\("), "Uso de exec()"),
    (re.compile(r"shell\s*=\s*True"), "subprocess con shell=True"),
    (re.compile(r"\bpickle\.loads?\s*\("), "Deserialización con pickle"),
]


def _complejidad(nodo):
    c = 1
    for n in ast.walk(nodo):
        if isinstance(n, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler, ast.IfExp,
                          ast.comprehension, ast.Assert, ast.match_case)):
            c += 1
        elif isinstance(n, ast.BoolOp):
            c += len(n.values) - 1
    return c


def _codigo_de_notebook(texto):
    nb = json.loads(texto)
    partes = []
    for celda in nb.get("cells", []):
        if celda.get("cell_type") != "code":
            continue
        src = celda.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        lineas = [("# " + ln) if ln.lstrip().startswith(("%", "!", "?")) else ln for ln in src.splitlines()]
        partes.append("\n".join(lineas))
    return "\n\n".join(partes)


def _pyflakes(codigo, ruta):
    try:
        from pyflakes import api, reporter
    except Exception:
        return None

    class Rep(reporter.Reporter):
        def __init__(self):
            self.items = []

        def unexpectedError(self, filename, msg):
            self.items.append({"archivo": filename, "linea": 0, "mensaje": str(msg), "tipo": "error"})

        def syntaxError(self, filename, msg, lineno, offset, text):
            pass  # ya lo reporta la verificación de sintaxis

        def flake(self, m):
            nombre = type(m).__name__
            grave = nombre in ("UndefinedName", "UndefinedExport", "UndefinedLocal", "ReturnOutsideFunction",
                               "DuplicateArgument", "YieldOutsideFunction", "ContinueOutsideLoop", "BreakOutsideLoop")
            self.items.append({"archivo": m.filename, "linea": m.lineno, "regla": nombre,
                               "mensaje": m.message % m.message_args, "tipo": "error" if grave else "advertencia"})

    rep = Rep()
    api.check(codigo, ruta, rep)
    return rep.items


def analizar(trabajo, archivos):
    sintaxis, hallazgos, seguridad = [], [], []
    met = {"archivos_python": 0, "notebooks": 0, "lineas_codigo": 0, "funciones": 0, "clases": 0,
           "con_docstring": 0, "complejidad_max": 0, "funcion_mas_compleja": "", "otros_validados": 0}
    pyflakes_ok = True
    for rel in archivos:
        ruta = os.path.join(trabajo, rel)
        try:
            with open(ruta, encoding="utf-8", errors="replace") as f:
                texto = f.read()
        except OSError as e:
            sintaxis.append({"archivo": rel, "linea": 0, "mensaje": "No se pudo leer: %s" % e})
            continue
        ext = rel.lower().rsplit(".", 1)[-1] if "." in rel else ""
        for i, ln in enumerate(texto.splitlines(), 1):
            if len(ln) > 2000:
                continue
            for patron, desc in PATRONES_RIESGO:
                if patron.search(ln):
                    seguridad.append({"archivo": rel, "linea": i, "mensaje": desc})
        if ext == "json":
            try:
                json.loads(texto)
                met["otros_validados"] += 1
            except ValueError as e:
                sintaxis.append({"archivo": rel, "linea": getattr(e, "lineno", 0), "mensaje": "JSON inválido: %s" % e})
            continue
        if ext == "ipynb":
            try:
                codigo = _codigo_de_notebook(texto)
                met["notebooks"] += 1
            except (ValueError, AttributeError) as e:
                sintaxis.append({"archivo": rel, "linea": 0, "mensaje": "Notebook ilegible: %s" % e})
                continue
        elif ext == "py":
            codigo = texto
            met["archivos_python"] += 1
        else:
            continue
        met["lineas_codigo"] += sum(1 for ln in codigo.splitlines() if ln.strip() and not ln.strip().startswith("#"))
        try:
            arbol = ast.parse(codigo, filename=rel)
        except SyntaxError as e:
            sintaxis.append({"archivo": rel, "linea": e.lineno or 0, "mensaje": "%s" % (e.msg,),
                             "texto": (e.text or "").strip()[:160]})
            continue
        except (RecursionError, MemoryError, ValueError) as e:
            sintaxis.append({"archivo": rel, "linea": 0, "mensaje": "No analizable: %s" % type(e).__name__})
            continue
        for n in ast.walk(arbol):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                met["funciones"] += 1
                if ast.get_docstring(n):
                    met["con_docstring"] += 1
                c = _complejidad(n)
                if c > met["complejidad_max"]:
                    met["complejidad_max"], met["funcion_mas_compleja"] = c, "%s:%s" % (rel, n.name)
            elif isinstance(n, ast.ClassDef):
                met["clases"] += 1
                if ast.get_docstring(n):
                    met["con_docstring"] += 1
        pf = _pyflakes(codigo, rel)
        if pf is None:
            pyflakes_ok = False
        else:
            hallazgos.extend(pf)
    return {"sintaxis": sintaxis, "hallazgos": hallazgos[:200], "seguridad": seguridad[:50],
            "metricas": met, "pyflakes_disponible": pyflakes_ok}
