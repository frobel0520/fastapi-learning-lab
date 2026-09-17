from typing import Literal

from pydantic import BaseModel, ConfigDict, HttpUrl


class Exercise(BaseModel):
    title: str
    prompt: str
    requirements: list[str]
    hints: list[str]
    checks: list[str]


class CodeExample(BaseModel):
    filename: str = "main.py"
    starter: str
    solution: str
    walkthrough: list[str]


class ExecutionGuide(BaseModel):
    mode: Literal["python", "fastapi"]
    invocation: str
    explanation: str
    expected_output: list[str]


class Lesson(BaseModel):
    id: str
    module_id: str
    order: int
    title: str
    duration_minutes: int
    status: Literal["ready", "draft", "planned"]
    summary: str
    objectives: list[str]
    concepts: list[str]
    code: CodeExample
    exercise: Exercise
    execution: ExecutionGuide | None = None
    source_url: HttpUrl


class LessonSummary(BaseModel):
    id: str
    title: str
    duration_minutes: int
    status: Literal["ready", "draft", "planned"]


class Module(BaseModel):
    id: str
    order: int
    title: str
    summary: str
    lessons: list[LessonSummary]


class ModuleContent(BaseModel):
    module: Module
    lessons: list[Lesson]


class Course(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    locale: str
    status: Literal["draft", "published"]
    source_url: HttpUrl
    modules: list[Module]
    lessons: list[Lesson]


class CourseSummary(BaseModel):
    id: str
    title: str
    locale: str
    status: Literal["draft", "published"]
    module_count: int
    lesson_count: int
    ready_lesson_count: int


class CourseList(BaseModel):
    items: list[CourseSummary]
    source: HttpUrl


class CoverageEntry(BaseModel):
    id: str
    category: str
    module_id: str
    title: str
    source_url: HttpUrl
    status: Literal["ready", "draft", "planned"]
    lesson_id: str | None = None


class CoverageManifest(BaseModel):
    schema_version: str
    source_index_url: HttpUrl
    checked_at: str
    target_fastapi_version: str
    entries: list[CoverageEntry]
