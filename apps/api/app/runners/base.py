from typing import Protocol

from app.models.execution import ExecutionRequest, ExecutionResult


class Runner(Protocol):
    async def run(self, request: ExecutionRequest) -> ExecutionResult: ...

