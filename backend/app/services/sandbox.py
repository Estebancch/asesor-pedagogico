"""Sandbox para verificación técnica del código entregado.

Defensa en profundidad pensada para un contenedor SIN privilegios (Render,
Railway, Docker estándar), donde no se puede anidar Docker ni crear namespaces:

  capa                         qué limita
  ---------------------------  ------------------------------------------------
  directorio temporal propio   el código solo ve una copia de la entrega
  entorno limpio               sin variables del servidor (claves, URL de BD)
  setrlimit                    CPU, memoria, nº de procesos, tamaño de archivos
  límite por prueba            una prueba colgada falla sola; las demás se reportan
  tiempo de pared              se mata el grupo de procesos al vencer
  seccomp-BPF                  sin sockets → sin red (a nivel de kernel)
  audit hook de Python         sin red, subprocesos, ctypes ni archivos ajenos
  usuario sin privilegios      si el servidor corre como root, baja a `nobody`
  PR_SET_DUMPABLE=0 (padre)    /proc/<servidor>/environ deja de ser legible

No equivale a una microVM (gVisor/Firecracker). Para producción con código
hostil se recomienda mover esta ejecución a un worker con ese aislamiento; la
interfaz `ejecutar()` está pensada para poder sustituirse.
"""
from __future__ import annotations

import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..config import obtener_ajustes

RUNNER = str(Path(__file__).with_name("sandbox_runner.py"))
MAX_SALIDA = 60_000


@dataclass
class ResultadoSandbox:
    codigo_salida: int | None
    salida: str
    errores: str
    vencio_tiempo: bool
    duracion_s: float
    capas: dict = field(default_factory=dict)
    limites: dict = field(default_factory=dict)


def proteger_proceso_servidor() -> bool:
    """Impide que procesos del mismo usuario lean /proc/<pid>/environ del servidor."""
    try:
        import ctypes
        return ctypes.CDLL(None, use_errno=True).prctl(4, 0, 0, 0, 0) == 0  # PR_SET_DUMPABLE
    except Exception:
        return False


def crear_directorio() -> str:
    d = tempfile.mkdtemp(prefix="asesor_sbx_")
    os.makedirs(os.path.join(d, ".tmp"), exist_ok=True)
    return d


def limpiar(directorio: str) -> None:
    shutil.rmtree(directorio, ignore_errors=True)


def escribir_archivos(directorio: str, archivos: dict[str, bytes]) -> list[str]:
    """Escribe la copia de la entrega. Las rutas ya vienen saneadas por extraccion.py,
    pero se vuelve a comprobar que nada escape del directorio."""
    base = os.path.realpath(directorio)
    escritos = []
    for rel, datos in archivos.items():
        destino = os.path.realpath(os.path.join(base, rel))
        if not destino.startswith(base + os.sep):
            continue
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(datos)
        escritos.append(rel)
    return escritos


def ejecutar(directorio: str, modo: str, *, args: list[str] | None = None, archivos: list[str] | None = None,
             timeout_s: int | None = None) -> ResultadoSandbox:
    aj = obtener_ajustes()
    timeout_s = timeout_s or aj.sandbox_timeout_s
    limites = {"tiempo_pared_s": timeout_s, "cpu_s": aj.sandbox_cpu_s, "por_prueba_s": aj.sandbox_prueba_s, "memoria_mb": aj.sandbox_memoria_mb,
               "procesos": 256, "archivo_mb": 20, "red": "permitida" if aj.sandbox_permitir_red else "bloqueada"}
    cfg = {"modo": modo, "trabajo": directorio, "args": args or [], "archivos": archivos or [],
           "permitir_red": aj.sandbox_permitir_red, "por_prueba_s": aj.sandbox_prueba_s}
    entorno = {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": directorio, "TMPDIR": os.path.join(directorio, ".tmp"),
        "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8",
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NO_COLOR": "1",
        "PY_COLORS": "0",
    }
    es_root = os.geteuid() == 0
    if es_root:
        for raiz, dirs, fichs in os.walk(directorio):
            for n in [raiz] + [os.path.join(raiz, f) for f in fichs]:
                try:
                    os.chown(n, 65534, 65534)
                except OSError:
                    pass

    def preparar():
        os.setsid()
        mem = aj.sandbox_memoria_mb * 1024 * 1024
        for recurso, valor in ((resource.RLIMIT_CPU, aj.sandbox_cpu_s), (resource.RLIMIT_AS, mem),
                               (resource.RLIMIT_FSIZE, 20 * 1024 * 1024), (resource.RLIMIT_NOFILE, 256),
                               (resource.RLIMIT_NPROC, 256), (resource.RLIMIT_CORE, 0)):
            try:
                resource.setrlimit(recurso, (valor, valor))
            except (ValueError, OSError):
                pass
        if es_root:
            os.setgroups([])
            os.setgid(65534)
            os.setuid(65534)

    salida_f = os.path.join(directorio, ".tmp", "stdout.txt")
    error_f = os.path.join(directorio, ".tmp", "stderr.txt")
    inicio = time.time()
    vencio = False
    with open(salida_f, "wb") as so, open(error_f, "wb") as se:
        proc = subprocess.Popen(
            [sys.executable, "-I", "-X", "utf8", RUNNER, json.dumps(cfg)],
            cwd=directorio, env=entorno, stdin=subprocess.DEVNULL, stdout=so, stderr=se,
            close_fds=True, preexec_fn=preparar,
        )
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            vencio = True
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)  # también limpia procesos huérfanos del grupo
            except (ProcessLookupError, PermissionError):
                pass
            proc.wait()

    def leer(ruta):
        try:
            with open(ruta, "rb") as f:
                datos = f.read(MAX_SALIDA + 1)
            txt = datos[:MAX_SALIDA].decode("utf-8", "replace")
            return txt + ("\n… (salida truncada)" if len(datos) > MAX_SALIDA else "")
        except OSError:
            return ""

    capas = {"seccomp": False, "audit_hook": False}
    try:
        with open(os.path.join(directorio, ".sandbox_capas.json")) as f:
            capas.update(json.load(f))
    except (OSError, ValueError):
        pass
    capas.update({"rlimits": True, "entorno_limpio": True, "directorio_aislado": True,
                  "usuario_sin_privilegios": es_root or os.geteuid() != 0})
    return ResultadoSandbox(codigo_salida=None if vencio else proc.returncode, salida=leer(salida_f),
                            errores=leer(error_f), vencio_tiempo=vencio,
                            duracion_s=round(time.time() - inicio, 2), capas=capas, limites=limites)
