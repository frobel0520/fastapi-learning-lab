// Runs every lesson's reference solution through the Pyodide runner in Node.
// Requires `python scripts/export_static_content.py` first and Node with JSPI (--experimental-wasm-jspi).
import { readFileSync } from "node:fs";
import { loadPyodide } from "pyodide";

import { prepareRuntime, runSubmission, supportsStackSwitching } from "../src/runner/pyodide-core.ts";
import type { RunnerRequest, RunnerResult } from "../src/runner/pyodide-core.ts";

type ExportedLesson = { id: string; code: { solution: string }; execution: { invocation: string } };

const LESSON_TIMEOUT_MS = 60_000;
const generated = new URL("../public/generated/", import.meta.url);
const read = (path: string) => readFileSync(new URL(path, generated), "utf8");

if (!supportsStackSwitching()) {
  console.error("WebAssembly JSPI is unavailable; run Node with --experimental-wasm-jspi.");
  process.exit(1);
}

const course = JSON.parse(read("course.json")) as { lessons: ExportedLesson[] };
const bootStarted = performance.now();
const pyodide = await loadPyodide();
await prepareRuntime(pyodide, { harness: read("runner/harness.py"), shim: read("runner/pyodide_shim.py") });
console.log(`runtime ready in ${Math.round(performance.now() - bootStarted)}ms`);

function withTimeout(label: string, promise: Promise<RunnerResult>): Promise<RunnerResult> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} did not finish within ${LESSON_TIMEOUT_MS}ms`)), LESSON_TIMEOUT_MS);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

async function run(label: string, request: RunnerRequest): Promise<RunnerResult> {
  return withTimeout(label, runSubmission(pyodide, request));
}

const failures: string[] = [];
function expect(label: string, passed: boolean, detail: string) {
  console.log(`${passed ? "ok  " : "FAIL"} ${label}${passed ? "" : `  ${detail}`}`);
  if (!passed) failures.push(label);
}

for (const lesson of course.lessons) {
  const result = await run(lesson.id, {
    lesson_id: lesson.id,
    code: `${lesson.code.solution.trimEnd()}\n`,
    observation_code: lesson.execution.invocation.trim(),
  });
  const printed = result.checks.some((check) => check.name === "Print output" && check.passed) && result.stdout.trim() !== "";
  const failed = result.checks.filter((check) => !check.passed).map((check) => `${check.name}: ${check.message}`);
  expect(`${lesson.id} (${result.duration_ms}ms)`, result.status === "passed" && printed, [...failed, result.stderr].filter(Boolean).join(" | ").slice(0, 600));
}

const wrong = await run("incorrect solution", {
  lesson_id: "python-type-hints",
  code: "def greeting(name):\n    return {'message': 'wrong'}",
  observation_code: null,
});
expect("incorrect solution fails", wrong.status === "failed" && wrong.checks.some((check) => !check.passed), JSON.stringify(wrong).slice(0, 300));

const typeHints = course.lessons.find((lesson) => lesson.id === "python-type-hints")!;
const printed = await run("print output", {
  lesson_id: typeHints.id,
  code: typeHints.code.solution,
  observation_code: typeHints.execution.invocation,
});
expect("print output is returned", printed.status === "passed" && printed.stdout === "Hello Leo\n", JSON.stringify(printed).slice(0, 300));

const flood = await run("output flood", {
  lesson_id: "python-type-hints",
  code: 'while True:\n    print("x" * 1000)',
  observation_code: null,
});
expect("output flood is terminated", flood.status === "error" && flood.stderr.includes("64 KB"), JSON.stringify(flood).slice(0, 300));

const after = await run("runtime reusable after flood", {
  lesson_id: typeHints.id,
  code: typeHints.code.solution,
  observation_code: typeHints.execution.invocation,
});
expect("runtime is reusable after an output flood", after.status === "passed" && after.stdout === "Hello Leo\n", JSON.stringify(after).slice(0, 300));

console.log(`\n${failures.length === 0 ? "all passed" : `${failures.length} failed: ${failures.join(", ")}`}`);
process.exit(failures.length === 0 ? 0 : 1);
