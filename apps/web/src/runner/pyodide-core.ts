// Environment-agnostic Pyodide runner: shared by the browser Web Worker and the Node CI check.
// It reuses apps/runner/harness.py unchanged, so hidden checks and the framed result
// protocol stay identical to the container runner.

export const PYODIDE_VERSION = "314.0.7";
export const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// Same pins as apps/runner/Dockerfile (a test keeps them in sync); anyio is required explicitly.
export const RUNNER_PACKAGES = [
  "anyio",
  "fastapi==0.141.1",
  "httpx==0.28.1",
  "python-multipart==0.0.22",
  "pyjwt==2.14.0",
  "pwdlib[argon2]==0.3.1",
  "sqlmodel==0.0.42",
  "pydantic-settings==2.15.0",
  "jinja2==3.1.6",
  "a2wsgi==1.10.10",
  "pytest==8.4.2",
  "strawberry-graphql==0.327.7",
  "uvicorn==0.52.4",
];

export const RESULT_MARKER = "\n__FASTAPI_LAB_RESULT__=";
export const OUTPUT_LIMIT_BYTES = 64_000;
const CAPTURED_TAIL_CHARS = 12_000;

export type RunnerRequest = {
  lesson_id: string;
  code: string;
  observation_code: string | null;
};

export type RunnerResult = {
  status: "passed" | "failed" | "timeout" | "error" | "unavailable";
  checks: { name: string; passed: boolean; message: string }[];
  stdout: string;
  stderr: string;
  duration_ms: number;
  runner: "browser-pyodide";
};

export type RunnerFiles = { harness: string; shim: string };

type WriteHandler = { write: (buffer: Uint8Array) => number };

export interface PyodideRuntime {
  loadPackage(names: string | string[]): Promise<unknown>;
  runPythonAsync(code: string): Promise<unknown>;
  setStdout(options: WriteHandler): void;
  setStderr(options: WriteHandler): void;
  FS: { mkdirTree(path: string): void; writeFile(path: string, data: string): void };
  globals: { set(name: string, value: unknown): void };
}

export function supportsStackSwitching(): boolean {
  return typeof (WebAssembly as { Suspending?: unknown }).Suspending === "function";
}

export class OutputCollector {
  overflowed = false;
  private bytes = 0;
  private readonly limit: number;
  private readonly chunks: string[] = [];
  private readonly decoder = new TextDecoder();

  constructor(limit: number = OUTPUT_LIMIT_BYTES) {
    this.limit = limit;
  }

  // Throwing makes Python's write raise OSError, which stops runaway output loops.
  write(buffer: Uint8Array): number {
    this.bytes += buffer.length;
    if (this.bytes > this.limit) {
      this.overflowed = true;
      throw new Error("output limit exceeded");
    }
    this.chunks.push(this.decoder.decode(buffer, { stream: true }));
    return buffer.length;
  }

  text(): string {
    return this.chunks.join("") + this.decoder.decode();
  }
}

export function failureResult(status: RunnerResult["status"], stderr: string, durationMs: number): RunnerResult {
  return { status, checks: [], stdout: "", stderr, duration_ms: Math.round(durationMs), runner: "browser-pyodide" };
}

export function parseRunnerOutput(stdout: string, stderr: string, durationMs: number): RunnerResult {
  const index = stdout.lastIndexOf(RESULT_MARKER);
  if (index === -1) {
    return { ...failureResult("error", `Invalid runner response: missing result marker\n${stderr}`.trim(), durationMs), stdout: stdout.slice(-CAPTURED_TAIL_CHARS) };
  }
  try {
    const payload = JSON.parse(stdout.slice(index + RESULT_MARKER.length).trim()) as Omit<RunnerResult, "runner">;
    return {
      status: payload.status,
      checks: payload.checks ?? [],
      stdout: stdout.slice(0, index).slice(-CAPTURED_TAIL_CHARS),
      // Like the container runner, interpreter warnings on stderr are not part of a completed result.
      stderr: (payload.stderr ?? "").slice(-CAPTURED_TAIL_CHARS),
      duration_ms: Math.round(durationMs),
      runner: "browser-pyodide",
    };
  } catch (error) {
    return failureResult("error", `Invalid runner response: ${String(error)}\n${stderr}`.trim(), durationMs);
  }
}

export async function prepareRuntime(pyodide: PyodideRuntime, files: RunnerFiles): Promise<void> {
  await pyodide.loadPackage("micropip");
  await pyodide.runPythonAsync(
    `import json, micropip\nawait micropip.install(json.loads(${JSON.stringify(JSON.stringify(RUNNER_PACKAGES))}))`,
  );
  pyodide.FS.mkdirTree("/opt/runner");
  pyodide.FS.writeFile("/opt/runner/harness.py", files.harness);
  pyodide.FS.writeFile("/opt/runner/pyodide_shim.py", files.shim);
  // Unbuffered streams: output rejected by the byte limit must not linger and leak into the next run.
  await pyodide.runPythonAsync(
    "import io, sys\n"
    + 'sys.stdout = io.TextIOWrapper(io.FileIO(1, "w", closefd=False), encoding="utf-8", errors="replace", write_through=True)\n'
    + 'sys.stderr = io.TextIOWrapper(io.FileIO(2, "w", closefd=False), encoding="utf-8", errors="replace", write_through=True)\n'
    + 'sys.path.insert(0, "/opt/runner")\n'
    + "import pyodide_shim\npyodide_shim.install()\nimport harness",
  );
}

export async function runSubmission(pyodide: PyodideRuntime, request: RunnerRequest): Promise<RunnerResult> {
  const started = performance.now();
  const stdout = new OutputCollector();
  const stderr = new OutputCollector();
  pyodide.setStdout({ write: (buffer) => stdout.write(buffer) });
  pyodide.setStderr({ write: (buffer) => stderr.write(buffer) });
  pyodide.globals.set("_runner_payload", JSON.stringify(request));
  try {
    await pyodide.runPythonAsync(
      "import io, sys, harness, pyodide_shim\n"
      + "pyodide_shim.reset_between_runs()\n"
      + "sys.stdin = io.StringIO(_runner_payload)\n"
      + "harness.main()\n"
      + "sys.stdout.flush()",
    );
  } catch (error) {
    const elapsed = performance.now() - started;
    if (stdout.overflowed || stderr.overflowed) {
      return failureResult("error", "Execution output exceeded 64 KB.", elapsed);
    }
    return failureResult("error", String(error).slice(-CAPTURED_TAIL_CHARS), elapsed);
  }
  return parseRunnerOutput(stdout.text(), stderr.text(), performance.now() - started);
}
