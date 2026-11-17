from __future__ import annotations

import base64

from .base import ErrorIA, ProveedorIA, RespuestaIA


class Gemini(ProveedorIA):
    """Google Gemini por REST (generateContent) con salida estructurada.

    La documentación vigente (nov. 2026) define el esquema en
    generationConfig.responseFormat.text; versiones anteriores de la API usaban
    responseMimeType + responseJsonSchema. Se intenta el formato actual y, si el
    servicio lo rechaza con 400, se degrada al anterior y luego a JSON sin
    esquema: en todos los casos la respuesta se valida después con Pydantic.
    """
    nombre = "gemini"
    multimodal = True
    acepta_pdf = True

    def _variantes(self, esquema: dict) -> list[dict]:
        return [
            {"responseFormat": {"text": {"mimeType": "application/json", "schema": esquema}}},
            {"responseMimeType": "application/json", "responseJsonSchema": esquema},
            {"responseMimeType": "application/json"},
        ]

    def generar_json(self, *, sistema, usuario, esquema, adjuntos=None, contexto=None) -> RespuestaIA:
        if not self.api_key:
            raise ErrorIA("Falta la clave de API de Gemini. Configúrala en Administración → Modelo de IA "
                          "o en la variable GEMINI_API_KEY.")
        partes: list[dict] = []
        for a in adjuntos or []:
            partes.append({"inlineData": {"mimeType": a.mime, "data": base64.b64encode(a.datos).decode()}})
        partes.append({"text": usuario})
        url = f"{self.base_url}/models/{self.modelo}:generateContent"
        cab = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        ultimo = None
        variantes = self._variantes(esquema)
        for i, cfg in enumerate(variantes):
            gen = dict(cfg)
            if self.temperatura is not None:
                gen["temperature"] = self.temperatura
            cuerpo = {"systemInstruction": {"parts": [{"text": sistema}]},
                      "contents": [{"role": "user", "parts": partes}], "generationConfig": gen}
            r = self._post(url, cuerpo, cab)
            if r.status_code == 400 and i < len(variantes) - 1 and "API key" not in r.text:
                ultimo = r  # el servicio no aceptó esta forma de pedir el esquema: se prueba la siguiente
                continue
            if r.status_code != 200:
                raise self._error(r, "Gemini")
            datos = r.json()
            cands = datos.get("candidates") or []
            if not cands:
                raise ErrorIA(f"Gemini no devolvió contenido (posible bloqueo de seguridad): {str(datos.get('promptFeedback'))[:300]}")
            texto = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []) if not p.get("thought"))
            if not texto.strip():
                raise ErrorIA(f"Gemini devolvió una respuesta vacía (finishReason={cands[0].get('finishReason')}).")
            um = datos.get("usageMetadata", {})
            return RespuestaIA(texto=texto, modelo=datos.get("modelVersion", self.modelo),
                               uso={"tokens_entrada": um.get("promptTokenCount", 0),
                                    "tokens_salida": um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0),
                                    "tokens_total": um.get("totalTokenCount", 0)})
        raise self._error(ultimo, "Gemini")  # pragma: no cover

    def listar_modelos(self) -> list[str]:
        with self._cliente() as c:
            r = c.get(f"{self.base_url}/models", params={"pageSize": 200}, headers={"x-goog-api-key": self.api_key})
        if r.status_code != 200:
            raise self._error(r, "Gemini")
        return sorted(m["name"].split("/", 1)[-1] for m in r.json().get("models", [])
                      if "generateContent" in m.get("supportedGenerationMethods", ["generateContent"]))
