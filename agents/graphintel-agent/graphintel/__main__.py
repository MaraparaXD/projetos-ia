"""CLI local GraphIntel; somente lê graph.json e imprime relatório."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import GraphInputError, analyze, load_graph, review_with_model


def main(argv=None):
    parser = argparse.ArgumentParser(description="GraphIntel — análise offline de relações de código")
    parser.add_argument("--graph", type=Path, required=True, help="Arquivo graph.json exportado pelo Graphify")
    parser.add_argument("--focus", help="ID exato de nó para análise de impacto reverso")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--model", help="Modelo GGUF local no Ollama (opcional)")
    parser.add_argument("--ack-local-model", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = analyze(load_graph(args.graph), args.focus, args.depth)
        if args.model:
            from .model import OllamaLocal
            report = review_with_model(report, OllamaLocal(args.model, args.ack_local_model))
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (GraphInputError, ValueError, PermissionError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
