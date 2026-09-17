import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { OutputCollector, RESULT_MARKER, RUNNER_PACKAGES, parseRunnerOutput } from "../src/runner/pyodide-core.ts";

test("runner result keeps learner stdout separate from the framed payload", () => {
  const payload = { status: "passed", checks: [{ name: "Print output", passed: true, message: "ok" }], stdout: "", stderr: "", duration_ms: 0, runner: "local-container" };
  const result = parseRunnerOutput(`Hello Leo\n${RESULT_MARKER}${JSON.stringify(payload)}\n`, "SAWarning: noisy", 12.4);
  assert.equal(result.status, "passed");
  assert.equal(result.stdout, "Hello Leo\n");
  assert.equal(result.stderr, "");
  assert.equal(result.duration_ms, 12);
  assert.equal(result.runner, "browser-pyodide");
});

test("the last result marker wins even when learner output imitates it", () => {
  const fake = `${RESULT_MARKER}{"status":"passed","checks":[]}`;
  const real = { status: "failed", checks: [], stderr: "" };
  const result = parseRunnerOutput(`${fake}\n${RESULT_MARKER}${JSON.stringify(real)}\n`, "", 1);
  assert.equal(result.status, "failed");
});

test("missing result marker is reported as a runner error", () => {
  const result = parseRunnerOutput("partial output", "Traceback", 1);
  assert.equal(result.status, "error");
  assert.match(result.stderr, /missing result marker/);
  assert.equal(result.stdout, "partial output");
});

test("output collector stops writes beyond the byte limit", () => {
  const collector = new OutputCollector(8);
  const encoder = new TextEncoder();
  assert.equal(collector.write(encoder.encode("中文")), 6);
  assert.throws(() => collector.write(encoder.encode("xyz")));
  assert.equal(collector.overflowed, true);
  assert.equal(collector.text(), "中文");
});

test("browser runner packages use the same pins as the runner image", () => {
  const dockerfile = readFileSync(new URL("../../runner/Dockerfile", import.meta.url), "utf8");
  const imagePins = [...dockerfile.matchAll(/^\s+"?([\w\-[\]]+==[\w.]+)"?/gm)].map((match) => match[1]).sort();
  const browserPins = RUNNER_PACKAGES.filter((item) => item.includes("==")).sort();
  assert.deepEqual(browserPins, imagePins);
});
