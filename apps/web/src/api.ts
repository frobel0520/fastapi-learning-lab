import type { Course } from "./types";
import { resolveApiBaseUrl } from "./api-config";

export const apiBaseUrl = resolveApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
  import.meta.env.PROD,
  window.location.origin,
);

export async function fetchCourse(signal?: AbortSignal): Promise<Course> {
  const response = await fetch(`${apiBaseUrl}/api/v1/courses/fastapi-complete-guide`, { signal });
  if (!response.ok) throw new Error(`Course API returned HTTP ${response.status}`);
  return response.json() as Promise<Course>;
}

export type ExecutionResult = {
  status: "passed" | "failed" | "timeout" | "error" | "unavailable";
  checks: { name: string; passed: boolean; message: string }[];
  stdout: string;
  stderr: string;
  duration_ms: number;
  runner: "local-container" | "cloudflare-sandbox";
};

export async function executeCode(lessonId: string, code: string, observationCode: string) {
  const response = await fetch(`${apiBaseUrl}/api/v1/executions`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lesson_id: lessonId, code, observation_code: observationCode }),
  });
  if (!response.ok) throw new Error(`Execution API returned HTTP ${response.status}`);
  return response.json() as Promise<ExecutionResult>;
}
