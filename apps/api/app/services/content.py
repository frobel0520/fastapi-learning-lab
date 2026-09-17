import json
import os
from functools import lru_cache
from pathlib import Path

from app.models.content import Course, CoverageManifest, ExecutionGuide, Lesson, ModuleContent


PYTHON_OBSERVATIONS = {
    "python-type-hints": 'print(greeting("Leo")["message"])',
    "async-await": "print(asyncio.run(fetch_user()))",
    "http-api-mental-model": "print(request)\nprint(response)",
}


def _request(method: str, path: str, arguments: str = "", *, text: bool = False) -> str:
    separator = ", " if arguments else ""
    body_reader = "response.text" if text else "response.json()"
    return (
        "from fastapi.testclient import TestClient\n\n"
        "client = TestClient(app)\n"
        f'response = client.{method}("{path}"{separator}{arguments})\n'
        "print(response.status_code)\n"
        f"print({body_reader})"
    )


FASTAPI_OBSERVATIONS = {
    "first-fastapi-app": _request("get", "/health"),
    "path-operation": _request("get", "/items/42"),
    "automatic-docs-openapi": _request("get", "/items/7"),
    "fastapi-cli": _request("get", "/health"),
}


def _with_execution_guide(lesson: Lesson) -> Lesson:
    invocation = PYTHON_OBSERVATIONS.get(lesson.id)
    if invocation:
        explanation = (
            "這類純 Python 練習會直接執行 main.py；RUN & OUTPUT 顯示應加入的 print(...)。"
            "按「填入解答」會把實作與這段輸出程式一起放進 Coding。"
        )
        if lesson.id == "async-await":
            explanation += " async 函式先回傳 coroutine，需用 asyncio.run(...)（或在既有事件迴圈中 await）才會真正執行。"
        mode = "python"
    else:
        invocation = FASTAPI_OBSERVATIONS.get(lesson.id)
        if invocation is None:
            raise ValueError(f"Lesson {lesson.id} is missing an output observation")
        explanation = (
            "這段程式透過 TestClient 實際呼叫本題端點，並把 response 的 status code 與內容 print 到 OUTPUT。"
            "按「填入解答」時會一併加入 Coding；自行作答而未加入時，Runner 會在 hidden checks 後獨立執行。"
        )
        mode = "fastapi"
    return lesson.model_copy(update={
        "execution": ExecutionGuide(
            mode=mode,
            invocation=invocation,
            explanation=explanation,
            expected_output=lesson.exercise.checks,
        )
    })


def _content_root() -> Path:
    override = os.getenv("FASTAPI_LAB_CONTENT_DIR")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[4] / "content"


def _load_json(filename: str) -> object:
    path = _content_root() / filename
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def get_course() -> Course:
    course = Course.model_validate(_load_json("course.json"))
    module_files = sorted((_content_root() / "modules").glob("*.json"))
    module_by_id = {module.id: module for module in course.modules}
    lessons = [_with_execution_guide(lesson) for lesson in course.lessons]
    lesson_ids = {lesson.id for lesson in lessons}
    for path in module_files:
        content = ModuleContent.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if content.module.id not in module_by_id:
            raise ValueError(f"Unknown module id in {path.name}: {content.module.id}")
        for raw_lesson in content.lessons:
            lesson = _with_execution_guide(raw_lesson)
            if lesson.module_id != content.module.id:
                raise ValueError(f"Lesson {lesson.id} points to the wrong module")
            if lesson.id in lesson_ids:
                raise ValueError(f"Duplicate lesson id: {lesson.id}")
            lesson_ids.add(lesson.id)
            lessons.append(lesson)
        summary_ids = {item.id for item in content.module.lessons}
        content_ids = {item.id for item in content.lessons}
        if summary_ids != content_ids:
            raise ValueError(f"Lesson summaries do not match content in {path.name}")
        module_by_id[content.module.id] = content.module
    return course.model_copy(update={
        "modules": sorted(module_by_id.values(), key=lambda module: module.order),
        "lessons": sorted(lessons, key=lambda lesson: (lesson.module_id, lesson.order)),
    })


@lru_cache(maxsize=1)
def get_coverage() -> CoverageManifest:
    return CoverageManifest.model_validate(_load_json("coverage-manifest.json"))


def get_lesson(lesson_id: str) -> Lesson | None:
    return next((lesson for lesson in get_course().lessons if lesson.id == lesson_id), None)
