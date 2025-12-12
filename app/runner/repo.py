import logging
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import mkdtemp
from typing import Optional

logger = logging.getLogger(__name__)


def clone_repo(url: str, branch: str, workdir: Optional[Path] = None) -> Path:
    token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
    if token and url.startswith("https://github.com/"):
        parts = url.split("https://github.com/", 1)[1]
        url = f"https://{token}@github.com/{parts}"
        logger.info("Using token-authenticated clone URL for GitHub")
    target_dir = Path(workdir or mkdtemp(prefix="codex-run-")) / "repo"
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    logger.info("Cloning %s (branch %s) into %s", url, branch, target_dir)
    subprocess.run(["git", "clone", "--branch", branch, url, str(target_dir)], check=True)
    return target_dir
