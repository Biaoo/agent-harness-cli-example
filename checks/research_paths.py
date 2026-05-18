from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONTEXT_PATH = "research/context.json"


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def load_research_context(root: Path, context_path: str = DEFAULT_CONTEXT_PATH) -> dict[str, str]:
    path = resolve(root, context_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}

    context: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, str):
            context[key] = value.strip()

    topic_slug = context.get("topic_slug", "")
    if topic_slug and not context.get("research_dir"):
        context["research_dir"] = f"research/{topic_slug}"
    return context


def expand_research_path(value: str, context: dict[str, str]) -> str:
    expanded = value
    for key, replacement in context.items():
        expanded = expanded.replace("{" + key + "}", replacement)
        expanded = expanded.replace("{context." + key + "}", replacement)
    return expanded


def resolve_config_path(root: Path, raw_path: str, config: dict[str, Any]) -> tuple[str, Path, dict[str, str]]:
    context_path = str(config.get("context_path", DEFAULT_CONTEXT_PATH))
    context = load_research_context(root, context_path)
    expanded_path = expand_research_path(raw_path, context)
    return expanded_path, resolve(root, expanded_path), context
