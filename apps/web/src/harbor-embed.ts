// Harbor (frobel0520/harbor) shows maintenance mode and announcement banners on the public demo.
// Only the static build is public; local and self-hosted API builds must not depend on Harbor.
export const HARBOR_EMBED_SRC = "https://harbor-1wk.pages.dev/embed/maintenance.js";
export const HARBOR_PROJECT_SLUG = "fastapi-learning-lab";

export interface HeadScriptTag {
  tag: "script";
  attrs: Record<string, string>;
  injectTo: "head";
}

// Harbor needs a classic blocking script in <head> (no async/defer) so it can hide the page before first paint.
// The script is fail-open: if Harbor is unreachable the page shows within 800 ms.
export function harborEmbedTags(mode: string): HeadScriptTag[] {
  if (mode !== "static") {
    return [];
  }
  return [
    {
      tag: "script",
      attrs: { src: HARBOR_EMBED_SRC, "data-project": HARBOR_PROJECT_SLUG },
      injectTo: "head",
    },
  ];
}
