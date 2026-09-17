export type ContentStatus = "ready" | "draft" | "planned";

export type LessonSummary = { id: string; title: string; duration_minutes: number; status: ContentStatus };
export type CourseModule = { id: string; order: number; title: string; summary: string; lessons: LessonSummary[] };
export type Lesson = LessonSummary & {
  module_id: string; order: number; summary: string; objectives: string[]; concepts: string[];
  code: { filename: string; starter: string; solution: string; walkthrough: string[] };
  exercise: { title: string; prompt: string; requirements: string[]; hints: string[]; checks: string[] };
  execution: { mode: "python" | "fastapi"; invocation: string; explanation: string; expected_output: string[] };
  source_url: string;
};
export type Course = {
  id: string; title: string; locale: string; status: "draft" | "published"; source_url: string;
  modules: CourseModule[]; lessons: Lesson[];
};
