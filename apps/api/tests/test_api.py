from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "stage": "learning-lab-v1"}


def test_course_catalog_and_lesson_lookup() -> None:
    catalog = client.get("/api/v1/courses")
    assert catalog.status_code == 200
    item = catalog.json()["items"][0]
    assert item["module_count"] == 14
    assert item["ready_lesson_count"] == 7

    lesson = client.get("/api/v1/lessons/first-fastapi-app")
    assert lesson.status_code == 200
    assert lesson.json()["source_url"].startswith("https://fastapi.tiangolo.com/")
    assert lesson.json()["exercise"]["checks"]


def test_course_and_coverage_contracts() -> None:
    course = client.get("/api/v1/courses/fastapi-complete-guide")
    assert course.status_code == 200
    lessons = course.json()["lessons"]
    lesson_ids = [lesson["id"] for lesson in lessons]
    assert len(lesson_ids) == len(set(lesson_ids))
    assert all(lesson["execution"]["invocation"] for lesson in lessons)
    assert all(lesson["execution"]["explanation"] for lesson in lessons)
    assert all(lesson["execution"]["expected_output"] for lesson in lessons)
    assert all("print(" in lesson["execution"]["invocation"] for lesson in lessons)
    fastapi_lessons = [lesson for lesson in lessons if lesson["execution"]["mode"] == "fastapi"]
    assert all("TestClient" in lesson["execution"]["invocation"] for lesson in fastapi_lessons)
    assert all("print(" not in lesson["code"]["solution"] for lesson in lessons)
    async_lesson = next(lesson for lesson in lessons if lesson["id"] == "async-await")
    assert async_lesson["execution"]["invocation"] == "print(asyncio.run(fetch_user()))"
    assert "print(" not in async_lesson["code"]["solution"]

    coverage = client.get("/api/v1/coverage")
    assert coverage.status_code == 200
    entries = coverage.json()["entries"]
    assert len(entries) == 6
    assert all(entry["source_url"].startswith("https://fastapi.tiangolo.com/") for entry in entries)
    coverage_ids = [entry["id"] for entry in entries]
    assert len(coverage_ids) == len(set(coverage_ids))
    course_modules = {module["id"] for module in course.json()["modules"]}
    assert all(entry["module_id"] in course_modules for entry in entries)
    linked_entries = [entry for entry in entries if entry["lesson_id"]]
    assert all(entry["lesson_id"] in lesson_ids for entry in linked_entries)
    module_by_lesson = {lesson["id"]: lesson["module_id"] for lesson in course.json()["lessons"]}
    assert all(entry["module_id"] == module_by_lesson[entry["lesson_id"]] for entry in linked_entries)
    ready_modules = {lesson["module_id"] for lesson in course.json()["lessons"] if lesson["status"] == "ready"}
    assert {"m00-foundations", "m01-first-api"} <= ready_modules
    assert all(entry["status"] == "ready" and entry["lesson_id"] for entry in entries)
    assert {entry["id"] for entry in entries if entry["source_url"] in {
        "https://fastapi.tiangolo.com/editor-support/",
    }} == {
        "editor-support",
    }


def test_missing_content_returns_404() -> None:
    assert client.get("/api/v1/courses/missing").status_code == 404
    assert client.get("/api/v1/lessons/missing").status_code == 404


def test_local_cors_origin_is_allowed() -> None:
    response = client.options(
        "/api/v1/courses",
        headers={
            "Origin": "http://127.0.0.1:4173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4173"
