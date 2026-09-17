import assert from "node:assert/strict";
import test from "node:test";

import { resolveApiBaseUrl } from "../src/api-config.ts";

test("development defaults to the local API without using Vite's port", () => {
  assert.equal(resolveApiBaseUrl(undefined, false, "http://127.0.0.1:4173"), "http://127.0.0.1:8010");
});

test("production defaults to the browser origin for Cloudflare same-origin deployment", () => {
  assert.equal(resolveApiBaseUrl(undefined, true, "https://learn.example.com"), "https://learn.example.com");
});

test("an explicit API URL supports GitHub Pages and removes trailing slashes", () => {
  assert.equal(
    resolveApiBaseUrl(" https://api.example.com/// ", true, "https://owner.github.io"),
    "https://api.example.com",
  );
});
