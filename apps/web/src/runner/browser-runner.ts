import { failureResult, supportsStackSwitching } from "./pyodide-core";
import type { RunnerRequest, RunnerResult } from "./pyodide-core";
import { reportRunnerProgress } from "./progress";

// Boot covers the first Pyodide + package download; execution is timed separately.
const BOOT_TIMEOUT_MS = 180_000;
const EXECUTION_TIMEOUT_MS = 20_000;

type WorkerMessage =
  | { type: "progress"; message: string }
  | { type: "ready" }
  | { type: "boot-error"; message: string }
  | { type: "result"; id: number; result: RunnerResult };

let worker: Worker | null = null;
let ready: Promise<Worker> | null = null;
let nextId = 1;

function resetWorker(): void {
  worker?.terminate();
  worker = null;
  ready = null;
}

function startWorker(): Promise<Worker> {
  const current = new Worker(new URL("./pyodide.worker.ts", import.meta.url), { type: "module" });
  worker = current;
  return new Promise<Worker>((resolve, reject) => {
    const fail = (message: string) => {
      window.clearTimeout(timer);
      if (worker === current) resetWorker();
      reject(new Error(message));
    };
    const timer = window.setTimeout(() => fail("載入逾時"), BOOT_TIMEOUT_MS);
    current.addEventListener("message", (event: MessageEvent<WorkerMessage>) => {
      const data = event.data;
      if (data.type === "progress") reportRunnerProgress(data.message);
      if (data.type === "ready") {
        window.clearTimeout(timer);
        resolve(current);
      }
      if (data.type === "boot-error") fail(data.message);
    });
    current.addEventListener("error", (event) => fail(event.message || "Worker 啟動失敗"));
    current.postMessage({ type: "init", baseUrl: new URL(import.meta.env.BASE_URL, window.location.href).href });
  });
}

export async function runInBrowser(request: RunnerRequest): Promise<RunnerResult> {
  const started = performance.now();
  if (!supportsStackSwitching()) {
    return failureResult(
      "unavailable",
      "這個瀏覽器不支援 WebAssembly JSPI，無法在瀏覽器內執行 Python。請改用最新版 Chrome 或 Edge。",
      0,
    );
  }

  let current: Worker;
  try {
    ready ??= startWorker();
    current = await ready;
  } catch (error) {
    return failureResult("unavailable", `Python 執行環境載入失敗：${(error as Error).message}`, performance.now() - started);
  }

  const id = nextId++;
  const executionStarted = performance.now();
  return new Promise<RunnerResult>((resolve) => {
    const onMessage = (event: MessageEvent<WorkerMessage>) => {
      if (event.data.type !== "result" || event.data.id !== id) return;
      window.clearTimeout(timer);
      current.removeEventListener("message", onMessage);
      resolve(event.data.result);
    };
    // A runaway loop blocks the worker, so the only way out is to terminate it and boot a new one next time.
    const timer = window.setTimeout(() => {
      current.removeEventListener("message", onMessage);
      if (worker === current) resetWorker();
      resolve(failureResult("timeout", "Execution exceeded the time limit.", performance.now() - executionStarted));
    }, EXECUTION_TIMEOUT_MS);
    current.addEventListener("message", onMessage);
    current.postMessage({ type: "run", id, request });
  });
}
