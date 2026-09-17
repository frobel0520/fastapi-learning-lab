export type RunState = "idle" | "running" | "done" | "error";

export type LessonWorkspace = {
  code: string;
  output: string;
  runState: RunState;
};

export type WorkspaceStore = Record<string, LessonWorkspace>;

export const WORKSPACE_STORAGE_KEY = "fastapi-learning-lab:workspaces:v1";
export const IDLE_OUTPUT = "等待執行。按「執行測試」會在隔離環境中跑 hidden checks。";
const MAX_PERSISTED_OUTPUT = 12_000;

export function defaultWorkspace(starter: string): LessonWorkspace {
  return { code: starter, output: IDLE_OUTPUT, runState: "idle" };
}

export function workspaceFor(store: WorkspaceStore, lessonId: string, starter: string): LessonWorkspace {
  return store[lessonId] ?? defaultWorkspace(starter);
}

export function loadWorkspaceStore(storage: Pick<Storage, "getItem"> = window.localStorage): WorkspaceStore {
  try {
    const raw = storage.getItem(WORKSPACE_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).flatMap(([lessonId, value]) => {
      if (!value || typeof value !== "object") return [];
      const candidate = value as Partial<LessonWorkspace>;
      if (typeof candidate.code !== "string" || typeof candidate.output !== "string") return [];
      const runState = candidate.runState === "done" || candidate.runState === "error" ? candidate.runState : "idle";
      return [[lessonId, {
        code: candidate.code,
        output: candidate.output,
        runState,
      }]];
    }));
  } catch {
    return {};
  }
}

export function saveWorkspaceStore(store: WorkspaceStore, storage: Pick<Storage, "setItem"> = window.localStorage): void {
  try {
    const compact = Object.fromEntries(Object.entries(store).map(([lessonId, workspace]) => [lessonId, {
      ...workspace,
      runState: workspace.runState === "running" ? "idle" : workspace.runState,
      output: workspace.output.slice(-MAX_PERSISTED_OUTPUT),
    }]));
    storage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(compact));
  } catch {
    // Storage can be disabled or full. The in-memory workspace still works.
  }
}
