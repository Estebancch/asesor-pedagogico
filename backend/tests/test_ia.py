import json

import httpx
import pytest
from pydantic import BaseModel

from app.services.ia import crear_proveedor
from app.services.ia.base import ErrorIA, esquema_plano, generar_estructurado


class Salida(BaseModel):
    nivel: str
    puntos: int


def _proveedor(nombre, manejador):
    return crear_proveedor({"proveedor": nombre, "modelo": "modelo-x", "_api_key": "clave", "temperatura": 0.0,
                            "base_url": "https://ia.test/v1"}, transporte=httpx.MockTransport(manejador))


def test_gemini_envia_esquema_y_degrada_al_formato_anterior():
    vistos = []

    def manejador(req: httpx.Request):
        cuerpo = json.loads(req.content)
        vistos.append(cuerpo["generationConfig"])
        assert req.headers["x-goog-api-key"] == "clave" and req.url.path.endswith("/models/modelo-x:generateContent")
        if "responseFormat" in cuerpo["generationConfig"]:
            return httpx.Response(400, json={"error": {"message": "Unknown name responseFormat"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"nivel": "alto", "puntos": 3}'}]}}],
                                         "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15}})

    obj, resp = generar_estructurado(_proveedor("gemini", manejador), Salida, sistema="s", usuario="u")
    assert obj.puntos == 3 and resp.uso["tokens_total"] == 15
    assert vistos[0]["responseFormat"]["text"]["schema"] == esquema_plano(Salida)
    assert vistos[1]["responseJsonSchema"] == esquema_plano(Salida) and vistos[1]["responseMimeType"] == "application/json"


def test_reintenta_con_el_error_de_validacion():
    llamadas = []

    def manejador(req):
        cuerpo = json.loads(req.content)
        llamadas.append(cuerpo["messages"][1]["content"])
        texto = '{"nivel": "alto"}' if len(llamadas) == 1 else '```json\n{"nivel": "alto", "puntos": 4}\n```'
        return httpx.Response(200, json={"choices": [{"message": {"content": texto}}], "usage": {"total_tokens": 7}})

    obj, resp = generar_estructurado(_proveedor("openai", manejador), Salida, sistema="s", usuario="u")
    assert obj.puntos == 4 and resp.intentos == 2 and "NO fue aceptada" in llamadas[1]


def test_claude_usa_herramienta_forzada():
    def manejador(req):
        cuerpo = json.loads(req.content)
        assert cuerpo["tool_choice"] == {"type": "tool", "name": "registrar_resultado"}
        assert cuerpo["tools"][0]["input_schema"] == esquema_plano(Salida)
        return httpx.Response(200, json={"content": [{"type": "tool_use", "input": {"nivel": "medio", "puntos": 2}}],
                                         "usage": {"input_tokens": 3, "output_tokens": 4}})

    obj, _ = generar_estructurado(_proveedor("anthropic", manejador), Salida, sistema="s", usuario="u")
    assert obj.nivel == "medio"


def test_error_claro_si_la_clave_es_invalida_o_nunca_valida():
    with pytest.raises(ErrorIA, match="clave de API no es válida"):
        _proveedor("gemini", lambda r: httpx.Response(401, json={"error": {"message": "bad key"}})).generar_json(
            sistema="s", usuario="u", esquema={})
    siempre_mal = lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "no soy json"}}]})  # noqa: E731
    with pytest.raises(ErrorIA, match="no produjo una respuesta válida"):
        generar_estructurado(_proveedor("openai", siempre_mal), Salida, sistema="s", usuario="u", reintentos=1)


def test_gemini_saturado_pasa_al_modelo_de_respaldo(monkeypatch):
    monkeypatch.setattr("app.services.ia.base.time.sleep", lambda s: None)
    pedidos = []

    def manejador(req):
        modelo = req.url.path.split("/models/")[1].split(":")[0]
        pedidos.append(modelo)
        if modelo == "modelo-x":
            return httpx.Response(503, json={"error": {"message": "This model is currently experiencing high demand."}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({"nivel": "alto", "puntos": 4})}]}}],
                                         "modelVersion": modelo})

    obj, resp = generar_estructurado(_proveedor("gemini", manejador), Salida, sistema="s", usuario="u")
    assert obj.nivel == "alto" and resp.modelo == "gemini-3.6-flash"
    assert pedidos.count("modelo-x") == 4 and pedidos[-1] == "gemini-3.6-flash"


def test_gemini_clave_invalida_no_prueba_respaldo():
    pedidos = []

    def manejador(req):
        pedidos.append(req.url.path)
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    with pytest.raises(ErrorIA):
        _proveedor("gemini", manejador).generar_json(sistema="s", usuario="u", esquema={"type": "object"})
    assert len(pedidos) == 1


def test_gemini_sin_respuesta_a_tiempo_pasa_al_respaldo(monkeypatch):
    monkeypatch.setattr("app.services.ia.base.time.sleep", lambda s: None)
    pedidos = []

    def manejador(req):
        modelo = req.url.path.split("/models/")[1].split(":")[0]
        pedidos.append(modelo)
        if modelo == "modelo-x":
            raise httpx.ReadTimeout("sin respuesta", request=req)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({"nivel": "medio", "puntos": 3})}]}}],
                                         "modelVersion": modelo})

    obj, resp = generar_estructurado(_proveedor("gemini", manejador), Salida, sistema="s", usuario="u")
    assert resp.modelo == "gemini-3.6-flash"
    assert pedidos.count("modelo-x") == 1  # no insiste con el modelo que no respondió


def test_gemini_cuota_agotada_pasa_al_respaldo_tras_un_reintento(monkeypatch):
    monkeypatch.setattr("app.services.ia.base.time.sleep", lambda s: None)
    pedidos = []

    def manejador(req):
        modelo = req.url.path.split("/models/")[1].split(":")[0]
        pedidos.append(modelo)
        if modelo in ("modelo-x", "gemini-3.6-flash"):
            return httpx.Response(429, json={"error": {"message": "Quota exceeded"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({"nivel": "bajo", "puntos": 1})}]}}],
                                         "modelVersion": modelo})

    obj, resp = generar_estructurado(_proveedor("gemini", manejador), Salida, sistema="s", usuario="u")
    assert resp.modelo == "gemini-3.5-flash-lite"
    assert pedidos.count("modelo-x") == 2 and pedidos.count("gemini-3.6-flash") == 2


def test_gemini_todos_saturados_da_error_claro(monkeypatch):
    monkeypatch.setattr("app.services.ia.base.time.sleep", lambda s: None)
    proveedor = _proveedor("gemini", lambda r: httpx.Response(503, json={"error": {"message": "high demand"}}))
    with pytest.raises(ErrorIA, match="503"):
        proveedor.generar_json(sistema="s", usuario="u", esquema={"type": "object"})
