import logging
import os
import subprocess
import time
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CodexResult:
    stdout: str
    stderr: str
    returncode: int


def run_codex_plan(repo_path: Path, instructions: str) -> CodexResult:
    logger.info("Executing Codex agent")
    logger.info("Working directory: %s", repo_path)
    logger.info("Instructions:\n%s", instructions or "(none provided)")

    if not instructions:
        logger.warning("No instructions provided; skipping Codex execution")
        return CodexResult(stdout="", stderr="no instructions", returncode=0)

    cmd = [
        "codex",
        "exec",
        "-C",
        str(repo_path),
        "--sandbox",
        "workspace-write",
        instructions,
    ]

    logger.info("Running command: %s", " ".join(cmd))
    logger.info("Codex currently working ...")
    proc = subprocess.Popen(
        cmd,
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    spinner = cycle(["|", "/", "-", "\\"])
    while proc.poll() is None:
        logger.info("Codex still running %s", next(spinner))
        time.sleep(3)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        logger.error(
            "Codex command failed (exit %s). stdout:\n%s\nstderr:\n%s",
            proc.returncode,
            stdout,
            stderr,
        )
    if stdout:
        logger.info("Codex stdout:\n%s", stdout.strip())
    if stderr:
        logger.info("Codex stderr:\n%s", stderr.strip())
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=stderr)
    return CodexResult(stdout=stdout or "", stderr=stderr or "", returncode=proc.returncode)
