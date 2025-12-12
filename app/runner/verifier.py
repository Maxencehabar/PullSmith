import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_tests(repo_path: Path) -> None:
    logger.info("Skipping tests (no test command configured) for %s", repo_path)
