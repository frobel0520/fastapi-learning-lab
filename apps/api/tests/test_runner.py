import asyncio

from fastapi.testclient import TestClient

from app.config import DEFAULT_ALLOWED_ORIGINS, allowed_origins
from app.main import app
from app.models.execution import CheckResult, ExecutionRequest, ExecutionResult
from app.runners.local_container import LESSON_TIMEOUT_OVERRIDES, LocalContainerRunner
from app.services.runner import get_runner
from app.services.submission import OUTPUT_OBSERVATION_MARKER


class PassingRunner:
    request: ExecutionRequest | None = None

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        self.request = request
        return ExecutionResult(
            status="passed",
            checks=[CheckResult(name="fixture", passed=True, message=request.lesson_id)],
            duration_ms=12,
            runner="local-container",
        )


def test_container_command_enforces_security_boundary() -> None:
    command = LocalContainerRunner().command("fastapi-lab-test")
    pairs = list(zip(command, command[1:]))
    assert ("--network", "none") in pairs
    assert ("--read-only", "--tmpfs") in pairs
    assert ("--cap-drop", "all") in pairs
    assert ("--security-opt", "no-new-privileges") in pairs
    assert ("--user", "65532:65532") in pairs
    assert ("--memory", "192m") in pairs
    assert ("--pids-limit", "64") in pairs
    assert ("--pull", "never") in pairs
    assert ("--ulimit", "nofile=64:64") in pairs
    assert LESSON_TIMEOUT_OVERRIDES == {}


def test_execution_route_depends_on_runner_contract() -> None:
    runner = PassingRunner()
    app.dependency_overrides[get_runner] = lambda: runner
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/executions",
            json={"lesson_id": "async-await", "code": "async def fetch_user(): pass"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "passed"
        assert response.json()["checks"][0]["message"] == "async-await"
        assert runner.request is not None
    finally:
        app.dependency_overrides.clear()


def test_execution_route_rejects_unknown_lesson() -> None:
    app.dependency_overrides[get_runner] = lambda: PassingRunner()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/executions",
            json={"lesson_id": "not-a-course", "code": "print('hello')"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_execution_route_splits_embedded_observation() -> None:
    runner = PassingRunner()
    app.dependency_overrides[get_runner] = lambda: runner
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/executions",
            json={
                "lesson_id": "python-type-hints",
                "code": f"answer = 42\n\n{OUTPUT_OBSERVATION_MARKER}\nprint(answer)",
            },
        )
        assert response.status_code == 200
        assert runner.request is not None
        assert runner.request.code == "answer = 42\n"
        assert runner.request.observation_code == "print(answer)"
    finally:
        app.dependency_overrides.clear()


def test_allowed_origins_supports_deployment_configuration() -> None:
    assert tuple(allowed_origins("")) == DEFAULT_ALLOWED_ORIGINS
    assert allowed_origins(" https://example.github.io/,https://api.example.com,https://example.github.io ") == [
        "https://example.github.io",
        "https://api.example.com",
    ]


def test_cancelled_execution_kills_and_removes_container(monkeypatch) -> None:
    class FakeStdin:
        def write(self, payload: bytes) -> None:
            assert payload

        async def drain(self) -> None:
            return None

        def close(self) -> None:
            return None

    class FakeProcess:
        def __init__(self) -> None:
            self.stdin = FakeStdin()
            self.stdout = asyncio.StreamReader()
            self.stderr = asyncio.StreamReader()
            self.returncode = None
            self.killed = False
            self.finished = asyncio.Event()

        async def wait(self) -> int:
            await self.finished.wait()
            return self.returncode or 0

        def kill(self) -> None:
            self.killed = True
            self.returncode = -9
            self.stdout.feed_eof()
            self.stderr.feed_eof()
            self.finished.set()

    async def scenario() -> None:
        process = FakeProcess()
        removed: list[str] = []
        runner = LocalContainerRunner(engine="fake-engine")

        async def create_process(*args, **kwargs):
            return process

        async def remove_container(name: str) -> None:
            removed.append(name)

        monkeypatch.setattr("app.runners.local_container.shutil.which", lambda _: "fake-engine")
        monkeypatch.setattr("app.runners.local_container.asyncio.create_subprocess_exec", create_process)
        monkeypatch.setattr(runner, "_remove_container", remove_container)

        task = asyncio.create_task(runner._run_once(ExecutionRequest(
            lesson_id="python-type-hints",
            code="print('hello')",
        )))
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("cancelled runner task did not propagate cancellation")

        assert process.killed
        assert len(removed) == 1
        assert removed[0].startswith("fastapi-lab-")

    asyncio.run(scenario())
