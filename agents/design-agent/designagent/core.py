"""Design Agent: revisão de interface a partir de especificações explícitas.

Não abre URL, não renderiza browser, não modifica CSS e não alega teste visual.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

MAX_BYTES = 1_000_000
ROLES = frozenset({"text", "button", "link", "input", "image", "navigation", "card", "container", "modal", "heading"})
INTERACTIVE = frozenset({"button", "link", "input"})
TEXT_ROLES = frozenset({"text", "heading", "button", "link", "input"})


class ScreenInputError(ValueError):
    pass


def _hex(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ScreenInputError("Cor deve estar no formato #RRGGBB.")
    return value


def _luminance(hex_color: str) -> float:
    values = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    converted = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return 0.2126 * converted[0] + 0.7152 * converted[1] + 0.0722 * converted[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Contraste relativo WCAG para cores opacas, sem alpha/transparência."""
    a, b = _luminance(_hex(foreground)), _luminance(_hex(background))
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _integer(value, minimum=0, maximum=10_000) -> bool:
    return type(value) is int and minimum <= value <= maximum


def load_screen(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ScreenInputError("Entrada ausente ou acima de 1 MB.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ScreenInputError("JSON inválido.") from exc
    if not isinstance(raw, dict) or set(raw) != {"schema", "screen"}:
        raise ScreenInputError("Formato exige schema e screen.")
    if raw["schema"] != "designagent.screen.v1" or not isinstance(raw["screen"], dict):
        raise ScreenInputError("Versão de especificação desconhecida.")
    screen = raw["screen"]
    if set(screen) != {"name", "platform", "viewport", "components"}:
        raise ScreenInputError("A tela exige nome, plataforma, viewport e componentes.")
    if (not isinstance(screen["name"], str) or
            not 1 <= len(screen["name"]) <= 100 or
            any(ord(c) < 32 for c in screen["name"]) or
            screen["platform"] not in {"web", "mobile"} or
            not isinstance(screen["viewport"], dict) or
            set(screen["viewport"]) != {"width", "height"} or
            not all(_integer(screen["viewport"].get(key), 200, 5000) for key in ("width", "height"))):
        raise ScreenInputError("Dados básicos da tela inválidos.")
    components = screen["components"]
    if not isinstance(components, list) or not 1 <= len(components) <= 200:
        raise ScreenInputError("A tela deve ter de 1 a 200 componentes.")
    seen, cleaned = set(), []
    optional = {"foreground", "background", "large_text", "width", "height",
                "accessible_name", "label", "alt", "responsive", "feedback"}
    for item in components:
        if not isinstance(item, dict) or not {"id", "role"} <= item.keys() or not set(item) <= optional | {"id", "role"}:
            raise ScreenInputError("Componente inválido ou campo não permitido.")
        name, role = item["id"], item["role"]
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name)
                or name in seen or role not in ROLES):
            raise ScreenInputError("ID duplicado ou papel desconhecido.")
        seen.add(name)
        for key in ("foreground", "background"):
            if key in item:
                _hex(item[key])
        for key in ("width", "height"):
            if key in item and not _integer(item[key], 0, 5000):
                raise ScreenInputError("Dimensão de componente inválida.")
        for key in ("large_text", "accessible_name", "label", "alt", "responsive", "feedback"):
            if key in item and type(item[key]) is not bool:
                raise ScreenInputError("Estado de controle deve ser booleano.")
        cleaned.append(dict(item))
    return {"schema": raw["schema"], "screen": {**screen, "components": cleaned}}


def _finding(component: dict, rule: str, severity: str, issue: str, advice: str, measurement=None):
    stable = hashlib.sha256(json.dumps([component["id"], rule]).encode()).hexdigest()[:20]
    return {
        "id": stable, "component_id": component["id"], "role": component["role"],
        "rule": rule, "severity": severity, "status": "candidate", "origin": "rule",
        "issue": issue, "recommendation": advice, "measurement": measurement,
        "validated_by_human": False,
    }


def analyze(screen_data: dict) -> dict:
    screen = screen_data["screen"]
    findings, unchecked = [], []
    mobile = screen["platform"] == "mobile" or screen["viewport"]["width"] <= 480
    for component in screen["components"]:
        role = component["role"]
        if role in TEXT_ROLES:
            if "foreground" in component and "background" in component:
                ratio = contrast_ratio(component["foreground"], component["background"])
                threshold = 3.0 if component.get("large_text") else 4.5
                if ratio < threshold:
                    findings.append(_finding(component, "text-contrast", "Alta",
                        "Contraste declarado abaixo do mínimo WCAG AA para texto.",
                        "Revisar as cores e medir novamente com as cores renderizadas reais.",
                        {"ratio": round(ratio, 2), "required": threshold}))
            else:
                unchecked.append({"component_id": component["id"], "check": "text-contrast",
                                  "reason": "Cores opacas não declaradas."})
        if mobile and role in INTERACTIVE:
            if "width" in component and "height" in component:
                if component["width"] < 44 or component["height"] < 44:
                    findings.append(_finding(component, "touch-target", "Média",
                        "Área de toque declarada abaixo da meta heurística de 44x44 px.",
                        "Aumentar a área acionável e confirmar em dispositivo real.",
                        {"width": component["width"], "height": component["height"]}))
            else:
                unchecked.append({"component_id": component["id"], "check": "touch-target",
                                  "reason": "Dimensões não declaradas."})
        if role in {"button", "link", "input", "navigation"} and component.get("accessible_name") is False:
            findings.append(_finding(component, "accessible-name", "Alta",
                "Componente interativo sem nome acessível declarado.",
                "Adicionar nome acessível sem redundâncias e testar navegação assistiva."))
        if role == "input" and component.get("label") is False:
            findings.append(_finding(component, "form-label", "Alta",
                "Campo sem rótulo declarado.",
                "Associar rótulo perceptível e identificador programático."))
        if role == "image" and component.get("alt") is False:
            findings.append(_finding(component, "image-alt", "Média",
                "Imagem sem alternativa declarada.",
                "Descrever imagem informativa ou indicar apresentação decorativa."))
        if component.get("responsive") is False:
            findings.append(_finding(component, "responsive", "Média",
                "Componente marcado como não responsivo na especificação.",
                "Revisar quebra de layout nas larguras relevantes."))
        if role == "button" and component.get("feedback") is False:
            findings.append(_finding(component, "interaction-feedback", "Baixa",
                "Botão não declara retorno visual/assistivo.",
                "Prever estados de foco, carregamento e resultado, quando aplicáveis."))
    return {
        "schema": "designagent.analysis.v1", "status": "candidate",
        "screen_name": screen["name"], "platform": screen["platform"],
        "viewport": screen["viewport"], "component_count": len(screen["components"]),
        "findings": findings, "unchecked": unchecked, "mode": "deterministic",
        "limitations": [
            "As verificações dependem dos valores declarados, não de uma interface renderizada.",
            "Não há validação automática de conformidade WCAG nem teste com usuários.",
            "Meta de toque 44x44 é recomendação de usabilidade, não alegação de WCAG.",
        ],
    }


def model_metadata(report: dict) -> dict:
    """Metadados sem textos da tela, IDs de componentes ou cores reais."""
    return {
        "schema": "designagent.model.v1",
        "platform": report["platform"],
        "viewport_band": "mobile" if report["viewport"]["width"] <= 480 else "wide",
        "component_count": report["component_count"],
        "findings": [
            {"finding_id": item["id"], "rule": item["rule"],
             "severity": item["severity"], "role": item["role"]}
            for item in report["findings"][:50]
        ],
        "unverified_checks": len(report["unchecked"]),
    }


def review_with_model(report: dict, provider) -> dict:
    updated = dict(report)
    try:
        response = provider.generate(
            "Você é especialista em design de produto. Critique com liberdade e proponha "
            "melhorias concretas sem inventar medições nem afirmar testes realizados. "
            "Responda JSON com suggestions: lista de objetos finding_id e recommendation.",
            model_metadata(report),
        )
        suggestions = response.get("suggestions") if isinstance(response, dict) else None
        known = {item["id"] for item in report["findings"]}
        if (not isinstance(response, dict) or set(response) != {"suggestions"} or
                not isinstance(suggestions, list) or len(suggestions) > 15):
            raise ValueError("Contrato LLM inválido.")
        cleaned = []
        for item in suggestions:
            if not isinstance(item, dict) or set(item) != {"finding_id", "recommendation"}:
                raise ValueError("Item LLM inválido.")
            finding = item["finding_id"]
            comment = item["recommendation"]
            if (not isinstance(finding, str) or finding not in known or
                    not isinstance(comment, str) or not 1 <= len(comment) <= 300 or
                    any(ord(c) < 32 for c in comment)):
                raise ValueError("Comentário ou referência LLM inválidos.")
            cleaned.append({"finding_id": finding, "recommendation": comment, "origin": "llm",
                            "status": "unverified"})
        updated["mode"] = "local_llm_assisted"
        updated["model_suggestions"] = cleaned
    except (ValueError, OSError, TypeError, KeyError, TimeoutError):
        updated["mode"] = "deterministic_fallback"
        updated["model_suggestions"] = []
    return updated
