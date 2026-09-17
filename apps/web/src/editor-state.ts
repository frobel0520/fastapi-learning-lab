export const SOLUTION_READY_MESSAGE = "已填入參考解答與輸出觀察程式。按「執行測試」查看結果。";
export const OUTPUT_OBSERVATION_MARKER = "# --- RUN & OUTPUT：印出結果 ---";

export function solutionWithOutput(solution: string, invocation: string): string {
  return `${solution.trimEnd()}\n\n${OUTPUT_OBSERVATION_MARKER}\n${invocation.trim()}\n`;
}

export function splitEditorSubmission(code: string, fallbackInvocation: string) {
  const markerIndex = code.lastIndexOf(OUTPUT_OBSERVATION_MARKER);
  if (markerIndex === -1) {
    return { code, observationCode: fallbackInvocation.trim() };
  }

  const solution = code.slice(0, markerIndex).trimEnd();
  const observationCode = code.slice(markerIndex + OUTPUT_OBSERVATION_MARKER.length).trim();
  return {
    code: `${solution}\n`,
    observationCode: observationCode || fallbackInvocation.trim(),
  };
}

export function createSolutionEditorState(solution: string, invocation: string) {
  return {
    code: solutionWithOutput(solution, invocation),
    runState: "idle" as const,
    output: SOLUTION_READY_MESSAGE,
  };
}
