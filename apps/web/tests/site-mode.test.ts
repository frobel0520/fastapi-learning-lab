import assert from "node:assert/strict";
import test from "node:test";

import { SITE_COPY, resolveSiteMode } from "../src/site-mode.ts";

test("static mode is opt-in so local development keeps using the FastAPI API", () => {
  assert.equal(resolveSiteMode(undefined), "api");
  assert.equal(resolveSiteMode("false"), "api");
  assert.equal(resolveSiteMode(" TRUE "), "static");
});

test("static copy never tells learners to start the local API", () => {
  const copy = Object.values(SITE_COPY.static).join("\n");
  assert.doesNotMatch(copy, /8010|VITE_API_BASE_URL/);
  assert.match(SITE_COPY.static.runtimeLabel, /Pyodide/);
});
