import os
from functools import lru_cache

from app.runners.base import Runner
from app.runners.local_container import LocalContainerRunner


@lru_cache(maxsize=1)
def get_runner() -> Runner:
    provider = os.getenv("FASTAPI_LAB_RUNNER", "local-container")
    if provider != "local-container":
        raise RuntimeError(f"Unsupported runner provider: {provider}")
    return LocalContainerRunner()

