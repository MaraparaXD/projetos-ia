"""Ollama apenas em 127.0.0.1, sem proxy, redirecionamento ou execução."""
from __future__ import annotations

import json
import re
from urllib import request


class LocalModelError(ValueError):
    pass


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LocalModelError("Redirecionamento proibido.")


class OllamaLocal:
    def __init__(self, model: str, ack: bool):
        if not ack:
            raise LocalModelError("É necessário confirmar o uso do Ollama local.")
        if (not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,100}", model)
                or "cloud" in model.lower() or "://" in model):
            raise LocalModelError("Identificador de modelo local inválido.")
        self.model = model
        self.opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())

    def _post(self, route: str, payload: dict) -> dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(data) > 24_000:
            raise LocalModelError("Payload maior que o limite.")
        req = request.Request("http://127.0.0.1:11434/api/" + route,
                              data=data, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=15) as response:
                raw = response.read(24_001)
                if response.status != 200 or len(raw) > 24_000:
                    raise LocalModelError("Resposta local excede o limite.")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise LocalModelError("Resposta local inválida.")
            return result
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise LocalModelError("Ollama indisponível ou resposta inválida.") from exc

    def generate(self, system: str, metadata: dict) -> dict:
        show = self._post("show", {"model": self.model})
        details = show.get("details")
        info = show.get("model_info")
        if (show.get("remote_host") or show.get("remote_model")
                or not isinstance(details, dict) or details.get("format") != "gguf"
                or not isinstance(info, dict) or not info.get("general.architecture")):
            raise LocalModelError("Modelo GGUF exclusivamente local não verificado.")
        reply = self._post("generate", {
            "model": self.model, "stream": False, "format": "json",
            "system": system, "prompt": "DADOS_NAO_CONFIAVEIS:\n" +
            json.dumps(metadata, ensure_ascii=False),
            "options": {"temperature": 0.2, "num_predict": 512},
        })
        try:
            return json.loads(reply["response"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LocalModelError("JSON consultivo inválido.") from exc
