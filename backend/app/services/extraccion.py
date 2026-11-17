"""Extracción de evidencias de una entrega: informe PDF, código (ZIP o GitHub),
presentación opcional e imágenes. Cada fragmento queda como una *fuente* con
identificador estable para que las citas del modelo sean verificables."""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass, field

import httpx

EXT_CODIGO = {
    "py": "python", "ipynb": "notebook", "js": "javascript", "jsx": "javascript", "ts": "typescript",
    "tsx": "typescript", "java": "java", "c": "c", "h": "c", "cpp": "c++", "cs": "c#", "go": "go", "rs": "rust",
    "r": "r", "sql": "sql", "html": "html", "css": "css", "sh": "shell", "kt": "kotlin", "php": "php", "rb": "ruby",
}
EXT_TEXTO = {"md": "markdown", "txt": "texto", "json": "json", "yaml": "yaml", "yml": "yaml", "toml": "toml",
             "csv": "csv", "cfg": "config", "ini": "config", "env.example": "config"}
EXT_IMAGEN = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
DIRS_IGNORADOS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "env", "dist", "build", ".idea",
                  ".vscode", ".ipynb_checkpoints", ".pytest_cache", ".mypy_cache", "site-packages", "__MACOSX",
                  ".next", "target", "bin", "obj"}
MAX_ARCHIVOS_ZIP = 2000
MAX_DESCOMPRIMIDO = 80 * 1024 * 1024
MAX_ARCHIVO_TEXTO = 400_000
MAX_CSV = 4_000
MIN_TEXTO_PDF = 200  # caracteres: por debajo se considera PDF no legible (escaneado)


@dataclass
class Fuente:
    id: str
    tipo: str  # informe | codigo | documento | presentacion | verificacion
    titulo: str
    texto: str
    meta: dict = field(default_factory=dict)


@dataclass
class Evidencias:
    fuentes: list[Fuente] = field(default_factory=list)
    archivos_codigo: dict[str, bytes] = field(default_factory=dict)  # para verificación técnica
    imagenes: list[tuple[str, str, bytes]] = field(default_factory=list)  # (nombre, mime, datos)
    pdf_informe: bytes | None = None
    arbol: list[dict] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    def textos(self) -> dict[str, str]:
        return {f.id: f.texto for f in self.fuentes}

    def hash(self) -> str:
        h = hashlib.sha256()
        for f in sorted(self.fuentes, key=lambda x: x.id):
            h.update(f.id.encode())
            h.update(hashlib.sha256(f.texto.encode()).digest())
        for nombre, _, datos in sorted(self.imagenes):
            h.update(nombre.encode())
            h.update(hashlib.sha256(datos).digest())
        return h.hexdigest()


def texto_pdf(datos: bytes) -> list[str]:
    from pypdf import PdfReader
    lector = PdfReader(io.BytesIO(datos))
    if lector.is_encrypted:
        try:
            lector.decrypt("")
        except Exception:
            return []
    paginas = []
    for p in lector.pages[:200]:
        try:
            paginas.append((p.extract_text() or "").replace("\x00", ""))
        except Exception:
            paginas.append("")
    return paginas


def texto_pptx(datos: bytes) -> list[str]:
    from pptx import Presentation
    pres = Presentation(io.BytesIO(datos))
    diapositivas = []
    for d in pres.slides:
        partes = [f.text_frame.text for f in d.shapes if f.has_text_frame and f.text_frame.text.strip()]
        if d.has_notes_slide and d.notes_slide.notes_text_frame is not None:
            notas = d.notes_slide.notes_text_frame.text.strip()
            if notas:
                partes.append("Notas: " + notas)
        diapositivas.append("\n".join(partes))
    return diapositivas


def _ruta_segura(nombre: str) -> str | None:
    nombre = nombre.replace("\\", "/")
    if nombre.startswith("/") or re.match(r"^[A-Za-z]:", nombre):
        return None
    partes = [p for p in nombre.split("/") if p not in ("", ".")]
    if not partes or any(p == ".." for p in partes):
        return None
    if any(p in DIRS_IGNORADOS for p in partes[:-1]):
        return None
    return "/".join(partes)


def leer_zip(datos: bytes) -> tuple[dict[str, bytes], list[str]]:
    """Devuelve {ruta: contenido} de archivos útiles. Protege contra path
    traversal, bombas de descompresión y enlaces simbólicos."""
    avisos: list[str] = []
    archivos: dict[str, bytes] = {}
    try:
        zf = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        return {}, ["El archivo de código no es un ZIP válido."]
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_ARCHIVOS_ZIP:
        avisos.append(f"El ZIP tiene {len(infos)} archivos; solo se revisan los primeros {MAX_ARCHIVOS_ZIP}.")
        infos = infos[:MAX_ARCHIVOS_ZIP]
    total = 0
    for info in infos:
        if (info.external_attr >> 16) & 0o170000 == 0o120000:  # symlink
            continue
        ruta = _ruta_segura(info.filename)
        if not ruta:
            continue
        ext = ruta.lower().rsplit(".", 1)[-1] if "." in ruta.rsplit("/", 1)[-1] else ""
        es_imagen = ext in EXT_IMAGEN
        if ext not in EXT_CODIGO and ext not in EXT_TEXTO and not es_imagen and ext not in ("pdf",):
            continue
        limite = 1_500_000 if es_imagen else (5_000_000 if ext in ("ipynb", "pdf") else MAX_ARCHIVO_TEXTO)
        if info.file_size > limite:
            avisos.append(f"Se omitió «{ruta}» por tamaño ({info.file_size // 1024} KB).")
            continue
        total += info.file_size
        if total > MAX_DESCOMPRIMIDO:
            avisos.append("El contenido descomprimido supera el límite; el resto de archivos no se revisó.")
            break
        with zf.open(info) as f:
            archivos[ruta] = f.read(limite + 1)[:limite]
    # Quitar la carpeta raíz común (típica de los ZIP de GitHub)
    if archivos:
        primeros = {r.split("/", 1)[0] for r in archivos}
        if len(primeros) == 1 and all("/" in r for r in archivos):
            archivos = {r.split("/", 1)[1]: c for r, c in archivos.items()}
    return archivos, avisos


RE_GITHUB = re.compile(r"^https://github\.com/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+?)(?:\.git)?(?:/tree/([^/?#]+))?/?$")


def descargar_github(url: str, max_bytes: int = 40 * 1024 * 1024, cliente: httpx.Client | None = None) -> tuple[bytes, dict]:
    """Descarga una instantánea del repositorio público. Solo se aceptan URL de
    github.com (evita SSRF) y se fija el commit para dejar trazabilidad."""
    m = RE_GITHUB.match(url.strip())
    if not m:
        raise ValueError("La URL debe tener la forma https://github.com/usuario/repositorio")
    owner, repo, rama = m.group(1), m.group(2), m.group(3)
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "asesor-pedagogico"})
    try:
        commit = ""
        try:
            r = cliente.get(f"https://api.github.com/repos/{owner}/{repo}/commits/{rama or 'HEAD'}",
                            headers={"Accept": "application/vnd.github.sha"})
            if r.status_code == 200 and re.fullmatch(r"[0-9a-f]{40}", r.text.strip()):
                commit = r.text.strip()
        except httpx.HTTPError:
            pass
        ref = commit or rama or "HEAD"
        with cliente.stream("GET", f"https://codeload.github.com/{owner}/{repo}/zip/{ref}") as resp:
            if resp.status_code == 404:
                raise ValueError("No se encontró el repositorio. Verifica que sea público y que la URL esté bien escrita.")
            resp.raise_for_status()
            trozos, total = [], 0
            for t in resp.iter_bytes():
                total += len(t)
                if total > max_bytes:
                    raise ValueError("El repositorio supera el tamaño máximo permitido (40 MB).")
                trozos.append(t)
        return b"".join(trozos), {"owner": owner, "repo": repo, "commit": commit, "rama": rama or ""}
    finally:
        if propio:
            cliente.close()


def _notebook_a_texto(datos: bytes) -> str:
    try:
        nb = json.loads(datos.decode("utf-8", "replace"))
    except ValueError:
        return datos.decode("utf-8", "replace")[:MAX_ARCHIVO_TEXTO]
    partes = []
    for i, celda in enumerate(nb.get("cells", []), 1):
        src = celda.get("source", "")
        src = "".join(src) if isinstance(src, list) else str(src)
        if not src.strip():
            continue
        tipo = "código" if celda.get("cell_type") == "code" else "texto"
        partes.append(f"[celda {i} · {tipo}]\n{src}")
        if celda.get("cell_type") == "code":
            for o in celda.get("outputs", [])[:3]:
                txt = o.get("text") or (o.get("data", {}) or {}).get("text/plain") or ""
                txt = "".join(txt) if isinstance(txt, list) else str(txt)
                if txt.strip():
                    partes.append(f"[salida celda {i}]\n{txt[:1500]}")
    return "\n\n".join(partes)


def _prioridad(ruta: str) -> tuple:
    nombre = ruta.rsplit("/", 1)[-1].lower()
    ext = nombre.rsplit(".", 1)[-1] if "." in nombre else ""
    return (0 if nombre.startswith("readme") else 1 if ext in ("py", "ipynb") else 2 if ext in EXT_CODIGO else 3,
            ruta.count("/"), ruta)


def construir(*, informe: tuple[str, bytes] | None, zip_codigo: bytes | None,
              presentacion: tuple[str, bytes] | None = None, max_caracteres: int = 180_000) -> Evidencias:
    ev = Evidencias()
    presupuesto = max_caracteres

    if informe:
        nombre, datos = informe
        ev.pdf_informe = datos
        try:
            paginas = texto_pdf(datos)
        except Exception as e:  # PDF corrupto
            paginas = []
            ev.advertencias.append(f"No se pudo leer el informe PDF ({type(e).__name__}).")
        total = sum(len(p.strip()) for p in paginas)
        if total < MIN_TEXTO_PDF:
            ev.advertencias.append(
                "El informe PDF no contiene texto legible (parece escaneado o es una imagen). "
                "Vuelve a exportarlo como PDF de texto para que pueda citarse.")
        for i, txt in enumerate(paginas, 1):
            if txt.strip():
                txt = txt[:max(0, presupuesto)]
                presupuesto -= len(txt)
                ev.fuentes.append(Fuente(f"informe:p{i}", "informe", f"{nombre} · página {i}", txt, {"pagina": i}))
    else:
        ev.advertencias.append("La entrega no incluye informe PDF.")

    if zip_codigo:
        archivos, avisos = leer_zip(zip_codigo)
        ev.advertencias.extend(avisos)
        if not archivos and not avisos:
            ev.advertencias.append("El ZIP de código no contiene archivos reconocibles.")
        for ruta in sorted(archivos, key=_prioridad):
            datos = archivos[ruta]
            ext = ruta.lower().rsplit(".", 1)[-1] if "." in ruta.rsplit("/", 1)[-1] else ""
            item = {"ruta": ruta, "bytes": len(datos), "sha256": hashlib.sha256(datos).hexdigest()[:16],
                    "lenguaje": EXT_CODIGO.get(ext) or EXT_TEXTO.get(ext) or ("imagen" if ext in EXT_IMAGEN else ext),
                    "incluido": False, "truncado": False}
            ev.arbol.append(item)
            if ext in EXT_IMAGEN:
                if len(ev.imagenes) < 6:
                    ev.imagenes.append((ruta, EXT_IMAGEN[ext], datos))
                    item["incluido"] = True
                continue
            if ext == "pdf":
                continue
            if ext in EXT_CODIGO or ext in ("json", "toml", "cfg", "ini", "txt", "md", "yaml", "yml"):
                ev.archivos_codigo[ruta] = datos
            if b"\x00" in datos[:2000]:
                continue
            texto = _notebook_a_texto(datos) if ext == "ipynb" else datos.decode("utf-8", "replace")
            if ext == "csv":
                texto = texto[:MAX_CSV]
            if ext == "json" and len(texto) > 6000:
                texto = texto[:6000]
            if presupuesto <= 0:
                continue
            if len(texto) > presupuesto:
                texto, item["truncado"] = texto[:presupuesto], True
            presupuesto -= len(texto)
            item["incluido"] = True
            ev.fuentes.append(Fuente(f"codigo:{ruta}", "codigo", ruta, texto,
                                     {"lenguaje": item["lenguaje"], "lineas": texto.count("\n") + 1}))
        if any(not a["incluido"] and a["lenguaje"] not in ("imagen", "pdf") for a in ev.arbol):
            ev.advertencias.append("La entrega es extensa: algunos archivos no entraron en el análisis del modelo "
                                   "(sí se incluyen en la verificación técnica). Revisa el manifiesto de evidencias.")
    else:
        ev.advertencias.append("La entrega no incluye código fuente.")

    if presentacion:
        nombre, datos = presentacion
        try:
            if nombre.lower().endswith(".pptx"):
                laminas = texto_pptx(datos)
            elif nombre.lower().endswith(".pdf"):
                laminas = texto_pdf(datos)
            else:
                laminas = []
            for i, txt in enumerate(laminas, 1):
                if txt.strip() and presupuesto > 0:
                    txt = txt[:presupuesto]
                    presupuesto -= len(txt)
                    ev.fuentes.append(Fuente(f"presentacion:d{i}", "presentacion", f"{nombre} · diapositiva {i}", txt))
        except Exception as e:
            ev.advertencias.append(f"No se pudo leer la presentación ({type(e).__name__}).")
    return ev


def manifiesto(ev: Evidencias) -> dict:
    return {
        "fuentes": [{"id": f.id, "tipo": f.tipo, "titulo": f.titulo, "caracteres": len(f.texto),
                     "sha256": hashlib.sha256(f.texto.encode()).hexdigest()[:16], **f.meta} for f in ev.fuentes],
        "archivos": ev.arbol,
        "imagenes": [n for n, _, _ in ev.imagenes],
        "advertencias": ev.advertencias,
    }
