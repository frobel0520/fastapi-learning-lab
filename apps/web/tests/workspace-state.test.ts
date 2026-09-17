import assert from "node:assert/strict";
import test from "node:test";

import {
  IDLE_OUTPUT,
  WORKSPACE_STORAGE_KEY,
  defaultWorkspace,
  loadWorkspaceStore,
  saveWorkspaceStore,
  workspaceFor,
} from "../src/workspace-state.ts";

test("每堂課使用獨立 workspace，切換後可恢復原本程式碼", () => {
  const store = {
    first: { code: "print('first')", output: "first", runState: "done" as const },
    second: { code: "print('second')", output: "second", runState: "error" as const },
  };

  assert.equal(workspaceFor(store, "first", "starter").code, "print('first')");
  assert.equal(workspaceFor(store, "second", "starter").code, "print('second')");
  assert.deepEqual(workspaceFor(store, "new", "starter"), defaultWorkspace("starter"));
});

test("localStorage round trip 會保留 code、output 與完成狀態", () => {
  const memory = new Map<string, string>();
  const storage = {
    getItem: (key: string) => memory.get(key) ?? null,
    setItem: (key: string, value: string) => { memory.set(key, value); },
  };
  saveWorkspaceStore({ lesson: { code: "print('ok')", output: "ok", runState: "done" } }, storage);

  const restored = loadWorkspaceStore(storage);

  assert.equal(restored.lesson.code, "print('ok')");
  assert.equal(restored.lesson.output, "ok");
  assert.equal(restored.lesson.runState, "done");
  assert.ok(memory.has(WORKSPACE_STORAGE_KEY));
});

test("重新整理時不保留 running 假狀態，無資料時使用等待訊息", () => {
  const storage = {
    getItem: () => JSON.stringify({ lesson: { code: "pass", output: "running", runState: "running" } }),
  };

  assert.equal(loadWorkspaceStore(storage).lesson.runState, "idle");
  assert.equal(defaultWorkspace("pass").output, IDLE_OUTPUT);
});

test("已保存的 print 程式會保留在 Coding workspace", () => {
  const legacySolution = `import asyncio

async def fetch_user() -> dict[str, int]:
    await asyncio.sleep(0.1)
    return {"id": 7}

print(asyncio.run(fetch_user()))`;
  const customCode = `${legacySolution}\nprint("我的除錯資訊")`;
  const storage = {
    getItem: () => JSON.stringify({
      "async-await": { code: legacySolution, output: "done", runState: "done" },
      custom: { code: customCode, output: "done", runState: "done" },
    }),
  };

  const restored = loadWorkspaceStore(storage);

  assert.equal(restored["async-await"].code, legacySolution);
  assert.equal(restored.custom.code, customCode);
});
