import type { Course } from "./types";
import { resolveApiBaseUrl } from "./api-config";
import { resolveSiteMode } from "./site-mode";

export const siteMode = resolveSiteMode(import.meta.env.VITE_STATIC_SITE);

export const apiBaseUrl = resolveApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
  import.meta.env.PROD,
  window.location.origin,
);

export async function fetchCourse(signal?: AbortSignal): Promise<Course> {
  const url = siteMode === "static"
    ? `${import.meta.env.BASE_URL}generated/course.json`
    : `${apiBaseUrl}/api/v1/courses/fastapi-complete-guide`;
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`Course content returned HTTP ${response.status}`);
  return response.json() as Promise<Course>;
}

export type ExecutionResult = {
  status: "passed" | "failed" | "timeout" | "error" | "unavailable";
  checks: { name: string; passed: boolean; message: string }[];
  stdout: string;
  stderr: string;
  duration_ms: number;
  runner: "local-container" | "cloudflare-sandbox" | "browser-pyodide";
};

export async function executeCode(lessonId: string, code: string, observationCode: string): Promise<ExecutionResult> {
  if (siteMode === "static") {
    // Loaded on first run so reading lessons never pays for the runner bundle.
    const { runInBrowser } = await import("./runner/browser-runner");
    return runInBrowser({ lesson_id: lessonId, code, observation_code: observationCode });
  }
  const response = await fetch(`${apiBaseUrl}/api/v1/executions`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lesson_id: lessonId, code, observation_code: observationCode }),
  });
  if (!response.ok) throw new Error(`Execution API returned HTTP ${response.status}`);
  return response.json() as Promise<ExecutionResult>;
}
