from __future__ import annotations

import base64

from .base import ErrorIA, ProveedorIA, RespuestaIA


class OpenAICompatible(ProveedorIA):
    """API «chat completions» compatible con OpenAI. Cubre OpenAI y, cambiando la
    URL base, modelos locales (Ollama, LM Studio, vLLM) y otros servicios (Groq,
    OpenRouter, Together…)."""
    nombre = "openai"
    multimodal = True
    requiere_clave = True

    def generar_json(self, *, sistema, usuario, esquema, adjuntos=None, contexto=None) -> RespuestaIA:
        if self.requiere_clave and not self.api_key:
            raise ErrorIA("Falta la clave de API (OPENAI_API_KEY o Administración → Modelo de IA).")
        if not self.modelo:
            raise ErrorIA("Indica el nombre del modelo en Administración → Modelo de IA.")
        contenido: list[dict] | str = usuario
        imagenes = [a for a in (adjuntos or []) if a.mime.startswith("image/")]
        if imagenes:
            contenido = [{"type": "text", "text": usuario}] + [
                {"type": "image_url", "image_url": {"url": f"data:{a.mime};base64,{base64.b64encode(a.datos).decode()}"}}
                for a in imagenes]
        base = {"model": self.modelo, "messages": [{"role": "system", "content": sistema},
                                                   {"role": "user", "content": contenido}]}
        formatos = [{"type": "json_schema", "json_schema": {"name": "resultado", "schema": esquema}},
                    {"type": "json_object"}]
        cab = {"Content-Type": "application/json"}
        if self.api_key:
            cab["Authorization"] = f"Bearer {self.api_key}"
        ultimo = None
        for fmt in formatos:
            for con_temp in ((True, False) if self.temperatura is not None else (False,)):
                cuerpo = dict(base, response_format=fmt)
                if con_temp:
                    cuerpo["temperature"] = self.temperatura
                r = self._post(f"{self.base_url}/chat/completions", cuerpo, cab)
                if r.status_code == 400:
                    ultimo = r
                    continue
                if r.status_code != 200:
                    raise self._error(r, self.nombre)
                d = r.json()
                texto = (d.get("choices") or [{}])[0].get("message", {}).get("content") or ""
                if not texto.strip():
                    raise ErrorIA("El modelo devolvió una respuesta vacía.")
                u = d.get("usage", {})
                return RespuestaIA(texto=texto, modelo=d.get("model", self.modelo),
                                   uso={"tokens_entrada": u.get("prompt_tokens", 0),
                                        "tokens_salida": u.get("completion_tokens", 0),
                                        "tokens_total": u.get("total_tokens", 0)})
        raise self._error(ultimo, self.nombre)

    def listar_modelos(self) -> list[str]:
        cab = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with self._cliente() as c:
            r = c.get(f"{self.base_url}/models", headers=cab)
        if r.status_code != 200:
            raise self._error(r, self.nombre)
        return sorted(m.get("id", "") for m in r.json().get("data", []))


class Ollama(OpenAICompatible):
    """Modelos locales mediante Ollama (endpoint compatible con OpenAI)."""
    nombre = "ollama"
    requiere_clave = False
