import assert from "node:assert/strict";
import test from "node:test";

import { HARBOR_EMBED_SRC, HARBOR_PROJECT_SLUG, harborEmbedTags } from "../src/harbor-embed.ts";

test("only the static GitHub Pages build loads the Harbor script", () => {
  assert.deepEqual(harborEmbedTags("development"), []);
  assert.deepEqual(harborEmbedTags("production"), []);
  assert.equal(harborEmbedTags("static").length, 1);
});

test("Harbor script is a blocking head script for this project's slug", () => {
  const [tag] = harborEmbedTags("static");
  assert.equal(tag.tag, "script");
  assert.equal(tag.injectTo, "head");
  assert.equal(tag.attrs.src, HARBOR_EMBED_SRC);
  assert.equal(tag.attrs["data-project"], HARBOR_PROJECT_SLUG);
  assert.equal("async" in tag.attrs, false);
  assert.equal("defer" in tag.attrs, false);
  assert.match(HARBOR_PROJECT_SLUG, /^[a-z0-9-]{2,40}$/);
});
