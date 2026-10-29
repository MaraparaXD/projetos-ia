"""Only read repository metadata. Never run target code or network operations."""
from __future__ import annotations
import os
import re
import subprocess
from pathlib import Path
from typing import Any

_SHA40 = re.compile(r"[a-f0-9]{40}", re.IGNORECASE)


def _git(repo: Path, *args: str) -> str:
    # No shell, no hooks, no fsmonitor command. Optional locks disabled so status
    # does not rewrite the index merely to refresh cached information.
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'GIT_CONFIG_'))}
    env.update({'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0',
                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                'GIT_LFS_SKIP_SMUDGE': '1'})
    command = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
               '-c', f'core.hooksPath={os.devnull}', '-C', str(repo), *args]
    try:
        completed = subprocess.run(command, shell=False, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding='utf-8', errors='replace',
                                   timeout=20, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'Cannot inspect Git metadata ({type(exc).__name__})') from exc
    if completed.returncode:
        # Git stderr may contain user-controlled or confidential paths; do not echo it.
        raise ValueError(f'Git inspection failed: {args[0]} (exit {completed.returncode})')
    if len(completed.stdout) > 2_000_000:
        raise ValueError('Git output too large')
    return completed.stdout.strip()


def inspect_repo(path: Path) -> dict[str, Any]:
    """Return HEAD + dirty status only. Never fetch, checkout, execute hooks or write."""
    try:
        path = path.resolve(strict=True)
        if not path.is_dir():
            raise ValueError('Not a directory')
        top = Path(_git(path, 'rev-parse', '--show-toplevel')).resolve(strict=True)
        if top != path:
            raise ValueError('Provide the exact repository root')
        head = _git(path, 'rev-parse', '--verify', 'HEAD')
        if not _SHA40.fullmatch(head):
            raise ValueError('HEAD is not a SHA-1 Git object ID (unsupported repository hash)')
        # Number only. Never return filenames, which can be confidential.
        changes = _git(path, 'status', '--porcelain=v1', '--untracked-files=all')
        count = 0 if not changes else len(changes.splitlines())
        return {'head': head.lower(), 'clean': count == 0, 'changed_entries': count,
                'git_valid': True}
    except (OSError, ValueError) as exc:
        return {'head': None, 'clean': None, 'changed_entries': None,
                'git_valid': False, 'reason': str(exc)}


def compare_commit(expected: str, state: dict[str, Any]) -> dict[str, Any]:
    if not _SHA40.fullmatch(expected):
        return {'commit_verified': False, 'baseline_valid': False,
                'commit_reason': 'Expected commit must be a full 40-character SHA-1'}
    matched = bool(state.get('git_valid') and state.get('head') == expected.lower())
    clean = state.get('clean') is True
    return {'commit_verified': matched,
            'baseline_valid': matched and clean,
            'commit_reason': ('HEAD matches and worktree clean' if matched and clean
                              else 'HEAD matches but worktree is dirty' if matched
                              else 'HEAD mismatch or Git unavailable')}
