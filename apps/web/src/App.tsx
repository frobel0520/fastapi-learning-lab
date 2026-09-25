import { useEffect, useMemo, useRef, useState } from "react";
import { executeCode, fetchCourse, siteMode } from "./api";
import { createSolutionEditorState, solutionWithOutput, splitEditorSubmission } from "./editor-state";
import { onRunnerProgress } from "./runner/progress";
import { SITE_COPY } from "./site-mode";
import type { Course, Lesson } from "./types";
import { IDLE_OUTPUT, loadWorkspaceStore, saveWorkspaceStore, workspaceFor } from "./workspace-state";
import type { LessonWorkspace, WorkspaceStore } from "./workspace-state";

type LayoutMode = "workbench" | "focus" | "review";
type LessonTab = "concept" | "code" | "practice";
const LESSON_TABS: LessonTab[] = ["concept", "code", "practice"];
const LESSON_TAB_LABELS: Record<LessonTab, string> = { concept: "概念解析", code: "程式碼導讀", practice: "Coding 練習" };
const COPY = SITE_COPY[siteMode];

function CloudMark() {
  return <span className="cloud-mark" aria-hidden="true"><i /><i /><i /><i /></span>;
}

function ExecutionGuide({ lesson }: { lesson: Lesson }) {
  return <section className="execution-guide" aria-label="執行與輸出說明">
    <span className="placeholder-label">RUN &amp; OUTPUT</span>
    <h3>怎麼呼叫、怎麼看到 output</h3>
    <span className="observation-badge">填入解答時會一併加入右側 Coding</span>
    <pre><code>{lesson.execution.invocation}</code></pre>
    <p>{lesson.execution.explanation}</p>
    <strong>成功時會看到</strong>
    <ul>{lesson.execution.expected_output.map((item) => <li key={item}>{item}</li>)}</ul>
  </section>;
}

function ConceptGuide({ lesson }: { lesson: Lesson }) {
  return <div className="concept-guide">
    <section className="lead-section">
      <span className="placeholder-label">LEARNING OUTCOMES</span>
      <h2>學完這一課，你會做到</h2>
      <ul className="objective-list">{lesson.objectives.map((item) => <li key={item}>{item}</li>)}</ul>
    </section>
    <section className="concept-chapter">
      <span className="placeholder-label">MENTAL MODEL</span>
      <h2>先建立正確的心智模型</h2>
      <div className="concept-stack">{lesson.concepts.map((item, index) => <div key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></div>)}</div>
    </section>
    <section className="concept-chapter">
      <span className="placeholder-label">EXECUTION FLOW</span>
      <h2>程式實際怎麼運作</h2>
      <ol className="flow-list">{lesson.code.walkthrough.map((item) => <li key={item}>{item}</li>)}</ol>
    </section>
    <section className="concept-grid">
      <div><span className="placeholder-label">COMMON PITFALLS</span><h2>常見錯誤</h2><ul>{lesson.exercise.hints.map((item) => <li key={item}>{item}</li>)}</ul></div>
      <div><span className="placeholder-label">PRACTICE MAP</span><h2>接下來怎麼驗證</h2><p>{lesson.exercise.prompt}</p><ul>{lesson.exercise.requirements.map((item) => <li key={item}>{item}</li>)}</ul></div>
    </section>
    <aside className="reference-note"><strong>Reference</strong><span>本頁已包含完成練習需要的觀念；官方文件保留作延伸查閱。</span><a href={lesson.source_url} target="_blank" rel="noreferrer">FastAPI 官方來源 <span>↗</span></a></aside>
  </div>;
}

export default function App() {
  const [course, setCourse] = useState<Course | null>(null);
  const [activeLessonId, setActiveLessonId] = useState("first-fastapi-app");
  const [activeTab, setActiveTab] = useState<LessonTab>("concept");
  const [layout, setLayout] = useState<LayoutMode>("workbench");
  const [compact, setCompact] = useState(false);
  const [dark, setDark] = useState(false);
  const [showTweaks, setShowTweaks] = useState(false);
  const [contentState, setContentState] = useState<"loading" | "ready" | "error">("loading");
  const [workspaces, setWorkspaces] = useState<WorkspaceStore>(() => loadWorkspaceStore());
  const lineNumbersRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchCourse(controller.signal).then((data) => {
      setCourse(data);
      const initial = data.lessons.find((item) => item.id === activeLessonId) ?? data.lessons[0];
      if (initial) setActiveLessonId(initial.id);
      setContentState("ready");
    }).catch((error: unknown) => {
      if ((error as { name?: string }).name !== "AbortError") setContentState("error");
    });
    return () => controller.abort();
  }, []);

  const lesson = useMemo<Lesson | null>(() => course?.lessons.find((item) => item.id === activeLessonId) ?? null, [activeLessonId, course]);
  const activeModule = course?.modules.find((item) => item.id === lesson?.module_id);
  const readyCount = course?.lessons.filter((item) => item.status === "ready").length ?? 0;
  const mappedCount = course?.modules.reduce((count, item) => count + item.lessons.length, 0) ?? 0;
  const workspace = lesson ? workspaceFor(workspaces, lesson.id, lesson.code.starter) : { code: "", output: IDLE_OUTPUT, runState: "idle" as const };
  const completedSolution = lesson ? solutionWithOutput(lesson.code.solution, lesson.execution.invocation) : "";

  useEffect(() => saveWorkspaceStore(workspaces), [workspaces]);

  function updateWorkspace(patch: Partial<LessonWorkspace>) {
    if (!lesson) return;
    setWorkspaces((current) => ({
      ...current,
      [lesson.id]: { ...workspaceFor(current, lesson.id, lesson.code.starter), ...patch },
    }));
  }

  function selectLesson(id: string) {
    const next = course?.lessons.find((item) => item.id === id);
    if (!next) return;
    setActiveLessonId(id); setActiveTab("concept");
  }

  async function runPreview() {
    if (!lesson) return;
    updateWorkspace({ runState: "running", output: COPY.running });
    const stopProgress = onRunnerProgress((message) => updateWorkspace({ runState: "running", output: message }));
    try {
      const submission = splitEditorSubmission(workspace.code, lesson.execution.invocation);
      const result = await executeCode(lesson.id, submission.code, submission.observationCode);
      const checks = result.checks.map((item) => `${item.passed ? "✓" : "✗"} ${item.name} — ${item.message}`).join("\n");
      const details = [checks, result.stdout, result.stderr].filter(Boolean).join("\n");
      updateWorkspace({ runState: result.status === "passed" ? "done" : "error", output: `${details || result.status}\n${result.runner} · ${result.duration_ms}ms` });
    } catch {
      updateWorkspace({ runState: "error", output: COPY.runFailed });
    } finally {
      stopProgress();
    }
  }

  function loadSolution() {
    if (!lesson) return;
    const next = createSolutionEditorState(lesson.code.solution, lesson.execution.invocation);
    updateWorkspace({ code: next.code, runState: next.runState, output: next.output });
    if (window.matchMedia("(max-width: 760px)").matches) setLayout("focus");
  }

  function openEditor() {
    setActiveTab("code");
    if (window.matchMedia("(max-width: 760px)").matches) setLayout("focus");
  }

  function moveTab(current: LessonTab, direction: -1 | 1) {
    const index = LESSON_TABS.indexOf(current);
    const next = LESSON_TABS[(index + direction + LESSON_TABS.length) % LESSON_TABS.length];
    setActiveTab(next);
    window.requestAnimationFrame(() => document.getElementById(`lesson-tab-${next}`)?.focus());
  }

  if (contentState === "loading") return <main className="content-state" aria-live="polite"><CloudMark /><strong>正在載入課程引擎…</strong><span>讀取模組、範例與練習契約</span></main>;
  if (contentState === "error" || !course || !lesson) return <main className="content-state is-error" role="alert"><strong>{COPY.contentErrorTitle}</strong><span>{COPY.contentErrorDetail}</span><button type="button" onClick={() => window.location.reload()}>重新載入</button></main>;

  return (
    <div className={`app-shell layout-${layout} ${compact ? "is-compact" : ""} ${dark ? "is-dark" : ""}`}>
      <a className="skip-link" href="#lesson-content">跳到課程內容</a>
      <header className="topbar">
        <div className="brand-lockup"><CloudMark /><strong>FastAPI Learning Lab</strong><span className="stage-tag">v1</span></div>
        <div className="header-context"><span className="course-label">學習路徑</span><strong>{course.title}</strong></div>
        <div className="header-actions"><a className="atlas-link" href="https://frobel0520.github.io/learning-atlas/" aria-label="返回 Learning Atlas 學習總入口">學習總覽 ↗</a><a className="text-button" href={course.source_url} target="_blank" rel="noreferrer">官方文件</a><button className="avatar-button" type="button" aria-label="本機學習者">MW</button></div>
      </header>

      <aside className="course-nav" aria-label="課程導覽">
        <div className="nav-summary"><span className="overline">AVAILABLE NOW</span><div className="progress-copy"><strong>{readyCount}/{mappedCount}</strong><span>堂可學習課程</span></div><div className="progress-track"><span style={{ width: `${mappedCount ? (readyCount / mappedCount) * 100 : 0}%` }} /></div></div>
        <nav className="module-list">
          {course.modules.map((courseModule) => <section className="module" key={courseModule.id}>
            <div className="module-heading"><span>{String(courseModule.order).padStart(2, "0")}</span><strong>{courseModule.title}</strong></div>
            <div className="lesson-list">
              {courseModule.lessons.length === 0 && <span className="module-planned">課程編寫中</span>}
              {courseModule.lessons.map((item) => <button className={`lesson-link ${item.id === lesson.id ? "is-current" : "is-ready"}`} key={item.id} onClick={() => selectLesson(item.id)} type="button"><span className="lesson-state" aria-hidden="true">{item.id === lesson.id ? "•" : ""}</span><span>{item.title}</span><small>{item.duration_minutes}m</small></button>)}
            </div>
          </section>)}
        </nav>
      </aside>

      <main className="lesson-main" id="lesson-content" tabIndex={-1}>
        <label className="mobile-course-picker"><span>切換課程</span><select aria-label="切換課程" value={lesson.id} onChange={(event) => selectLesson(event.target.value)}>{course.modules.map((courseModule) => <optgroup key={courseModule.id} label={`${String(courseModule.order).padStart(2, "0")} ${courseModule.title}`}>{courseModule.lessons.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</optgroup>)}</select></label>
        <div className="breadcrumb"><span>{String(activeModule?.order ?? 0).padStart(2, "0")} {activeModule?.title}</span><b>/</b><span>{lesson.title}</span></div>
        <div className="lesson-heading"><div><span className="lesson-kicker">LESSON {String(lesson.order).padStart(2, "0")} · {lesson.duration_minutes} MIN</span><h1>{lesson.title}</h1><p>{lesson.summary}</p></div><span className="lesson-status">可學習</span></div>
        <div className="lesson-tabs" role="tablist" aria-label="課程內容">{LESSON_TABS.map((tab) => <button aria-controls={`lesson-panel-${tab}`} aria-selected={activeTab === tab} className={activeTab === tab ? "is-active" : ""} id={`lesson-tab-${tab}`} key={tab} onClick={() => setActiveTab(tab)} onKeyDown={(event) => { if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); moveTab(tab, event.key === "ArrowLeft" ? -1 : 1); } }} role="tab" tabIndex={activeTab === tab ? 0 : -1} type="button">{LESSON_TAB_LABELS[tab]}</button>)}</div>
        <article className="lesson-content">
          {activeTab === "concept" && <section aria-labelledby="lesson-tab-concept" id="lesson-panel-concept" role="tabpanel"><ConceptGuide lesson={lesson} /></section>}
          {activeTab === "code" && <section aria-labelledby="lesson-tab-code" className="reading-panel" id="lesson-panel-code" role="tabpanel"><h2>逐步理解範例</h2><ol>{lesson.code.walkthrough.map((item) => <li key={item}>{item}</li>)}</ol><ExecutionGuide lesson={lesson} /><button className="secondary-button" type="button" onClick={loadSolution}>填入解答與輸出程式</button></section>}
          {activeTab === "practice" && <section aria-labelledby="lesson-tab-practice" className="practice-panel" id="lesson-panel-practice" role="tabpanel"><span className="placeholder-label">CODING EXERCISE</span><h2>{lesson.exercise.title}</h2><p>{lesson.exercise.prompt}</p><h3>完成條件</h3><ul>{lesson.exercise.requirements.map((item) => <li key={item}>{item}</li>)}</ul><details><summary>需要提示？</summary><ul>{lesson.exercise.hints.map((item) => <li key={item}>{item}</li>)}</ul></details><ExecutionGuide lesson={lesson} /><button className="primary-button" type="button" onClick={openEditor}>開始修改程式</button></section>}
        </article>
      </main>

      <aside className="lab-panel" aria-label="程式碼實驗室">
        <div className="lab-header"><div><button className="lab-back-button" type="button" onClick={() => setLayout("workbench")}>返回教材</button><span className="status-dot" /><strong>{lesson.code.filename}</strong></div><span>{COPY.runtimeLabel}</span></div>
        <div className="editor-wrap"><div className="line-numbers" ref={lineNumbersRef} aria-hidden="true">{workspace.code.split("\n").map((_, index) => <span key={index}>{index + 1}</span>)}</div><textarea aria-describedby="lesson-checks" aria-label="FastAPI 程式碼" value={workspace.code} onChange={(event) => updateWorkspace({ code: event.target.value })} onScroll={(event) => { if (lineNumbersRef.current) lineNumbersRef.current.scrollTop = event.currentTarget.scrollTop; }} spellCheck={false} /></div>
        <div className="lab-toolbar">
          <button className="secondary-button" disabled={workspace.runState === "running"} type="button" onClick={() => updateWorkspace({ code: lesson.code.starter, output: IDLE_OUTPUT, runState: "idle" })}>重設</button>
          <button className="solution-button" disabled={workspace.runState === "running" || workspace.code === completedSolution} type="button" onClick={loadSolution}>{workspace.code === completedSolution ? "已填入解答" : "填入解答"}</button>
          <button className="run-button" disabled={workspace.runState === "running"} type="button" onClick={runPreview}>{workspace.runState === "running" ? "執行中…" : "執行測試"}</button>
        </div>
        <div aria-busy={workspace.runState === "running"} aria-live="polite" className={`terminal is-${workspace.runState}`} role="status"><div><strong>OUTPUT</strong><span>{workspace.runState.toUpperCase()}</span></div><pre>{workspace.output}</pre></div>
        <div className="lab-note" id="lesson-checks"><strong>本題將檢查</strong><ul>{lesson.exercise.checks.map((item) => <li key={item}>{item}</li>)}</ul></div>
      </aside>

      <button className="tweaks-trigger" type="button" onClick={() => setShowTweaks((value) => !value)} aria-expanded={showTweaks}>顯示設定</button>
      {showTweaks && <div className="tweaks-panel"><div className="tweaks-heading"><strong>Tweaks</strong><button type="button" onClick={() => setShowTweaks(false)}>關閉</button></div><label>版面<select value={layout} onChange={(event) => setLayout(event.target.value as LayoutMode)}><option value="workbench">Workbench</option><option value="focus">Focus</option><option value="review">Review</option></select></label><label className="switch-row"><span>緊湊密度</span><input type="checkbox" checked={compact} onChange={(event) => setCompact(event.target.checked)} /></label><label className="switch-row"><span>深色模式</span><input type="checkbox" checked={dark} onChange={(event) => setDark(event.target.checked)} /></label></div>}
    </div>
  );
}
