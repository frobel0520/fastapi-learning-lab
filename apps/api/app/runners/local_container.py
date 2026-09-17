import asyncio
import json
import os
import shutil
import time
import uuid

from app.models.execution import ExecutionRequest, ExecutionResult


class OutputLimitExceeded(Exception):
    pass


RESULT_MARKER = b"\n__FASTAPI_LAB_RESULT__="
LESSON_TIMEOUT_OVERRIDES = {
    "request-examples": 10.0,
    "dataclass-models": 10.0,
    "pydantic-v2-migration": 10.0,
}


class LocalContainerRunner:
    """Execute learner code in a short-lived, network-isolated Podman container."""

    def __init__(
        self,
        *,
        engine: str | None = None,
        image: str | None = None,
        timeout_seconds: float = 6.0,
    ) -> None:
        self.engine = engine or os.getenv("FASTAPI_LAB_CONTAINER_ENGINE", "podman")
        self.image = image or os.getenv("FASTAPI_LAB_RUNNER_IMAGE", "localhost/fastapi-learning-lab-runner:dev")
        self.timeout_seconds = timeout_seconds
        self._slots = asyncio.Semaphore(2)

    def command(self, container_name: str) -> list[str]:
        return [
            self.engine,
            "run",
            "--rm",
            "--interactive",
            "--pull",
            "never",
            "--name",
            container_name,
            "--network",
            "none",
            "--memory",
            "192m",
            "--cpus",
            "0.5",
            "--pids-limit",
            "64",
            "--ulimit",
            "nofile=64:64",
            "--ulimit",
            "fsize=1048576:1048576",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=32m",
            "--cap-drop",
            "all",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "65532:65532",
            "--workdir",
            "/tmp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            self.image,
        ]

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        started = time.monotonic()
        try:
            await asyncio.wait_for(self._slots.acquire(), timeout=1.0)
        except TimeoutError:
            return self._result("unavailable", started, stderr="Runner is busy. Please retry.")
        try:
            return await self._run_once(request)
        finally:
            self._slots.release()

    async def _run_once(self, request: ExecutionRequest) -> ExecutionResult:
        started = time.monotonic()
        if shutil.which(self.engine) is None:
            return self._result("unavailable", started, stderr=f"Container engine '{self.engine}' was not found.")

        name = f"fastapi-lab-{uuid.uuid4().hex[:12]}"
        payload = json.dumps(request.model_dump(), ensure_ascii=False).encode("utf-8")
        try:
            process = await asyncio.create_subprocess_exec(
                *self.command(name),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as error:
            return self._result("unavailable", started, stderr=str(error))

        tasks: list[asyncio.Task[object]] = []
        try:
            assert process.stdin is not None
            process.stdin.write(payload)
            await process.stdin.drain()
            process.stdin.close()
            stdout_task = asyncio.create_task(self._read_limited(process.stdout, 64_000))
            stderr_task = asyncio.create_task(self._read_limited(process.stderr, 64_000))
            wait_task = asyncio.create_task(process.wait())
            tasks = [stdout_task, stderr_task, wait_task]
            stdout, stderr, _ = await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task, wait_task),
                timeout=max(self.timeout_seconds, LESSON_TIMEOUT_OVERRIDES.get(request.lesson_id, 0.0)),
            )
        except TimeoutError:
            await self._cleanup_process(process, name, tasks)
            return self._result("timeout", started, stderr="Execution exceeded the time limit.")
        except OutputLimitExceeded:
            await self._cleanup_process(process, name, tasks)
            return self._result("error", started, stderr="Execution output exceeded 64 KB.")
        except asyncio.CancelledError:
            await asyncio.shield(self._cleanup_process(process, name, tasks))
            raise

        stdout_text = stdout.decode("utf-8", errors="replace")[-12_000:]
        stderr_text = stderr.decode("utf-8", errors="replace")[-12_000:]
        if process.returncode != 0:
            status = "unavailable" if "image not known" in stderr_text.lower() else "error"
            return self._result(status, started, stdout=stdout_text, stderr=stderr_text)

        try:
            learner_output, marker, result_payload = stdout.rpartition(RESULT_MARKER)
            if marker:
                data = json.loads(result_payload.strip())
                captured_stdout = learner_output.decode("utf-8", errors="replace")[-12_000:]
            else:
                # Backward-compatible parsing for a runner image built before
                # framed stdout was introduced.
                data = json.loads(stdout_text.strip().splitlines()[-1])
                captured_stdout = ""
            result = ExecutionResult.model_validate(data)
            result.stdout = captured_stdout
            result.duration_ms = round((time.monotonic() - started) * 1000)
            return result
        except (IndexError, json.JSONDecodeError, ValueError) as error:
            return self._result("error", started, stdout=stdout_text, stderr=f"Invalid runner response: {error}\n{stderr_text}")

    async def _cleanup_process(
        self,
        process: asyncio.subprocess.Process,
        name: str,
        tasks: list[asyncio.Task[object]],
    ) -> None:
        for task in tasks:
            if not task.done():
                task.cancel()
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        try:
            await process.wait()
        except ProcessLookupError:
            pass
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self._remove_container(name)

    async def _remove_container(self, name: str) -> None:
        try:
            cleanup = await asyncio.create_subprocess_exec(
                self.engine,
                "rm",
                "--force",
                name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(cleanup.wait(), timeout=2)
        except (OSError, TimeoutError):
            return

    @staticmethod
    async def _read_limited(
        stream: asyncio.StreamReader | None,
        limit: int,
    ) -> bytes:
        if stream is None:
            return b""
        chunks: list[bytes] = []
        size = 0
        while chunk := await stream.read(4096):
            size += len(chunk)
            if size > limit:
                raise OutputLimitExceeded
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _result(
        status: str,
        started: float,
        *,
        stdout: str = "",
        stderr: str = "",
    ) -> ExecutionResult:
        return ExecutionResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            duration_ms=round((time.monotonic() - started) * 1000),
            runner="local-container",
        )
