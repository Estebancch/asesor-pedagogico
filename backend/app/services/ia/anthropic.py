from __future__ import annotations

import base64

from .base import ErrorIA, ProveedorIA, RespuestaIA


class Anthropic(ProveedorIA):
    """Claude por la API de Messages. La salida estructurada se obtiene forzando
    el uso de una herramienta cuyo input_schema es el esquema pedido."""
    nombre = "anthropic"
    multimodal = True
    acepta_pdf = True

    def _cab(self) -> dict:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}

    def generar_json(self, *, sistema, usuario, esquema, adjuntos=None, contexto=None) -> RespuestaIA:
        if not self.api_key:
            raise ErrorIA("Falta la clave de API de Anthropic (ANTHROPIC_API_KEY o Administración → Modelo de IA).")
        bloques: list[dict] = []
        for a in adjuntos or []:
            fuente = {"type": "base64", "media_type": a.mime, "data": base64.b64encode(a.datos).decode()}
            if a.mime == "application/pdf":
                bloques.append({"type": "document", "source": fuente})
            elif a.mime.startswith("image/"):
                bloques.append({"type": "image", "source": fuente})
        bloques.append({"type": "text", "text": usuario})
        cuerpo = {"model": self.modelo, "max_tokens": 16000, "system": sistema,
                  "messages": [{"role": "user", "content": bloques}],
                  "tools": [{"name": "registrar_resultado", "description": "Registra el resultado estructurado.",
                             "input_schema": esquema}],
                  "tool_choice": {"type": "tool", "name": "registrar_resultado"}}
        if self.temperatura is not None:
            cuerpo["temperature"] = self.temperatura
        r = self._post(f"{self.base_url}/messages", cuerpo, self._cab())
        if r.status_code == 400 and "temperature" in r.text and "temperature" in cuerpo:
            cuerpo.pop("temperature")
            r = self._post(f"{self.base_url}/messages", cuerpo, self._cab())
        if r.status_code != 200:
            raise self._error(r, "Anthropic")
        d = r.json()
        datos = next((b.get("input") for b in d.get("content", []) if b.get("type") == "tool_use"), None)
        texto = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
        if datos is None and not texto.strip():
            raise ErrorIA(f"Claude no devolvió contenido (stop_reason={d.get('stop_reason')}).")
        u = d.get("usage", {})
        return RespuestaIA(texto=texto, datos=datos, modelo=d.get("model", self.modelo),
                           uso={"tokens_entrada": u.get("input_tokens", 0), "tokens_salida": u.get("output_tokens", 0),
                                "tokens_total": u.get("input_tokens", 0) + u.get("output_tokens", 0)})

    def listar_modelos(self) -> list[str]:
        with self._cliente() as c:
            r = c.get(f"{self.base_url}/models", headers=self._cab())
        if r.status_code != 200:
            raise self._error(r, "Anthropic")
        return sorted(m.get("id", "") for m in r.json().get("data", []))
