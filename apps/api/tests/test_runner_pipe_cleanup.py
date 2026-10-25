import asyncio
import sys
import time

import pytest

from app.models.execution import ExecutionRequest
from app.runners.local_container import LocalContainerRunner


@pytest.mark.parametrize("descriptor", [1, 2], ids=["stdout", "stderr"])
def test_output_flood_cleanup_drains_pipes_and_releases_slot(descriptor: int) -> None:
    class PipeRunner(LocalContainerRunner):
        def __init__(self) -> None:
            super().__init__(engine=sys.executable, timeout_seconds=2)
            self.removed: list[str] = []

        def command(self, container_name: str) -> list[str]:
            # This controlled producer exercises real OS pipes without Docker
            # or executing learner code on the test host.
            producer = f"""import os, sys
sys.stdin.buffer.read()
while True:
    os.write({descriptor}, b'x' * 262144)
"""
            return [sys.executable, "-u", "-c", producer]

        async def _remove_container(self, name: str) -> None:
            self.removed.append(name)

    async def scenario() -> None:
        runner = PipeRunner()
        request = ExecutionRequest(lesson_id="pipe-cleanup-fixture", code="controlled fixture")
        # Reusing the runner three times also proves its two slots are released.
        for _ in range(3):
            started = time.monotonic()
            result = await asyncio.wait_for(runner.run(request), timeout=5)
            assert result.status == "error"
            assert "64 KB" in result.stderr
            assert time.monotonic() - started < 5
        assert len(runner.removed) == 3

    asyncio.run(scenario())
