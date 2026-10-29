"""Conservative AI-component inventory from package manifests only.

Dependency names are indicators, not proof a model/agent is deployed.
Do not read .env, application source files or package-lock secrets.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

AI_PACKAGES = {
  'openai': 'LLM provider SDK', 'anthropic': 'LLM provider SDK', 'langchain': 'LLM orchestration',
  '@langchain/core': 'LLM orchestration', '@langchain/openai': 'LLM orchestration',
  'llama-index': 'RAG', 'llamaindex': 'RAG', 'transformers': 'ML model execution',
  'torch': 'ML model execution', 'tensorflow': 'ML model execution',
  'ollama': 'Local LLM integration', 'crewai': 'Agent orchestration',
  'autogen': 'Agent orchestration', 'sentence-transformers': 'Embeddings',
  'chromadb': 'Vector store', 'faiss-cpu': 'Vector store', 'pinecone': 'Vector store',
  'qdrant-client': 'Vector store', 'openai-agents': 'Agent orchestration',
}


def scan_manifests(repo: Path) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    if not repo.is_dir():
        raise ValueError('Repository is not a folder')
    indicators: list[dict[str, str]] = []
    looked: list[str] = []
    # Root-level manifests only: no recursive discovery or source inspection.
    for name in ('package.json', 'requirements.txt', 'pyproject.toml'):
        p = (repo / name)
        if not p.is_file() or p.is_symlink() or p.stat().st_size > 1_000_000:
            continue
        looked.append(name)
        raw = p.read_text(encoding='utf-8', errors='replace')
        names: set[str] = set()
        if name == 'package.json':
            try:
                d = json.loads(raw)
                for field in ('dependencies', 'devDependencies', 'optionalDependencies'):
                    v = d.get(field, {}) if isinstance(d, dict) else {}
                    if isinstance(v, dict):
                        names.update(str(k).lower() for k in v)
            except json.JSONDecodeError:
                continue
        elif name == 'requirements.txt':
            for line in raw.splitlines():
                value = line.strip()
                if value and not value.startswith(('#', '-', '.')):
                    m = re.match(r'^([A-Za-z][A-Za-z0-9_.-]*)\s*(?:[=<>!~\[; ]|$)', value)
                    if m:
                        names.add(m[1].lower().replace('_', '-'))
        elif name == 'pyproject.toml':
            # Parse metadata only when Python stdlib tomllib is present.
            try:
                import tomllib
                cfg = tomllib.loads(raw)
                deps = cfg.get('project', {}).get('dependencies', [])
                if isinstance(deps, list):
                    for d in deps:
                        m = re.match(r'^([A-Za-z][A-Za-z0-9_.-]*)', str(d))
                        if m:
                            names.add(m[1].lower().replace('_', '-'))
                poetry = cfg.get('tool', {}).get('poetry', {}).get('dependencies', {})
                if isinstance(poetry, dict):
                    names.update(str(k).lower() for k in poetry)
            except (ImportError, ValueError, AttributeError):
                pass
        for name_hit in sorted(names & AI_PACKAGES.keys()):
            indicators.append({'manifest': name, 'dependency': name_hit,
                               'area': AI_PACKAGES[name_hit]})
    return {'manifests_checked': looked, 'indicators': indicators,
            'ai_component_confirmed': False,
            'applicability': 'requires human confirmation' if indicators else 'not established by manifest inspection',
            'note': 'Dependencies alone cannot prove actual AI use, deployment or security vulnerabilities.'}
