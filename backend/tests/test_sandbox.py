from app.services import verificacion

CODIGO = {
    "calc.py": b"def suma(a, b):\n    return a + b\n",
    "test_calc.py": b"""
import os, socket, subprocess
import pytest
from calc import suma

def test_suma():
    assert suma(2, 3) == 5

def test_sin_red():
    with pytest.raises((PermissionError, OSError)):
        socket.create_connection(("1.1.1.1", 80), timeout=2)

def test_sin_subprocesos():
    with pytest.raises(PermissionError):
        subprocess.run(["ls"])

def test_sin_archivos_ajenos():
    with pytest.raises(PermissionError):
        open("/etc/passwd").read()
    with pytest.raises(PermissionError):
        open("/tmp/fuera_del_sandbox.txt", "w")

def test_entorno_limpio():
    assert not any("SECRET" in k or "API_KEY" in k or "DATABASE" in k for k in os.environ)
""",
}


def test_pruebas_pasan_y_el_aislamiento_funciona():
    v = verificacion.verificar(CODIGO)
    assert v["sintaxis"]["estado"] == "ok"
    assert v["pruebas"]["estado"] == "ok" and v["pruebas"]["total"] == 5, v["pruebas"]["salida"]
    assert v["sandbox"]["capas"]["audit_hook"] and v["sandbox"]["limites"]["red"] == "bloqueada"


def test_error_de_sintaxis_y_hallazgos_estaticos():
    v = verificacion.verificar({"a.py": b"def f(:\n    pass\n", "b.py": b"import os\nprint(no_definida)\nAPI_KEY = 'AIzaSyA1234567890abcdefghijklmnopqrstuv'\n"})
    assert v["sintaxis"]["estado"] == "falla" and v["sintaxis"]["errores"][0]["archivo"] == "a.py"
    assert v["analisis_estatico"]["estado"] == "falla"
    assert any(h.get("regla") == "UndefinedName" for h in v["analisis_estatico"]["hallazgos"])
    assert v["analisis_estatico"]["seguridad"]
    assert v["pruebas"]["estado"] == "sin_pruebas"


def test_bucle_infinito_se_detiene(monkeypatch):
    from app.config import obtener_ajustes
    monkeypatch.setattr(obtener_ajustes(), "sandbox_timeout_s", 4)
    monkeypatch.setattr(obtener_ajustes(), "sandbox_cpu_s", 2)
    v = verificacion.verificar({"test_x.py": b"def test_x():\n    while True:\n        pass\n"})
    assert v["pruebas"]["estado"] == "error"


def test_pruebas_del_docente_y_dependencia_faltante():
    v = verificacion.verificar({"calc.py": b"def suma(a, b):\n    return a - b\n"},
                               pruebas_docente="from calc import suma\n\ndef test_docente():\n    assert suma(1, 1) == 2\n")
    assert v["pruebas"]["estado"] == "falla" and v["pruebas"]["origen"]["docente"]
    v = verificacion.verificar({"test_m.py": b"import modulo_que_no_existe_xyz\n\ndef test_a():\n    assert True\n"})
    assert v["pruebas"]["estado"] == "no_ejecutable" and verificacion.falla_regla(v, "pruebas") is None


def test_una_prueba_colgada_no_borra_las_demas(monkeypatch):
    from app.config import obtener_ajustes
    monkeypatch.setattr(obtener_ajustes(), "sandbox_prueba_s", 1)
    codigo = {"test_bucle.py": b"""
def test_rapida():
    assert 1 + 1 == 2

def test_bucle_infinito():
    while True:
        try:
            pass
        except Exception:
            pass
"""}
    p = verificacion.verificar(codigo)["pruebas"]
    assert p["estado"] == "falla" and p["total"] == 2 and p["aprobadas"] == 1, p["salida"]
    assert any("superó el límite" in d["mensaje"] for d in p["detalle"])
