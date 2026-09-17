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
    "path-enum-values": _request("get", "/models/resnet"),
    "query-parameters": _request("get", "/items?skip=1&limit=2"),
    "request-body": _request("post", "/items", 'json={"name": "Pen", "price": 1.5}'),
    "body-multiple-params": _request("put", "/items/7", 'json={"item": {"name": "Pen"}, "user": {"username": "ada"}, "importance": 2}'),
    "query-string-validation": _request("get", "/search?q=fastapi"),
    "path-numeric-validation": _request("get", "/items/100"),
    "query-param-models": _request("get", "/items?limit=2&order_by=updated_at"),
    "body-fields": _request("post", "/items", 'json={"name": "Pen", "price": 2}'),
    "nested-models": _request("post", "/items", 'json={"name": "Pen", "tags": ["blue"], "image": {"url": "https://example.com/pen.png", "name": "pen"}}'),
    "request-examples": _request("post", "/items", 'json={"name": "Book", "price": 3}'),
    "extra-data-types": _request("post", "/events", 'json={"id": "12345678-1234-5678-1234-567812345678", "starts_at": "2026-01-02T03:04:05Z"}'),
    "dataclass-models": '''from fastapi.testclient import TestClient

client = TestClient(app)
response = client.post(
    "/catalogs",
    json={"owner": "Leo", "items": [{"name": "Pen", "price": 1.5, "tags": ["blue"]}]},
)
print(response.status_code)
print(response.json())
print(app.openapi()["components"]["schemas"])''',
    "pydantic-v2-migration": '''from fastapi.testclient import TestClient

item = Item.model_validate({"name": "  Pen  ", "price": 2})
print(item.model_dump())

client = TestClient(app)
response = client.post("/items", json={"name": "  Pen  ", "price": 2})
print(response.status_code)
print(response.json())''',
    "cookie-parameters": _request("get", "/session", 'cookies={"session_id": "abc"}'),
    "header-parameters": _request("get", "/agent", 'headers={"user-agent": "lab-browser"}'),
    "cookie-param-models": _request("get", "/cookies", 'cookies={"session_id": "abc", "fatebook_tracker": "t1"}'),
    "header-param-models": _request("get", "/headers", 'headers={"host": "api.example", "save-data": "true"}'),
    "form-data": _request("post", "/login", 'data={"username": "ada", "password": "abcd"}'),
    "form-models": _request("post", "/login", 'data={"username": "ada", "password": "abcd"}'),
    "request-files": _request("post", "/files", 'files={"file": ("hello.txt", b"hello", "text/plain")}'),
    "forms-and-files": _request("post", "/assets", 'data={"description": "notes"}, files={"file": ("note.txt", b"abc", "text/plain")}'),
    "response-model": _request("get", "/users/me"),
    "extra-models": _request("post", "/users", 'json={"username": "ada", "password": "secret"}'),
    "response-status-code": _request("post", "/items"),
    "handling-errors": _request("get", "/items/1"),
    "path-operation-configuration": _request("get", "/legacy"),
    "json-compatible-encoder": _request("get", "/payload"),
    "body-updates": _request("patch", "/items/1", 'json={"price": 5}'),
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
