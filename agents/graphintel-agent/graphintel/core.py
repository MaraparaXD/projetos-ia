"""GraphIntel: interpretação somente leitura de graph.json do Graphify.

Este código não executa Graphify, código de terceiros, scanners ou modelos.
"""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path

MAX_BYTES = 8_000_000
MAX_NODES = 10_000
MAX_EDGES = 35_000
DEPENDENCIES = frozenset({
    "calls", "imports", "imports_from", "depends_on", "inherits",
    "mixes_in", "uses", "references", "implements", "contains",
})


class GraphInputError(ValueError):
    pass


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 180:
        raise GraphInputError("Identificador de nó inválido.")
    if any(ord(c) < 32 for c in value):
        raise GraphInputError("Identificador de nó contém caracteres de controle.")
    return value


def _text(value: object, length: int = 180) -> str:
    if not isinstance(value, str) or len(value) > length:
        return ""
    return "".join(c for c in value if ord(c) >= 32)


def load_graph(path: Path) -> dict:
    """Suporta graph.json no formato node-link (nodes + links/edges).

    É intencionalmente restrito: sem leitura de código, scripts, URLs ou imports.
    """
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise GraphInputError("Grafo ausente ou maior que 8 MB.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise GraphInputError("JSON de grafo inválido.") from exc
    if not isinstance(raw, dict):
        raise GraphInputError("Estrutura de grafo inválida.")
    nodes_raw = raw.get("nodes")
    links_raw = raw.get("links", raw.get("edges"))
    if (not isinstance(nodes_raw, list) or not isinstance(links_raw, list)
            or len(nodes_raw) > MAX_NODES or len(links_raw) > MAX_EDGES):
        raise GraphInputError("Quantidade de nós ou ligações excedida.")
    nodes = {}
    for node in nodes_raw:
        if not isinstance(node, dict):
            raise GraphInputError("Nó inválido.")
        node_id = _identifier(node.get("id"))
        if node_id in nodes:
            raise GraphInputError("Nó duplicado.")
        nodes[node_id] = {
            "id": node_id,
            "label": _text(node.get("label", node_id)),
            "file_type": _text(node.get("file_type", "unknown"), 60),
            "source_file": _text(node.get("source_file", ""), 260),
        }
    edges = []
    for link in links_raw:
        if not isinstance(link, dict):
            raise GraphInputError("Ligação inválida.")
        source = _identifier(link.get("_src", link.get("source")))
        target = _identifier(link.get("_tgt", link.get("target")))
        if source not in nodes or target not in nodes:
            raise GraphInputError("Ligação cita nó inexistente.")
        relation = _text(link.get("relation", "unknown"), 80).lower()
        confidence = _text(link.get("confidence", "UNKNOWN"), 30).upper()
        if confidence not in {"EXTRACTED", "INFERRED", "AMBIGUOUS", "UNKNOWN"}:
            confidence = "UNKNOWN"
        edges.append({"source": source, "target": target,
                      "relation": relation, "confidence": confidence})
    return {"nodes": nodes, "edges": edges,
            "schema_version": _text(str(raw.get("graph", {}).get("schema_version", "unknown"))
                                    if isinstance(raw.get("graph", {}), dict) else "unknown", 40)}


def analyze(graph: dict, focus: str | None = None, depth: int = 3) -> dict:
    """Impacto reverso: mudar B pode afetar A quando A chama/importa B."""
    if type(depth) is not int or not 1 <= depth <= 8:
        raise ValueError("Profundidade deve estar entre 1 e 8.")
    nodes, edges = graph["nodes"], graph["edges"]
    if focus is not None and focus not in nodes:
        raise GraphInputError("Nó focal não está no grafo.")
    inbound = {key: set() for key in nodes}
    degrees = {key: 0 for key in nodes}
    confidence_by_arc = {}
    for edge in edges:
        source, target = edge["source"], edge["target"]
        degrees[source] += 1
        degrees[target] += 1
        if edge["relation"] in DEPENDENCIES:
            inbound[target].add(source)
            confidence_by_arc[(target, source)] = edge["confidence"]
    ranked = sorted(nodes, key=lambda key: (-degrees[key], key))[:10]
    hotspots = [
        {"id": key, "label": nodes[key]["label"], "connections": degrees[key],
         "source_file": nodes[key]["source_file"]}
        for key in ranked
    ]
    affected = []
    if focus is not None:
        seen = {focus}
        queue = deque([(focus, 0)])
        while queue and len(affected) < 200:
            current, distance = queue.popleft()
            if distance >= depth:
                continue
            for parent in sorted(inbound[current]):
                if parent in seen:
                    continue
                seen.add(parent)
                affected.append({
                    "id": parent, "label": nodes[parent]["label"],
                    "source_file": nodes[parent]["source_file"],
                    "distance": distance + 1, "through": current,
                    "confidence": confidence_by_arc[(current, parent)],
                })
                queue.append((parent, distance + 1))
    return {
        "schema": "graphintel.analysis.v1",
        "status": "candidate", "origin": "graph_rules",
        "model_used": False,
        "node_count": len(nodes), "edge_count": len(edges),
        "focus": focus, "impact_candidates": affected,
        "hotspots": hotspots,
        "limitations": [
            "Relações do grafo não comprovam impacto de execução.",
            "Ligações INFERRED/AMBIGUOUS requerem confirmação humana.",
            "Não houve execução de código nem testes de segurança.",
        ],
    }


def model_metadata(report: dict) -> dict:
    """Apenas contagens e aliases: nunca nomes, caminhos, código ou IDs reais."""
    return {
        "schema": "graphintel.model.v1",
        "nodes": report["node_count"], "edges": report["edge_count"],
        "focus_selected": report["focus"] is not None,
        "impact": [
            {"alias": f"impact-{i+1}", "distance": item["distance"],
             "confidence": item["confidence"]}
            for i, item in enumerate(report["impact_candidates"][:30])
        ],
        "hotspots": [
            {"alias": f"hotspot-{i+1}", "connections": item["connections"]}
            for i, item in enumerate(report["hotspots"][:10])
        ],
    }


def review_with_model(report: dict, provider) -> dict:
    """Parecer opcional não reclassifica nós nem afirma risco comprovado."""
    result = dict(report)
    try:
        reply = provider.generate(
            "Você revisa um grafo sintético de dependências. Não invente nós, "
            "não alegue vulnerabilidades. Responda JSON com observations: lista "
            "de até 5 comentários gerais concisos, sem comandos.",
            model_metadata(report),
        )
        if not isinstance(reply, dict) or set(reply) != {"observations"}:
            raise ValueError("Contrato de parecer inválido.")
        values = reply["observations"]
        if (not isinstance(values, list) or len(values) > 5
                or any(not isinstance(v, str) or not 1 <= len(v) <= 240
                       or any(ord(c) < 32 for c in v) for v in values)):
            raise ValueError("Comentários fora do limite.")
        result["model_used"] = True
        result["mode"] = "local_llm_assisted"
        result["model_observations"] = values
    except (ValueError, OSError, KeyError, TypeError, TimeoutError):
        result["mode"] = "deterministic_fallback"
        result["model_observations"] = []
    return result
