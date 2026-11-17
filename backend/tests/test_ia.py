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
