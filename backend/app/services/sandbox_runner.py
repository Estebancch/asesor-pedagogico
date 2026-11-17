"""Proceso hijo del sandbox. Se ejecuta con `python -I` y aplica el aislamiento
ANTES de tocar código entregado por estudiantes:

1. seccomp-BPF (kernel): niega socket(), io_uring, ptrace y process_vm_*  → sin red.
2. Audit hook de Python (PEP 578): niega red, subprocesos, escritura fuera del
   directorio de trabajo, lectura fuera de la lista permitida y carga de binarios.

Los límites de CPU, memoria, procesos y tamaño de archivo los fija el padre
(sandbox.py) con setrlimit antes del exec.

Modos:  analizar  → análisis sin ejecutar código (ast + pyflakes)
        pytest    → ejecuta pruebas unitarias
"""
import json
import os
import sys


def aplicar_seccomp():
    """Devuelve True si el filtro quedó instalado."""
    import ctypes
    import platform

    arq = platform.machine()
    if arq == "x86_64":
        audit, negados, x32 = 0xC000003E, [41, 425, 101, 310, 311], True
    elif arq == "aarch64":
        audit, negados, x32 = 0xC00000B7, [198, 425, 117, 270, 271], False
    else:
        return False

    class SockFilter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]

    class SockFprog(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(SockFilter))]

    LD, JEQ, JGE, RET = 0x20, 0x15, 0x35, 0x06
    PERMITIR, NEGAR = 0x7FFF0000, 0x00050000 | 13  # ERRNO(EACCES)
    ins = [(LD, 0, 0, 4), (JEQ, 1, 0, audit), (RET, 0, 0, NEGAR), (LD, 0, 0, 0)]
    if x32:
        ins += [(JGE, 0, 1, 0x40000000), (RET, 0, 0, NEGAR)]
    for nr in negados:
        ins += [(JEQ, 0, 1, nr), (RET, 0, 0, NEGAR)]
    ins.append((RET, 0, 0, PERMITIR))
    arr = (SockFilter * len(ins))(*[SockFilter(*i) for i in ins])
    prog = SockFprog(len(ins), arr)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        return False
    return libc.prctl(22, 2, ctypes.byref(prog), 0, 0) == 0  # PR_SET_SECCOMP, MODE_FILTER


def instalar_audit_hook(trabajo, permitir_red):
    real = os.path.realpath
    trabajo = real(trabajo)
    lectura_ok = tuple({real(p) for p in (
        trabajo, sys.prefix, sys.base_prefix, sys.exec_prefix, "/usr/lib", "/usr/local/lib", "/lib", "/lib64",
        "/usr/share/zoneinfo", "/usr/share/locale", "/etc/localtime", "/etc/mime.types",
        "/dev/null", "/dev/urandom", "/dev/random", "/proc/self", "/proc/cpuinfo", "/proc/meminfo",
        "/proc/stat", "/sys/devices/system/cpu", "/sys/fs/cgroup", os.path.dirname(os.path.abspath(__file__)),
    ) if p})
    red = {"socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname",
           "socket.gethostbyaddr", "socket.sendto", "socket.sendmsg"}
    procesos = {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.fork", "os.forkpty",
                "os.spawn", "pty.spawn", "os.kill", "os.killpg"}
    binarios = {"ctypes.dlopen", "ctypes.dlsym", "ctypes.dlsym/handle", "ctypes.cdata", "ctypes.cdata/buffer"}

    def dentro(ruta, bases):
        return any(ruta == b or ruta.startswith(b + os.sep) for b in bases)

    def hook(evento, args):
        if evento in red and not permitir_red:
            raise PermissionError("sandbox: el acceso a la red está deshabilitado")
        if evento in procesos:
            raise PermissionError("sandbox: no se permite crear ni señalar procesos (%s)" % evento)
        if evento in binarios:
            raise PermissionError("sandbox: no se permite cargar código nativo con ctypes")
        if evento == "import" and args and args[1]:
            f = str(args[1])
            if f.endswith((".so", ".pyd", ".dll")) and dentro(real(f), (trabajo,)):
                raise PermissionError("sandbox: no se permite importar binarios entregados")
        if evento == "sqlite3.connect" and args:
            db = str(args[0])
            if db != ":memory:" and not dentro(real(db), (trabajo,)):
                raise PermissionError("sandbox: base de datos fuera del directorio de trabajo")
        if evento == "open" and args:
            ruta, modo, flags = args[0], args[1], args[2] if len(args) > 2 else 0
            if isinstance(ruta, int):
                return
            if isinstance(ruta, bytes):
                ruta = ruta.decode("utf-8", "replace")
            ruta = real(str(ruta))
            escribe = (isinstance(modo, str) and any(c in modo for c in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if escribe:
                if not (dentro(ruta, (trabajo,)) or ruta == "/dev/null"):
                    raise PermissionError("sandbox: escritura fuera del directorio de trabajo: %s" % ruta)
            elif not dentro(ruta, lectura_ok):
                raise PermissionError("sandbox: lectura no permitida: %s" % ruta)
        if evento in ("os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.chown",
                      "os.truncate", "os.symlink", "os.link", "shutil.rmtree", "shutil.move") and args:
            for a in args[:2]:
                if isinstance(a, (str, bytes)) and not dentro(real(os.fsdecode(a)), (trabajo,)):
                    raise PermissionError("sandbox: operación de archivos fuera del directorio de trabajo")

    sys.addaudithook(hook)


class TiempoAgotado(BaseException):
    """No hereda de Exception: un `except Exception` del código entregado no la puede tragar."""


def limite_por_prueba(segundos):
    """Plugin de pytest: corta con SIGALRM la prueba que supere el límite, para que
    un bucle infinito falle esa prueba y no se pierda el resultado de las demás."""
    import signal

    import pytest

    class Limite:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_call(self, item):
            def vencer(signum, frame):
                raise TiempoAgotado("sandbox: la prueba superó el límite de %s s y se detuvo" % segundos)
            previo = signal.signal(signal.SIGALRM, vencer)
            signal.setitimer(signal.ITIMER_REAL, segundos)
            try:
                yield
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previo)

    return Limite()


def main():
    cfg = json.loads(sys.argv[1])
    trabajo = cfg["trabajo"]
    os.chdir(trabajo)
    capas = {"seccomp": False, "audit_hook": False}
    if not cfg.get("permitir_red"):
        try:
            capas["seccomp"] = bool(aplicar_seccomp())
        except Exception:
            capas["seccomp"] = False
    # Los módulos de análisis se importan antes del hook (no ejecutan código entregado).
    if cfg["modo"] == "analizar":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import analizador  # noqa
    else:
        import pytest  # noqa
    instalar_audit_hook(trabajo, bool(cfg.get("permitir_red")))
    capas["audit_hook"] = True
    with open(os.path.join(trabajo, ".sandbox_capas.json"), "w") as f:
        json.dump(capas, f)

    if cfg["modo"] == "analizar":
        resultado = analizador.analizar(trabajo, cfg.get("archivos", []))
        with open(os.path.join(trabajo, ".resultado_analisis.json"), "w") as f:
            json.dump(resultado, f)
        return 0
    for extra in (trabajo, os.path.join(trabajo, "src")):
        if os.path.isdir(extra) and extra not in sys.path:
            sys.path.insert(0, extra)
    sys.dont_write_bytecode = True
    por_prueba = float(cfg.get("por_prueba_s") or 0)
    return int(pytest.main(cfg.get("args", []), plugins=[limite_por_prueba(por_prueba)] if por_prueba > 0 else []))


if __name__ == "__main__":
    sys.exit(main())
