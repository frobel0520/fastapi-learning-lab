import assert from "node:assert/strict";
import test from "node:test";
import {
  createSolutionEditorState,
  OUTPUT_OBSERVATION_MARKER,
  SOLUTION_READY_MESSAGE,
  solutionWithOutput,
  splitEditorSubmission,
} from "../src/editor-state.ts";

test("填入解答會加入輸出觀察程式並重設執行狀態", () => {
  const solution = 'from fastapi import FastAPI\n\napp = FastAPI()\n';
  const invocation = 'print(TestClient(app).get("/").json())';
  const code = solutionWithOutput(solution, invocation);

  assert.deepEqual(createSolutionEditorState(solution, invocation), {
    code,
    runState: "idle",
    output: SOLUTION_READY_MESSAGE,
  });
  assert.match(code, new RegExp(OUTPUT_OBSERVATION_MARKER.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  assert.deepEqual(splitEditorSubmission(code, invocation), {
    code: solution,
    observationCode: invocation,
  });
});

test("送出時會把使用者修改過的 output 程式從答案分離", () => {
  const code = `answer = 42\n\n${OUTPUT_OBSERVATION_MARKER}\nprint(answer + 1)\n`;
  assert.deepEqual(splitEditorSubmission(code, "print(answer)"), {
    code: "answer = 42\n",
    observationCode: "print(answer + 1)",
  });
});

test("沒有 output 標記時使用課程預設呼叫方式", () => {
  assert.deepEqual(splitEditorSubmission("answer = 42\n", " print(answer) \n"), {
    code: "answer = 42\n",
    observationCode: "print(answer)",
  });
});
