type ProgressListener = (message: string) => void;

const listeners = new Set<ProgressListener>();

export function onRunnerProgress(listener: ProgressListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function reportRunnerProgress(message: string): void {
  for (const listener of listeners) listener(message);
}
