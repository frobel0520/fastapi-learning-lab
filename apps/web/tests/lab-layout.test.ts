import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

test("長程式碼在 editor 內捲動且不推走操作列", () => {
  assert.match(styles, /\.editor-wrap textarea \{[^}]*overflow: auto;/s);
  assert.match(styles, /\.editor-wrap textarea \{[^}]*resize: none;/s);
  assert.match(styles, /\.editor-wrap \{[^}]*height: clamp\(/s);
  assert.match(styles, /\.lab-toolbar \{[^}]*flex: 0 0 auto;/s);
});

test("程式碼捲動時行號維持同步", () => {
  assert.match(appSource, /lineNumbersRef/);
  assert.match(appSource, /lineNumbersRef\.current\.scrollTop = event\.currentTarget\.scrollTop/);
});

test("課程 tabs、output 與手機 coding flow 具有可操作語意", () => {
  assert.match(appSource, /aria-controls={`lesson-panel-\$\{tab\}`}/);
  assert.match(appSource, /role="tabpanel"/);
  assert.match(appSource, /aria-live="polite"/);
  assert.match(appSource, /className="mobile-course-picker"/);
  assert.match(appSource, /className="lab-back-button"/);
  assert.match(styles, /\.mobile-course-picker select \{[^}]*min-height: 44px;/s);
});

test("平板維持教材與 coding 兩欄，不讓第三欄覆蓋教材", () => {
  assert.match(styles, /\.lesson-main \{[^}]*overflow-x: hidden;[^}]*overflow-y: auto;/s);
  assert.match(styles, /@media \(max-width: 1180px\) \{[\s\S]*?\.course-nav \{ display: none; \}/);
  assert.match(styles, /@media \(max-width: 1180px\) \{[\s\S]*?\.lesson-main \{ margin-right: min\(430px, 52vw\); \}/);
  assert.match(styles, /@media \(max-width: 760px\) \{[\s\S]*?\.lesson-main \{[^}]*margin-right: 0;/);
});

test("RUN & OUTPUT 會在送出前與答案分離", () => {
  assert.match(appSource, /splitEditorSubmission\(workspace\.code, lesson\.execution\.invocation\)/);
  assert.match(appSource, /executeCode\(lesson\.id, submission\.code, submission\.observationCode\)/);
});
