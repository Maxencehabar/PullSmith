from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


@contextmanager
def temp_sandbox(prefix: str = "codex-run-", base: Path | None = None):
    if base:
        base.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=prefix, dir=base) as tmpdir:
        yield Path(tmpdir)
