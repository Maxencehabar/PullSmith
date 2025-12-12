import re
from pathlib import Path
from typing import Iterable


def allowed_path(path: Path, roots: Iterable[Path]) -> bool:
    return any(path.resolve().is_relative_to(root.resolve()) for root in roots)


def sanitize_branch_name(raw: str) -> str:
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", cleaned)
    cleaned = cleaned.strip("-._")
    return cleaned or "main"


def is_valid_branch_name(name: str) -> bool:
    return bool(re.match(r"^(feat|fix)/[a-z0-9._-]+$", name))


def normalize_branch_name(name: str) -> str:
    """Ensure branch starts with feat/ or fix/, sanitize the rest."""
    prefix = "feat/"
    body = name
    if name.startswith("fix/"):
        prefix = "fix/"
        body = name[len("fix/") :]
    elif name.startswith("feat/"):
        body = name[len("feat/") :]
    body = sanitize_branch_name(body)
    normalized = f"{prefix}{body}"
    if not is_valid_branch_name(normalized):
        normalized = f"{prefix}{sanitize_branch_name(body)}"
    return normalized
