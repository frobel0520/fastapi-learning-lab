import { PYODIDE_INDEX_URL, failureResult, prepareRuntime, runSubmission } from "./pyodide-core";
import type { PyodideRuntime, RunnerRequest } from "./pyodide-core";

type InitMessage = { type: "init"; baseUrl: string };
type RunMessage = { type: "run"; id: number; request: RunnerRequest };
type LoadPyodide = (options: { indexURL: string }) => Promise<PyodideRuntime>;

const scope = self as unknown as {
  postMessage(message: unknown): void;
  addEventListener(type: "message", listener: (event: MessageEvent<InitMessage | RunMessage>) => void): void;
};

let runtime: PyodideRuntime | null = null;

async function fetchText(url: URL): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url.pathname} returned HTTP ${response.status}`);
  return response.text();
}

async function boot(baseUrl: string): Promise<void> {
  scope.postMessage({ type: "progress", message: "第一次執行：正在下載 Python 執行環境（Pyodide），約需 10–30 秒…" });
  const { loadPyodide } = (await import(/* @vite-ignore */ `${PYODIDE_INDEX_URL}pyodide.mjs`)) as { loadPyodide: LoadPyodide };
  const pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });
  scope.postMessage({ type: "progress", message: "正在安裝 FastAPI、SQLModel 等課程套件…" });
  const [harness, shim] = await Promise.all([
    fetchText(new URL("generated/runner/harness.py", baseUrl)),
    fetchText(new URL("generated/runner/pyodide_shim.py", baseUrl)),
  ]);
  await prepareRuntime(pyodide, { harness, shim });
  runtime = pyodide;
}

scope.addEventListener("message", async (event) => {
  const data = event.data;
  if (data.type === "init") {
    try {
      await boot(data.baseUrl);
      scope.postMessage({ type: "ready" });
    } catch (error) {
      scope.postMessage({ type: "boot-error", message: error instanceof Error ? error.message : String(error) });
    }
    return;
  }
  scope.postMessage({ type: "progress", message: "正在瀏覽器內執行 hidden checks…" });
  const result = runtime
    ? await runSubmission(runtime, data.request)
    : failureResult("unavailable", "Python runtime is not ready.", 0);
  scope.postMessage({ type: "result", id: data.id, result });
});
