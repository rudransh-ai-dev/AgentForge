"""
Lightweight local retrieval for V5.

This is deliberately dependency-free so the upgrade works on the current
project without requiring Chroma or an embedding model to be installed first.
It can be swapped for vector search later behind the same public functions.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from core.memory import get_run_history


ROOT_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT_DIR / "docs"
WORKSPACE_DIR = ROOT_DIR / "workspace"

MAX_FILE_BYTES = 80_000
TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
    ".json", ".yml", ".yaml", ".toml",
}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "dist", ".mypy_cache"}


@dataclass
class RetrievalHit:
    source: str
    title: str
    snippet: str
    score: int


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_+#.-]{3,}", (text or "").lower())
        if token not in {"the", "and", "for", "with", "from", "this", "that", "into", "what", "how"}
    }


def _iter_text_files(root: Path):
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                yield path
            except OSError:
                continue


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _best_snippet(text: str, query_terms: set[str], max_chars: int = 700) -> str:
    if not text:
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return text[:max_chars].strip()
    ranked = sorted(
        paragraphs,
        key=lambda p: len(_tokens(p) & query_terms),
        reverse=True,
    )
    return ranked[0][:max_chars].strip()


def retrieve_context(query: str, limit: int = 5, include_workspace: bool = True) -> list[RetrievalHit]:
    query_terms = _tokens(query)
    if not query_terms:
        return []

    hits: list[RetrievalHit] = []

    for root, label in [(DOCS_DIR, "docs"), (WORKSPACE_DIR, "workspace")]:
        if label == "workspace" and not include_workspace:
            continue
        for path in _iter_text_files(root) or []:
            text = _read_text(path)
            score = len(_tokens(text[:5000]) & query_terms)
            if score <= 0:
                continue
            rel = path.relative_to(ROOT_DIR)
            hits.append(
                RetrievalHit(
                    source=str(rel),
                    title=f"{label}:{rel.name}",
                    snippet=_best_snippet(text, query_terms),
                    score=score,
                )
            )

    for run in get_run_history(limit=25):
        haystack = f"{run.get('prompt', '')}\n{run.get('route', '')}\n{run.get('project_id', '')}"
        score = len(_tokens(haystack) & query_terms)
        if score <= 0:
            continue
        hits.append(
            RetrievalHit(
                source=f"memory:runs:{run.get('run_id', '')}",
                title=f"past run via {run.get('route', 'unknown')}",
                snippet=(run.get("prompt") or "")[:700],
                score=score,
            )
        )

    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:limit]


def format_retrieval_block(hits: list[RetrievalHit], max_chars: int = 2200) -> str:
    if not hits:
        return ""
    parts = ["[Retrieved Local Context]"]
    used = len(parts[0])
    for hit in hits:
        item = f"\nSource: {hit.source}\n{hit.snippet}\n"
        if used + len(item) > max_chars:
            break
        parts.append(item)
        used += len(item)
    return "\n".join(parts).strip()
