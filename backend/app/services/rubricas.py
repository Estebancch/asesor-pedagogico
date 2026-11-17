"""Rúbricas: modelo, detección de inconsistencias e interpretación de archivos.

La rúbrica se guarda como JSON validado con Pydantic. El modelo es tolerante a
propósito (acepta ponderaciones que no suman 100, descriptores vacíos, etc.)
para poder *mostrar* las inconsistencias y dejar que el docente las corrija
antes de fijar la versión; `validar()` es quien decide si se puede evaluar.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field

ESCALA_MIN, ESCALA_MAX = 0.0, 5.0


class Nivel(BaseModel):
    id: str = ""
    nombre: str = ""
    puntaje: float = 0.0
    descripcion: str = ""


class Competencia(BaseModel):
    id: str = ""
    nombre: str = ""
    descripcion: str = ""


class ReglaObjetiva(BaseModel):
    """Regla definida en la rúbrica: si la verificación técnica falla, el
    criterio no puede superar `nivel_tope`. La aplica el backend, no el LLM."""
    verificacion: Literal["sintaxis", "analisis_estatico", "pruebas"]
    nivel_tope: str


class Criterio(BaseModel):
    id: str = ""
    nombre: str = ""
    descripcion: str = ""
    competencia_id: str = ""
    ponderacion: float = 0.0  # porcentaje
    descriptores: dict[str, str] = Field(default_factory=dict)  # nivel_id -> texto
    regla: ReglaObjetiva | None = None


class Rubrica(BaseModel):
    titulo: str = ""
    niveles: list[Nivel] = Field(default_factory=list)
    competencias: list[Competencia] = Field(default_factory=list)
    criterios: list[Criterio] = Field(default_factory=list)
    notas_interpretacion: list[str] = Field(default_factory=list)


class Inconsistencia(BaseModel):
    codigo: str
    severidad: Literal["error", "advertencia"]
    mensaje: str
    ruta: str = ""
    sugerencia: str = ""


# --- utilidades -------------------------------------------------------------

def slug(texto: str, prefijo: str = "x") -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:40]
    return t or prefijo


def _norm(texto: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()).strip()


def completar_ids(r: Rubrica) -> Rubrica:
    """Asigna ids estables a lo que no los tenga y los hace únicos."""
    def unicos(items, prefijo):
        vistos: set[str] = set()
        for i, it in enumerate(items, 1):
            base = it.id.strip() or slug(it.nombre, f"{prefijo}{i}")
            cand, n = base, 2
            while cand in vistos:
                cand, n = f"{base}_{n}", n + 1
            it.id = cand
            vistos.add(cand)
    unicos(r.niveles, "nivel")
    unicos(r.competencias, "comp")
    unicos(r.criterios, "crit")
    return r


def hash_rubrica(r: Rubrica) -> str:
    canon = json.dumps(r.model_dump(exclude={"notas_interpretacion"}), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest()


# --- validación -------------------------------------------------------------

def validar(r: Rubrica) -> list[Inconsistencia]:
    inc: list[Inconsistencia] = []

    def add(codigo, severidad, mensaje, ruta="", sugerencia=""):
        inc.append(Inconsistencia(codigo=codigo, severidad=severidad, mensaje=mensaje, ruta=ruta, sugerencia=sugerencia))

    # Niveles
    if len(r.niveles) < 2:
        add("NIVELES_INSUFICIENTES", "error", "La rúbrica necesita al menos dos niveles de valoración.",
            "niveles", "Agrega niveles como Excelente, Bueno, Aceptable e Insuficiente con su puntaje.")
    ids_nivel = [n.id for n in r.niveles]
    for i, n in enumerate(r.niveles):
        ruta = f"niveles[{i}]"
        if not n.nombre.strip():
            add("NIVEL_SIN_NOMBRE", "error", f"El nivel {i + 1} no tiene nombre.", ruta)
        if not (ESCALA_MIN <= n.puntaje <= ESCALA_MAX):
            add("PUNTAJE_FUERA_DE_ESCALA", "error",
                f"El nivel «{n.nombre or i + 1}» tiene puntaje {n.puntaje:g}; debe estar entre 0,0 y 5,0.", ruta,
                "Si la rúbrica usa otra escala (por ejemplo 0–100), conviértela a 0–5.")
    if len(set(ids_nivel)) != len(ids_nivel):
        add("NIVEL_DUPLICADO", "error", "Hay niveles con el mismo identificador.", "niveles")
    puntajes = [n.puntaje for n in r.niveles]
    if len(set(puntajes)) != len(puntajes) and len(r.niveles) >= 2:
        add("PUNTAJES_REPETIDOS", "advertencia", "Dos o más niveles comparten el mismo puntaje.", "niveles",
            "Cada nivel debería tener un puntaje distinto para diferenciar el desempeño.")
    if r.niveles and max(puntajes) < ESCALA_MAX:
        add("SIN_NIVEL_MAXIMO", "advertencia",
            f"Ningún nivel otorga 5,0: la nota máxima alcanzable sería {max(puntajes):g}.", "niveles")
    nombres_nivel = [_norm(n.nombre) for n in r.niveles if n.nombre.strip()]
    if len(set(nombres_nivel)) != len(nombres_nivel):
        add("NIVEL_NOMBRE_REPETIDO", "advertencia", "Hay niveles con el mismo nombre.", "niveles")

    # Competencias
    ids_comp = [c.id for c in r.competencias]
    if not r.competencias:
        add("SIN_COMPETENCIAS", "error", "La rúbrica no identifica competencias.", "competencias",
            "Define al menos una competencia y asóciala a los criterios.")
    for i, c in enumerate(r.competencias):
        if not c.nombre.strip():
            add("COMPETENCIA_SIN_NOMBRE", "error", f"La competencia {i + 1} no tiene nombre.", f"competencias[{i}]")
    if len(set(ids_comp)) != len(ids_comp):
        add("COMPETENCIA_DUPLICADA", "error", "Hay competencias con el mismo identificador.", "competencias")

    # Criterios
    if not r.criterios:
        add("SIN_CRITERIOS", "error", "La rúbrica no tiene criterios de evaluación.", "criterios")
    ids_crit = [c.id for c in r.criterios]
    if len(set(ids_crit)) != len(ids_crit):
        add("CRITERIO_DUPLICADO", "error", "Hay criterios con el mismo identificador.", "criterios")
    nombres_crit = [_norm(c.nombre) for c in r.criterios if c.nombre.strip()]
    if len(set(nombres_crit)) != len(nombres_crit):
        add("CRITERIO_NOMBRE_REPETIDO", "advertencia", "Hay criterios con el mismo nombre; podrían estar duplicados.", "criterios")
    usadas: set[str] = set()
    for i, c in enumerate(r.criterios):
        ruta = f"criterios[{i}]"
        etiqueta = c.nombre or f"criterio {i + 1}"
        if not c.nombre.strip():
            add("CRITERIO_SIN_NOMBRE", "error", f"El criterio {i + 1} no tiene nombre.", ruta)
        if c.ponderacion <= 0:
            add("PONDERACION_INVALIDA", "error", f"«{etiqueta}» tiene ponderación {c.ponderacion:g} %; debe ser mayor que 0.", ruta)
        if not c.competencia_id:
            add("CRITERIO_SIN_COMPETENCIA", "error", f"«{etiqueta}» no está asociado a una competencia.", ruta)
        elif c.competencia_id not in ids_comp:
            add("COMPETENCIA_INEXISTENTE", "error", f"«{etiqueta}» apunta a una competencia que no existe.", ruta)
        else:
            usadas.add(c.competencia_id)
        faltan = [n.nombre or n.id for n in r.niveles if not (c.descriptores.get(n.id) or "").strip()]
        if faltan and r.niveles:
            add("DESCRIPTOR_FALTANTE", "advertencia",
                f"«{etiqueta}» no describe el desempeño para: {', '.join(faltan)}.", ruta,
                "Sin descriptor, la IA tiene menos base para distinguir ese nivel.")
        sobran = [k for k in c.descriptores if k not in ids_nivel]
        if sobran:
            add("DESCRIPTOR_HUERFANO", "advertencia", f"«{etiqueta}» tiene descriptores de niveles que ya no existen.", ruta)
        textos = [_norm(t) for t in c.descriptores.values() if t.strip()]
        if len(textos) >= 2 and len(set(textos)) < len(textos):
            add("DESCRIPTORES_IDENTICOS", "advertencia", f"«{etiqueta}» repite el mismo descriptor en varios niveles.", ruta)
        if c.regla and c.regla.nivel_tope not in ids_nivel:
            add("REGLA_NIVEL_INEXISTENTE", "error", f"La regla objetiva de «{etiqueta}» usa un nivel que no existe.", ruta)
    for i, c in enumerate(r.competencias):
        if c.id not in usadas and r.criterios:
            add("COMPETENCIA_SIN_CRITERIOS", "advertencia", f"La competencia «{c.nombre}» no tiene criterios que la evalúen.", f"competencias[{i}]")

    total = round(sum(c.ponderacion for c in r.criterios), 4)
    if r.criterios and abs(total - 100) > 0.01:
        add("PONDERACIONES_NO_SUMAN_100", "error",
            f"Las ponderaciones suman {total:g} %, no 100 %.", "criterios",
            "Ajusta los porcentajes o usa «Normalizar a 100 %» para repartirlos proporcionalmente.")
    return inc


def tiene_errores(inc: list[Inconsistencia]) -> bool:
    return any(i.severidad == "error" for i in inc)


def normalizar_ponderaciones(r: Rubrica) -> Rubrica:
    """Reparte proporcionalmente para que sumen exactamente 100 (2 decimales)."""
    total = sum(max(c.ponderacion, 0) for c in r.criterios)
    if not r.criterios:
        return r
    if total <= 0:
        for c in r.criterios:
            c.ponderacion = 1
        total = len(r.criterios)
    acum = 0.0
    for c in r.criterios[:-1]:
        c.ponderacion = round(max(c.ponderacion, 0) * 100 / total, 2)
        acum += c.ponderacion
    r.criterios[-1].ponderacion = round(100 - acum, 2)
    return r


# --- interpretación de archivos ------------------------------------------------

class TextoRubrica(BaseModel):
    texto: str = ""
    tablas: list[list[list[str]]] = Field(default_factory=list)
    json_directo: dict | None = None


def extraer_contenido(nombre: str, datos: bytes) -> TextoRubrica:
    ext = nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""
    out = TextoRubrica()
    if ext == "json":
        out.json_directo = json.loads(datos.decode("utf-8-sig"))
        out.texto = json.dumps(out.json_directo, ensure_ascii=False, indent=1)
    elif ext == "pdf":
        import pdfplumber
        partes = []
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            for pag in pdf.pages[:30]:
                partes.append(pag.extract_text() or "")
                for t in pag.extract_tables() or []:
                    out.tablas.append([[(c or "").strip() for c in fila] for fila in t])
        out.texto = "\n".join(partes)
    elif ext == "docx":
        import docx
        d = docx.Document(io.BytesIO(datos))
        out.texto = "\n".join(p.text for p in d.paragraphs)
        for t in d.tables:
            filas = [[c.text.strip() for c in f.cells] for f in t.rows]
            out.tablas.append(filas)
            out.texto += "\n" + "\n".join(" | ".join(f) for f in filas)
    elif ext in ("xlsx", "xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(datos), data_only=True, read_only=True)
        for ws in wb.worksheets[:5]:
            filas = [["" if c is None else str(c).strip() for c in fila] for fila in ws.iter_rows(values_only=True)]
            filas = [f for f in filas if any(f)]
            if filas:
                out.tablas.append(filas)
                out.texto += "\n".join(" | ".join(f) for f in filas) + "\n"
    elif ext in ("csv", "tsv"):
        txt = datos.decode("utf-8-sig", errors="replace")
        try:
            dialecto = csv.Sniffer().sniff(txt[:4000], delimiters=",;\t|")
        except csv.Error:
            dialecto = csv.excel
        filas = [[c.strip() for c in f] for f in csv.reader(io.StringIO(txt), dialecto) if any(c.strip() for c in f)]
        out.tablas.append(filas)
        out.texto = txt
    else:  # md, txt
        out.texto = datos.decode("utf-8-sig", errors="replace")
        tabla = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in out.texto.splitlines()
                 if ln.count("|") >= 2 and not re.fullmatch(r"[\s|:\-]+", ln)]
        if tabla:
            out.tablas.append(tabla)
    return out


_RE_NUM = re.compile(r"(\d+(?:[.,]\d+)?)")
_ALTOS = ("excelente", "superior", "sobresaliente", "avanzado", "destacado", "alto", "optimo")
_BAJOS = ("insuficiente", "deficiente", "bajo", "inicial", "no cumple", "ausente", "nulo")


def _num(txt: str) -> float | None:
    m = _RE_NUM.search(txt or "")
    return float(m.group(1).replace(",", ".")) if m else None


def desde_tabla(filas: list[list[str]], titulo: str = "") -> Rubrica | None:
    """Heurística para tablas con una fila por criterio y una columna por nivel.
    Se usa sin modelo de IA (CSV/XLSX bien formados) y como respaldo."""
    # Las celdas de un PDF traen saltos de línea donde el texto se partió: se dejan en una sola línea.
    filas = [[" ".join(str(c or "").split()) for c in f] for f in filas]
    cab_i = next((i for i, f in enumerate(filas) if any("criteri" in _norm(c) for c in f)), None)
    if cab_i is None:
        return None
    cab = [_norm(c) for c in filas[cab_i]]
    crudas = filas[cab_i]
    col = {"criterio": None, "peso": None, "competencia": None, "descripcion": None}
    niveles_cols: list[int] = []
    for i, c in enumerate(cab):
        if not c:
            continue
        if col["criterio"] is None and "criteri" in c:
            col["criterio"] = i
        elif col["peso"] is None and re.search(r"pondera|peso|porcentaje|%|valor", c):
            col["peso"] = i
        elif col["competencia"] is None and "competenc" in c:
            col["competencia"] = i
        elif col["descripcion"] is None and re.fullmatch(r"descripcion.*|que se evalua.*", c):
            col["descripcion"] = i
        else:
            niveles_cols.append(i)
    if col["criterio"] is None or len(niveles_cols) < 2:
        return None

    r = Rubrica(titulo=titulo)
    for i in niveles_cols:
        nombre = crudas[i].strip()
        nums = [float(x.replace(",", ".")) for x in _RE_NUM.findall(nombre)]
        puntaje = max(nums) if nums else None
        limpio = re.sub(r"[\(\[]?\s*\d+(?:[.,]\d+)?(\s*[-–a]\s*\d+(?:[.,]\d+)?)?\s*[\)\]]?", "", nombre).strip(" :-–") or nombre
        r.niveles.append(Nivel(nombre=limpio, puntaje=puntaje if puntaje is not None else -1))
    if any(n.puntaje < 0 for n in r.niveles):
        n = len(r.niveles)
        desc = any(a in _norm(r.niveles[0].nombre) for a in _ALTOS) or any(b in _norm(r.niveles[-1].nombre) for b in _BAJOS)
        asc = any(b in _norm(r.niveles[0].nombre) for b in _BAJOS) or any(a in _norm(r.niveles[-1].nombre) for a in _ALTOS)
        orden = list(range(n)) if (desc or not asc) else list(reversed(range(n)))
        for pos, idx in enumerate(orden):
            r.niveles[idx].puntaje = round(5.0 - pos * (4.0 / (n - 1)), 2) if n > 1 else 5.0
        r.notas_interpretacion.append(
            "La rúbrica no indica el puntaje de cada nivel: se asignaron valores equidistantes entre 5,0 y 1,0. Revísalos.")
    elif max(n.puntaje for n in r.niveles) > 5:
        tope = max(n.puntaje for n in r.niveles)
        for n in r.niveles:
            n.puntaje = round(n.puntaje * 5 / tope, 2)
        r.notas_interpretacion.append(f"Los puntajes venían en escala 0–{tope:g} y se convirtieron a 0–5.")
    completar_ids(r)

    comp_por_nombre: dict[str, Competencia] = {}
    comp_actual = ""
    refs: list[Competencia] = []
    for fila in filas[cab_i + 1:]:
        fila = fila + [""] * (len(cab) - len(fila))
        nombre = fila[col["criterio"]].strip()
        if not nombre or "total" == _norm(nombre):
            continue
        if col["competencia"] is not None and fila[col["competencia"]].strip():
            comp_actual = fila[col["competencia"]].strip()
        comp_nombre = comp_actual or "Competencia general"
        comp = comp_por_nombre.setdefault(_norm(comp_nombre), Competencia(nombre=comp_nombre))
        peso = _num(fila[col["peso"]]) if col["peso"] is not None else None
        crit = Criterio(nombre=nombre, ponderacion=peso or 0.0,
                        descripcion=fila[col["descripcion"]].strip() if col["descripcion"] is not None else "")
        refs.append(comp)
        for nivel, i in zip(r.niveles, niveles_cols):
            if fila[i].strip():
                crit.descriptores[nivel.id] = fila[i].strip()
        r.criterios.append(crit)
    if not r.criterios:
        return None
    r.competencias = list(comp_por_nombre.values())
    completar_ids(r)
    for c, comp in zip(r.criterios, refs):
        c.competencia_id = comp.id
    pesos = [c.ponderacion for c in r.criterios]
    if pesos and all(0 < p <= 1 for p in pesos) and abs(sum(pesos) - 1) < 0.051:
        for c in r.criterios:
            c.ponderacion = round(c.ponderacion * 100, 2)
        r.notas_interpretacion.append("Las ponderaciones venían como fracción (0–1) y se expresaron en porcentaje.")
    if col["peso"] is None:
        r.notas_interpretacion.append("No se encontró una columna de ponderación: asigna el peso de cada criterio.")
    if col["competencia"] is None:
        r.notas_interpretacion.append("No se encontró una columna de competencias: todos los criterios quedaron en «Competencia general».")
    return r


# Esquema que se le pide al modelo de IA al interpretar una rúbrica en texto libre.
class _DescriptorIA(BaseModel):
    nivel: str = Field(description="Nombre exacto del nivel de valoración")
    texto: str = Field(description="Descriptor de desempeño tal como aparece en la rúbrica")


class _CriterioIA(BaseModel):
    nombre: str
    descripcion: str = ""
    competencia: str = Field(description="Nombre de la competencia a la que pertenece")
    ponderacion: float = Field(description="Porcentaje tal como aparece en la rúbrica; 0 si no aparece")
    descriptores: list[_DescriptorIA] = Field(default_factory=list)


class _NivelIA(BaseModel):
    nombre: str
    puntaje: float = Field(description="Puntaje del nivel en escala 0 a 5; -1 si la rúbrica no lo indica")


class _CompetenciaIA(BaseModel):
    nombre: str
    descripcion: str = ""


class RubricaInterpretadaIA(BaseModel):
    titulo: str = ""
    niveles: list[_NivelIA]
    competencias: list[_CompetenciaIA]
    criterios: list[_CriterioIA]
    observaciones: list[str] = Field(default_factory=list, description="Ambigüedades o datos faltantes detectados")


SISTEMA_RUBRICA = (
    "Eres un asistente que transcribe rúbricas de evaluación a un formato estructurado. "
    "Transcribe fielmente: NO corrijas ponderaciones aunque no sumen 100, NO inventes descriptores, "
    "NO completes niveles que no existan. Si un dato no aparece, déjalo vacío (o -1 / 0 donde se indica) "
    "y anótalo en 'observaciones'. Si los niveles traen un rango (p. ej. 4.0–4.5) usa el valor superior. "
    "Si la escala no es 0–5, convierte proporcionalmente a 0–5 y anótalo. Responde solo con el JSON."
)


def desde_ia(datos: RubricaInterpretadaIA) -> Rubrica:
    r = Rubrica(titulo=datos.titulo, notas_interpretacion=list(datos.observaciones))
    r.niveles = [Nivel(nombre=n.nombre, puntaje=n.puntaje) for n in datos.niveles]
    if any(n.puntaje < 0 for n in r.niveles):
        n = len(r.niveles)
        ordenados = sorted(range(n), key=lambda i: (0 if any(a in _norm(r.niveles[i].nombre) for a in _ALTOS) else
                                                    2 if any(b in _norm(r.niveles[i].nombre) for b in _BAJOS) else 1, i))
        for pos, idx in enumerate(ordenados):
            r.niveles[idx].puntaje = round(5.0 - pos * (4.0 / (n - 1)), 2) if n > 1 else 5.0
        r.notas_interpretacion.append("Puntajes de nivel inferidos (equidistantes entre 5,0 y 1,0). Revísalos.")
    r.competencias = [Competencia(nombre=c.nombre, descripcion=c.descripcion) for c in datos.competencias]
    completar_ids(r)
    por_nombre = {_norm(c.nombre): c for c in r.competencias}
    nivel_por_nombre = {_norm(n.nombre): n for n in r.niveles}
    for c in datos.criterios:
        comp = por_nombre.get(_norm(c.competencia))
        if comp is None and c.competencia.strip():
            comp = Competencia(nombre=c.competencia.strip())
            r.competencias.append(comp)
            completar_ids(r)
            por_nombre[_norm(comp.nombre)] = comp
        crit = Criterio(nombre=c.nombre, descripcion=c.descripcion, ponderacion=c.ponderacion,
                        competencia_id=comp.id if comp else "")
        for d in c.descriptores:
            n = nivel_por_nombre.get(_norm(d.nivel))
            if n and d.texto.strip():
                crit.descriptores[n.id] = d.texto.strip()
        r.criterios.append(crit)
    return completar_ids(r)


def plantilla_base() -> Rubrica:
    r = Rubrica(
        titulo="Nueva rúbrica",
        niveles=[Nivel(nombre="Excelente", puntaje=5.0), Nivel(nombre="Bueno", puntaje=4.0),
                 Nivel(nombre="Aceptable", puntaje=3.0), Nivel(nombre="Insuficiente", puntaje=1.5)],
        competencias=[Competencia(nombre="Competencia 1")],
    )
    completar_ids(r)
    r.criterios = [Criterio(nombre="Criterio 1", competencia_id=r.competencias[0].id, ponderacion=100)]
    return completar_ids(r)
