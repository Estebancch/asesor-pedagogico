import copy

from app.services import rubricas as srv
from tests.conftest import rubrica_ejemplo


def _codigos(r):
    return {i.codigo for i in srv.validar(r)}


def test_rubrica_valida_no_tiene_errores():
    r = srv.Rubrica.model_validate(rubrica_ejemplo())
    assert not srv.tiene_errores(srv.validar(r))


def test_detecta_ponderaciones_que_no_suman_100():
    d = copy.deepcopy(rubrica_ejemplo())
    d["criterios"][0]["ponderacion"] = 40
    r = srv.Rubrica.model_validate(d)
    assert "PONDERACIONES_NO_SUMAN_100" in _codigos(r)
    srv.normalizar_ponderaciones(r)
    assert abs(sum(c.ponderacion for c in r.criterios) - 100) < 1e-9
    assert "PONDERACIONES_NO_SUMAN_100" not in _codigos(r)


def test_detecta_inconsistencias_estructurales():
    d = copy.deepcopy(rubrica_ejemplo())
    d["niveles"][0]["puntaje"] = 7              # fuera de escala
    d["criterios"][1]["competencia_id"] = "x"   # competencia inexistente
    d["criterios"][2]["descriptores"].pop("bueno")
    d["criterios"][3]["ponderacion"] = 0
    cod = _codigos(srv.Rubrica.model_validate(d))
    assert {"PUNTAJE_FUERA_DE_ESCALA", "COMPETENCIA_INEXISTENTE", "DESCRIPTOR_FALTANTE", "PONDERACION_INVALIDA"} <= cod


def test_lector_de_tablas_csv():
    csv = ("Competencia;Criterio;Ponderación;Excelente (5.0);Bueno (4.0);Insuficiente (2.0)\n"
           "Modelado;Define estados;0,4;Completo;Parcial;Ausente\n"
           ";Define acciones;0,3;Completo;Parcial;Ausente\n"
           "Código;Implementa BFS;0,3;Correcto;Con errores;No ejecuta\n").encode()
    contenido = srv.extraer_contenido("rubrica.csv", csv)
    r = srv.desde_tabla(contenido.tablas[0])
    assert [n.puntaje for n in r.niveles] == [5.0, 4.0, 2.0]
    assert [c.ponderacion for c in r.criterios] == [40, 30, 30]      # fracciones → porcentaje
    assert len(r.competencias) == 2 and r.criterios[1].competencia_id == r.criterios[0].competencia_id
    assert not srv.tiene_errores(srv.validar(r))


def test_niveles_sin_puntaje_se_infieren_y_se_avisa():
    filas = [["Criterio", "Peso", "Excelente", "Aceptable", "Insuficiente"], ["A", "50%", "x", "y", "z"], ["B", "50%", "x", "y", "z"]]
    r = srv.desde_tabla(filas)
    assert [n.puntaje for n in r.niveles] == [5.0, 3.0, 1.0]
    assert any("puntaje" in n for n in r.notas_interpretacion)


def test_hash_cambia_con_el_contenido():
    r = srv.Rubrica.model_validate(rubrica_ejemplo())
    h = srv.hash_rubrica(r)
    r.criterios[0].ponderacion += 1
    assert srv.hash_rubrica(r) != h


def test_celdas_partidas_en_varias_lineas_quedan_en_una():
    r = srv.desde_tabla([["Criterio", "Peso", "Excelente (5.0)", "Bajo (1.0)"],
                              ["Comprensión del\nproblema", "60%", "Formula el\nproblema", "No lo formula"],
                              ["Código", "40%", "Correcto", "No ejecuta"]])
    assert r.criterios[0].nombre == "Comprensión del problema"
    assert "\n" not in "".join(r.criterios[0].descriptores.values())
