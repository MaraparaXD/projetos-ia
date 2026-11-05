"""Executa avaliações offline de especificações de tela explícitas."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import ScreenInputError, analyze, load_screen, review_with_model


def main(argv=None):
    parser = argparse.ArgumentParser(description="Design Agent — revisão estática de especificações UI")
    parser.add_argument("--input", type=Path, required=True,
                        help="JSON designagent.screen.v1 criado pelo usuário")
    parser.add_argument("--model", help="Modelo local GGUF em Ollama (opcional)")
    parser.add_argument("--ack-local-model", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = analyze(load_screen(args.input))
        if args.model:
            from .model import OllamaLocal
            result = review_with_model(result, OllamaLocal(args.model, args.ack_local_model))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, ScreenInputError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
