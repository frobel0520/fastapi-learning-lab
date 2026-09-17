from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import allowed_origins
from app.models.content import Course, CourseList, CourseSummary, CoverageManifest, Lesson
from app.models.execution import ExecutionRequest, ExecutionResult
from app.runners.base import Runner
from app.services.content import get_course, get_coverage, get_lesson
from app.services.runner import get_runner
from app.services.submission import normalize_execution_request


app = FastAPI(
    title="FastAPI Learning Lab API",
    version="0.1.0",
    summary="課程、練習與安全執行器的 API 契約",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "stage": "learning-lab-v1"}


@app.get("/api/v1/courses", response_model=CourseList, tags=["courses"])
async def list_courses() -> CourseList:
    course = get_course()
    return CourseList(
        items=[CourseSummary(
            id=course.id,
            title=course.title,
            locale=course.locale,
            status=course.status,
            module_count=len(course.modules),
            lesson_count=len(course.lessons),
            ready_lesson_count=sum(lesson.status == "ready" for lesson in course.lessons),
        )],
        source=course.source_url,
    )


@app.get("/api/v1/courses/{course_id}", response_model=Course, tags=["courses"])
async def read_course(course_id: str) -> Course:
    course = get_course()
    if course.id != course_id:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.get("/api/v1/lessons/{lesson_id}", response_model=Lesson, tags=["courses"])
async def read_lesson(lesson_id: str) -> Lesson:
    lesson = get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@app.get("/api/v1/coverage", response_model=CoverageManifest, tags=["courses"])
async def read_coverage() -> CoverageManifest:
    return get_coverage()


@app.post(
    "/api/v1/executions",
    response_model=ExecutionResult,
    tags=["executions"],
)
async def execute_code(
    payload: ExecutionRequest,
    runner: Runner = Depends(get_runner),
) -> ExecutionResult:
    if get_lesson(payload.lesson_id) is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return await runner.run(normalize_execution_request(payload))
