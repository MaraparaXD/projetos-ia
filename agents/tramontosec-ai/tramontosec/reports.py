"""Catalog older and newer audit reports, never merging or promoting finding IDs.

No full text, copied PDF, or external API calls are retained. PDF parser is optional.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any
from .core import open_db, record_document, require_workspace, now

IDS = re.compile(r'(?<![A-Za-z0-9_-])(?:VULN-\d{2,3}|A-\d{2}[a-z]?|CA-\d{2}|RMC09-[A-F]\d{2}|NF-\d{2})(?![A-Za-z0-9_-])')


def _text(path: Path) -> tuple[str, str]:
    if path.suffix.lower() in ('.md', '.txt'):
        if path.stat().st_size > 2_000_000:
            raise ValueError('Markdown report exceeds 2 MB')
        return path.read_text(encoding='utf-8', errors='replace'), 'markdown'
    if path.suffix.lower() == '.pdf':
        if path.stat().st_size > 20_000_000:
            raise ValueError('PDF report exceeds 20 MB')
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError('Optional pypdf dependency required to catalog PDF IDs') from exc
        pdf = PdfReader(str(path), strict=True)
        if len(pdf.pages) > 200 or pdf.is_encrypted:
            raise ValueError('Encrypted/oversized PDF not supported')
        texts = []
        for page in pdf.pages:
            result = page.extract_text() or ''
            texts.append(result[:120_000])
        return '\n'.join(texts)[:1_000_000], 'pdf'
    raise ValueError('Only Markdown, TXT and PDF reports are supported')


def catalog_report(root: Path, doc_id: str, path: Path, scope: str, period: str = '') -> dict[str, Any]:
    require_workspace(root)
    if scope not in ('external_assessment', 'whitebox_assessment'):
        raise ValueError('Scope must be external_assessment or whitebox_assessment')
    path = path.resolve(strict=True)
    text, fmt = _text(path)
    ids = sorted(set(IDS.findall(text)))
    # Register metadata only (path and SHA) in the preexisting documents table.
    result = record_document(root, doc_id, path, scope, period)
    with open_db(root) as db:
        previous = db.execute('SELECT scope,ids_json FROM report_catalog WHERE doc_id=?', (doc_id,)).fetchone()
        if previous and (previous['scope'] != scope or json.loads(previous['ids_json']) != ids):
            raise ValueError('Catalog ID already exists with differing metadata')
        db.execute('''INSERT OR IGNORE INTO report_catalog(doc_id,scope,format,ids_json,parsed_at,note)
                      VALUES(?,?,?,?,?,?)''',
                   (doc_id,scope,fmt,json.dumps(ids),now(),
                    'Heuristic ID discovery only; no automatic evidence or deduplication'))
    return {**result, 'scope': scope, 'format': fmt, 'historical_identifiers': ids,
            'count': len(ids), 'no_cross_report_merge': True}
