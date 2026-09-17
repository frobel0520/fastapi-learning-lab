import os
import shutil
import subprocess

import pytest

from app.models.execution import ExecutionRequest
from app.runners.local_container import LocalContainerRunner
from app.services.content import get_course
from app.services.submission import OUTPUT_OBSERVATION_MARKER, normalize_execution_request


RUN_INTEGRATION = os.getenv("FASTAPI_LAB_RUN_CONTAINER_TESTS") == "1"
ENGINE = os.getenv("FASTAPI_LAB_CONTAINER_ENGINE", "podman")
IMAGE = os.getenv("FASTAPI_LAB_RUNNER_IMAGE", "localhost/fastapi-learning-lab-runner:dev")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not RUN_INTEGRATION, reason="set FASTAPI_LAB_RUN_CONTAINER_TESTS=1"),
]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def runner() -> LocalContainerRunner:
    if shutil.which(ENGINE) is None:
        pytest.fail(f"container engine not found: {ENGINE}")
    return LocalContainerRunner(engine=ENGINE, image=IMAGE, timeout_seconds=6.0)


@pytest.mark.anyio
@pytest.mark.parametrize("lesson", get_course().lessons, ids=lambda lesson: lesson.id)
async def test_reference_solution_passes(runner: LocalContainerRunner, lesson: object) -> None:
    editor_code = (
        f"{lesson.code.solution.rstrip()}\n\n"
        f"{OUTPUT_OBSERVATION_MARKER}\n{lesson.execution.invocation.strip()}\n"
    )
    request = normalize_execution_request(ExecutionRequest(
        lesson_id=lesson.id,
        code=editor_code,
    ))
    assert request.code == f"{lesson.code.solution.rstrip()}\n"
    assert request.observation_code == lesson.execution.invocation.strip()
    result = await runner.run(request)
    details = "; ".join(f"{item.name}={item.passed}: {item.message}" for item in result.checks)
    assert result.status == "passed", f"{lesson.id}: {result.stderr} {details}"
    assert any(item.name == "Print output" and item.passed for item in result.checks)
    assert result.stdout.strip(), f"{lesson.id}: observation did not print output"


@pytest.mark.anyio
async def test_incorrect_solution_fails(runner: LocalContainerRunner) -> None:
    result = await runner.run(ExecutionRequest(
        lesson_id="python-type-hints",
        code="def greeting(name):\n    return {'message': 'wrong'}",
    ))
    assert result.status == "failed"
    assert any(not item.passed for item in result.checks)


@pytest.mark.anyio
async def test_print_output_is_returned(runner: LocalContainerRunner) -> None:
    lesson = next(item for item in get_course().lessons if item.id == "python-type-hints")
    result = await runner.run(ExecutionRequest(
        lesson_id=lesson.id,
        code=lesson.code.solution,
        observation_code=lesson.execution.invocation,
    ))

    assert result.status == "passed"
    assert result.stdout == "Hello Leo\n"
    assert "print(" not in lesson.code.solution


@pytest.mark.anyio
async def test_infinite_loop_times_out(runner: LocalContainerRunner) -> None:
    result = await runner.run(ExecutionRequest(
        lesson_id="python-type-hints",
        code="while True:\n    pass",
    ))
    assert result.status == "timeout"


@pytest.mark.anyio
async def test_output_flood_is_terminated(runner: LocalContainerRunner) -> None:
    result = await runner.run(ExecutionRequest(
        lesson_id="python-type-hints",
        code='while True:\n    print("x" * 1000)',
    ))
    assert result.status == "error"
    assert "64 KB" in result.stderr


@pytest.mark.anyio
async def test_container_security_boundary(runner: LocalContainerRunner) -> None:
    probe = '''
import os
import socket

try:
    socket.create_connection(("1.1.1.1", 80), timeout=0.5)
    network_blocked = False
except OSError:
    network_blocked = True

try:
    with open("/root-write-probe", "w", encoding="utf-8") as handle:
        handle.write("unexpected")
    root_read_only = False
except OSError:
    root_read_only = True

effective_uid = os.geteuid()
'''
    result = await runner.run(ExecutionRequest(lesson_id="security-boundary-probe", code=probe))
    assert result.status == "passed"
    assert len(result.checks) == 3


def test_no_runner_containers_are_left_behind() -> None:
    completed = subprocess.run(
        [ENGINE, "ps", "--filter", "name=fastapi-lab-", "--format", "{{.Names}}"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == ""
