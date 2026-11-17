"""Recorrido completo por la API con el proveedor simulado: rúbrica → entrega →
evaluación → revisión docente → publicación → informe y mapa."""
import copy
import io
import zipfile

from app.seed import _pdf
from app.seed_datos import CODIGO, INFORMES
from tests.conftest import rubrica_ejemplo

estado = {}


def _zip(archivos):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, t in archivos.items():
            z.writestr(n, t)
    return buf.getvalue()


def test_usuarios_y_permisos(cliente, admin):
    r = cliente.post("/api/usuarios", headers=admin, json={"nombre": "Profe Uno", "email": "profe@test.co", "password": "Profe12345", "rol": "docente"})
    assert r.status_code == 201
    assert cliente.post("/api/auth/registro", json={"nombre": "Ana Est", "email": "ana@test.co", "password": "corta"}).status_code == 422
    for nombre, email in (("Ana Estudiante", "ana@test.co"), ("Beto Estudiante", "beto@test.co")):
        r = cliente.post("/api/auth/registro", json={"nombre": nombre, "email": email, "password": "Clave12345"})
        assert r.status_code == 201 and r.json()["usuario"]["rol"] == "estudiante"
        estado[email] = {"h": {"Authorization": "Bearer " + r.json()["token"]}, "id": r.json()["usuario"]["id"]}
    r = cliente.post("/api/auth/login", json={"email": "profe@test.co", "password": "Profe12345"})
    estado["docente"] = {"Authorization": "Bearer " + r.json()["token"]}
    assert cliente.get("/api/cohortes").status_code == 401
    assert cliente.get("/api/usuarios", headers=estado["ana@test.co"]["h"]).status_code == 403
    assert cliente.post("/api/laboratorios", headers=estado["ana@test.co"]["h"], json={"cohorte_id": 1, "titulo": "Intruso"}).status_code == 403
    assert cliente.post("/api/auth/login", json={"email": "ana@test.co", "password": "incorrecta1"}).status_code == 401


def test_laboratorio_y_rubrica_con_inconsistencias(cliente):
    h = estado["docente"]
    cohortes = cliente.get("/api/cohortes", headers=h).json()
    assert [c["numero"] for c in cohortes] == [1, 2]
    r = cliente.post("/api/laboratorios", headers=h, json={"cohorte_id": cohortes[0]["id"], "titulo": "Agentes de búsqueda",
                                                           "descripcion": "BFS y A* en laberintos", "objetivos": "Implementar y comparar"})
    lab = estado["lab"] = r.json()["id"]
    mala = copy.deepcopy(rubrica_ejemplo())
    mala["criterios"][0]["ponderacion"] = 45  # suma 120
    rv = cliente.post(f"/api/laboratorios/{lab}/rubricas", headers=h, json={"contenido": mala}).json()
    assert rv["estado"] == "borrador" and rv["errores"] == 1
    assert cliente.post(f"/api/rubricas/{rv['id']}/validar", headers=h).status_code == 422
    # sin rúbrica validada no se puede evaluar
    ana = estado["ana@test.co"]["h"]
    archivos = {"informe": ("informe.pdf", _pdf("Lab", "Ana", INFORMES["busqueda"]), "application/pdf"),
                "codigo": ("codigo.zip", _zip(CODIGO["busqueda"]), "application/zip")}
    e = cliente.post(f"/api/laboratorios/{lab}/entregas", headers=ana, files=archivos, data={"comentario": "primer intento"})
    assert e.status_code == 201, e.text
    estado["entrega"] = e.json()["id"]
    assert cliente.post(f"/api/entregas/{estado['entrega']}/evaluar", headers=ana, json={}).status_code == 409
    # corregir: guardar con ponderaciones correctas y validar
    r = cliente.put(f"/api/rubricas/{rv['id']}", headers=h, json=rubrica_ejemplo())
    assert r.json()["errores"] == 0
    r = cliente.post(f"/api/rubricas/{rv['id']}/validar", headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "validada"
    assert cliente.put(f"/api/rubricas/{rv['id']}", headers=h, json=rubrica_ejemplo()).status_code == 409  # inmutable
    estado["rubrica"] = rv["id"]


def test_validaciones_de_entrega(cliente):
    ana, lab = estado["ana@test.co"]["h"], estado["lab"]
    pdf = ("informe.pdf", _pdf("Lab", "Ana", INFORMES["busqueda"]), "application/pdf")
    assert cliente.post(f"/api/laboratorios/{lab}/entregas", headers=ana, files={"informe": pdf}).status_code == 422  # sin código
    falso = {"informe": ("informe.pdf", b"no soy un pdf", "application/pdf"), "codigo": ("c.zip", _zip({"a.py": "x=1"}), "application/zip")}
    assert cliente.post(f"/api/laboratorios/{lab}/entregas", headers=ana, files=falso).status_code == 422
    r = cliente.post(f"/api/laboratorios/{lab}/entregas", headers=ana, files={"informe": pdf}, data={"repo_url": "http://evil.test/x"})
    assert r.status_code == 422


def test_evaluacion_revision_y_publicacion(cliente):
    ana, beto, h = estado["ana@test.co"]["h"], estado["beto@test.co"]["h"], estado["docente"]
    r = cliente.post(f"/api/entregas/{estado['entrega']}/evaluar", headers=ana, json={})
    assert r.status_code == 202
    vid = estado["eval"] = r.json()["id"]  # BackgroundTasks corre antes de devolver en TestClient
    d = cliente.get(f"/api/evaluaciones/{vid}", headers=h).json()
    assert d["estado"] == "preliminar", d.get("error")
    assert 0 <= d["nota"] <= 5 and d["nota"] == d["calculo"]["nota"]
    assert len(d["resultado"]["criterios"]) == 4 and d["resultado"]["citas"]["no_verificadas"] == 0
    assert d["verificacion"]["pruebas"]["estado"] == "ok" and d["verificacion"]["sandbox"]["capas"]["audit_hook"]
    t = d["trazabilidad"]
    assert t["modelo"] == "heuristico-v1" and t["rubrica_version"] == 1 and len(t["hash_evidencias"]) == 64
    assert any(f["id"] == "verificacion:resumen" for f in t["evidencias"]["fuentes"])
    # el estudiante no ve el resultado hasta que se publica; otro estudiante no ve nada
    propio = cliente.get(f"/api/evaluaciones/{vid}", headers=ana).json()
    assert propio["visible"] is False and "resultado" not in propio
    assert cliente.get(f"/api/evaluaciones/{vid}", headers=beto).status_code == 403
    assert cliente.get(f"/api/archivos/{d['entrega']['informe']['id']}", headers=beto).status_code == 403
    assert cliente.get(f"/api/archivos/{d['entrega']['informe']['id']}", headers=ana).content.startswith(b"%PDF")
    # una cita se puede comprobar contra la fuente analizada
    cita = d["resultado"]["criterios"][0]["evidencias"][0]
    fuente = cliente.get(f"/api/evaluaciones/{vid}/fuente", headers=h, params={"id": cita["fuente"]}).json()
    assert cita["cita"][:30] in fuente["texto"]
    # ajuste docente: exige motivo, recalcula la nota en el backend y queda en la auditoría
    url = f"/api/evaluaciones/{vid}/criterios/analisis"
    assert cliente.patch(url, headers=h, json={"nivel_id": "insuficiente"}).status_code == 422
    assert cliente.patch(url, headers=ana, json={"nivel_id": "excelente", "comentario": "yo"}).status_code == 403
    antes = d["nota"]
    d2 = cliente.patch(url, headers=h, json={"nivel_id": "insuficiente", "comentario": "El análisis no compara datos."}).json()
    por_id = {c["criterio_id"]: c for c in d2["calculo"]["desglose"]}
    assert por_id["analisis"]["puntaje"] == 1.5 and d2["nota"] <= antes
    assert abs(d2["calculo"]["suma_exacta"] - sum(x["ponderacion"] * x["puntaje"] / 100 for x in d2["calculo"]["desglose"])) < 1e-6
    aud = cliente.get(f"/api/evaluaciones/{vid}/auditoria", headers=h).json()
    assert [a["accion"] for a in aud][-1] == "criterio_ajustado" and aud[-1]["detalle"]["nota_despues"] == d2["nota"]
    # aprobar y publicar
    assert cliente.post(f"/api/evaluaciones/{vid}/aprobar", headers=h).json()["estado"] == "aprobada"
    pub = cliente.post(f"/api/evaluaciones/{vid}/publicar", headers=h).json()
    assert pub["estado"] == "publicada" and pub["nota_final"] == d2["nota"]
    visto = cliente.get(f"/api/evaluaciones/{vid}", headers=ana).json()
    assert visto["visible"] and visto["nota"] == d2["nota"]
    assert cliente.patch(url, headers=h, json={"nivel_id": "bueno", "comentario": "x"}).status_code == 409  # publicada → reabrir


def test_reproducibilidad_reutiliza_el_resultado(cliente):
    h = estado["docente"]
    r = cliente.post(f"/api/entregas/{estado['entrega']}/evaluar", headers=h, json={})
    d = cliente.get(f"/api/evaluaciones/{r.json()['id']}", headers=h).json()
    assert d["estado"] == "preliminar"
    assert d["trazabilidad"]["parametros"]["reutilizada_de_evaluacion"] == estado["eval"]
    assert d["trazabilidad"]["clave_reproducibilidad"] == cliente.get(f"/api/evaluaciones/{estado['eval']}", headers=h).json()["trazabilidad"]["clave_reproducibilidad"]
    assert cliente.delete(f"/api/evaluaciones/{r.json()['id']}", headers=h).status_code == 200


def test_informe_y_mapa(cliente):
    ana, beto, h = estado["ana@test.co"], estado["beto@test.co"], estado["docente"]
    inf = cliente.post(f"/api/informes/{ana['id']}/generar", headers=ana["h"]).json()
    assert inf["datos"]["evaluados"] == 1 and inf["datos"]["promedio"] is not None and inf["narrativa"]["resumen_ejecutivo"]
    assert inf["datos"]["competencias"] and inf["datos"]["laboratorios"][0]["estado"] == "publicada"
    pdf = cliente.get(f"/api/informes/{ana['id']}/pdf", headers=ana["h"])
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and len(pdf.content) > 2000
    assert cliente.get(f"/api/informes/{ana['id']}", headers=beto["h"]).status_code == 403
    assert cliente.post(f"/api/informes/{beto['id']}/generar", headers=beto["h"]).status_code == 409  # sin evaluaciones
    mapa = cliente.get(f"/api/mapa/{ana['id']}", headers=ana["h"]).json()
    tipos = [n["tipo"] for n in mapa["nodos"]]
    assert tipos[0] == "raiz" and "categoria" in tipos and "tema" in tipos
    tema = next(n for n in mapa["nodos"] if n["tipo"] == "tema")
    assert tema["laboratorios"][0]["titulo"] == "Agentes de búsqueda" and tema["dominio_etiqueta"]
    assert all(a["origen"] in {n["id"] for n in mapa["nodos"]} for a in mapa["aristas"])
    matriz = cliente.get("/api/portafolio/matriz", headers=h).json()
    assert len(matriz["filas"]) == 2
    port = cliente.get("/api/portafolio", headers=ana["h"]).json()
    assert port["cohortes"][0]["laboratorios"][0]["entregas"][0]["evaluaciones"][0]["estado"] == "publicada"


def test_admin_config_y_proyecto(cliente, admin):
    cfg = cliente.get("/api/config/ia", headers=admin).json()
    assert cfg["proveedor"] == "simulado" and "_api_key" not in cfg
    r = cliente.put("/api/config/ia", headers=admin, json={"proveedor": "gemini", "modelo": "gemini-3.8-flash", "api_key": "AIzaSECRETA-123456"})
    assert r.json()["clave_configurada"] and r.json()["clave_pista"] == "…3456" and "AIzaSECRETA" not in r.text
    cliente.put("/api/config/ia", headers=admin, json={"proveedor": "simulado"})
    assert cliente.get("/api/config/ia", headers=estado["docente"]).status_code == 403
    pub = cliente.get("/api/publico/proyecto").json()
    assert pub["proyecto"]["abstract"] and len(pub["equipo"]) == 3
    iid = pub["equipo"][0]["id"]
    assert cliente.patch(f"/api/proyecto/integrantes/{iid}", headers=admin, json={"nombre": "Nicolás", "rol": "Líder"}).json()["nombre"] == "Nicolás"
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    foto = cliente.post(f"/api/proyecto/integrantes/{iid}/foto", headers=admin, files={"foto": ("f.png", png, "image/png")}).json()["foto"]
    assert cliente.get(foto).content == png
    assert cliente.post(f"/api/proyecto/integrantes/{iid}/foto", headers=admin, files={"foto": ("f.png", b"<svg>", "image/png")}).status_code == 422


def test_instalacion_anterior_pasa_de_cohorte_a_corte():
    from app.db import SesionLocal
    from app.main import inicializar
    from app.models import Cohorte, Config
    with SesionLocal() as db:
        for c in db.query(Cohorte):
            c.nombre = f"Cohorte {c.numero}"
        fila = db.get(Config, "proyecto")
        if fila is None:
            db.add(Config(clave="proyecto", valor={"abstract": "Laboratorios de las cohortes 1 y 2.", "objetivos": ["Consolidar las dos cohortes."]}))
        else:
            fila.valor = {**fila.valor, "abstract": "Laboratorios de las cohortes 1 y 2."}
        db.commit()
    inicializar()
    with SesionLocal() as db:
        assert sorted(c.nombre for c in db.query(Cohorte)) == ["Corte 1", "Corte 2"]
        assert "los cortes 1 y 2" in db.get(Config, "proyecto").valor["abstract"]
