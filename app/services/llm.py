import json
import logging
from typing import Tuple

from openai import OpenAI

from app.core.config import get_settings
from app.domain.policies import sanitize_branch_name

logger = logging.getLogger(__name__)


def _fallback_branch_and_commit(instructions: str) -> Tuple[str, str]:
    slug = sanitize_branch_name(instructions or "codex-update")
    if not slug:
        slug = "codex-update"
    return f"feat/{slug[:40]}", "chore: apply codex changes"


def propose_branch_and_commit(codex_summary: str, instructions: str) -> Tuple[str, str]:
    """
    Ask an LLM to suggest a branch name and commit message based on the Codex output and instructions.
    Returns (branch_name, commit_message).
    """
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set; using fallback branch/commit")
        return _fallback_branch_and_commit(instructions)

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = (
        "You are a concise git assistant. Given the task instructions, propose a git branch name "
        "and commit message. Branch name requirements: start with 'feat/' or 'fix/' (choose based on intent), "
        "kebab-case, lowercase ASCII only (letters, numbers, hyphen), no quotes or punctuation, <=50 chars total. "
        "Commit message: concise, <=72 chars. "
        "Return JSON with keys branch and commit."
    )
    user = (
        f"Instructions:\n{instructions or '(none)'}"
    )
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {}
        branch = parsed.get("branch") or _fallback_branch_and_commit(instructions)[0]
        commit = parsed.get("commit") or _fallback_branch_and_commit(instructions)[1]
        from app.domain.policies import normalize_branch_name

        branch = normalize_branch_name(branch)[:50]
        return branch, commit
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM branch/commit suggestion failed: %s", exc)
        return _fallback_branch_and_commit(instructions)
