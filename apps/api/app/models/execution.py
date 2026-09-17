from typing import Literal

from pydantic import BaseModel, Field


class ExecutionRequest(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=20_000)
    observation_code: str | None = Field(default=None, max_length=10_000)


class CheckResult(BaseModel):
    name: str
    passed: bool
    message: str


class ExecutionResult(BaseModel):
    status: Literal["passed", "failed", "timeout", "error", "unavailable"]
    checks: list[CheckResult] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_ms: int
    runner: Literal["local-container", "cloudflare-sandbox"]
