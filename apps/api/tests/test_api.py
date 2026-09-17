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
    assert item["ready_lesson_count"] == 111

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
    assert len(entries) >= 60
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
    assert {"m02-request-data", "m03-modeling-validation", "m04-http-inputs", "m05-responses-errors", "m06-dependencies", "m07-security", "m08-data", "m09-architecture", "m10-realtime"} <= ready_modules
    dependency_lesson_ids = {
        "dependency-basics",
        "class-dependencies",
        "callable-dependencies",
        "sub-dependencies",
        "dependency-caching",
        "decorator-dependencies",
        "router-dependencies",
        "global-dependencies",
        "yield-dependencies",
    }
    assert dependency_lesson_ids <= set(lesson_ids)
    dependency_coverage = [entry for entry in entries if entry["module_id"] == "m06-dependencies"]
    assert dependency_coverage
    assert all(entry["status"] == "ready" for entry in dependency_coverage)
    security_lesson_ids = {
        "oauth2-password-bearer",
        "current-user-dependency",
        "oauth2-password-form",
        "password-hashing",
        "jwt-authentication",
        "active-user",
        "oauth2-scopes",
        "legacy-authentication-403",
    }
    assert security_lesson_ids <= set(lesson_ids)
    security_coverage = [entry for entry in entries if entry["module_id"] == "m07-security"]
    assert security_coverage
    assert all(entry["status"] == "ready" for entry in security_coverage)
    data_lesson_ids = {
        "sqlmodel-table",
        "sqlite-engine-tables",
        "session-dependency",
        "create-rows",
        "read-pagination",
        "data-model-separation",
        "update-delete",
    }
    assert data_lesson_ids <= set(lesson_ids)
    data_coverage = [entry for entry in entries if entry["module_id"] == "m08-data"]
    assert data_coverage
    assert all(entry["status"] == "ready" for entry in data_coverage)
    architecture_lesson_ids = {
        "middleware-process-time",
        "cors-origins",
        "bigger-applications",
        "static-files",
        "frontend-spa",
        "sub-applications",
        "jinja-templates",
        "lifespan-resources",
        "settings-environment",
        "wsgi-mount",
    }
    assert architecture_lesson_ids <= set(lesson_ids)
    architecture_coverage = [entry for entry in entries if entry["module_id"] == "m09-architecture"]
    assert len(architecture_coverage) == 10
    assert all(entry["status"] == "ready" and entry["lesson_id"] in architecture_lesson_ids for entry in architecture_coverage)
    realtime_lesson_ids = {
        "background-tasks",
        "stream-json-lines",
        "server-sent-events",
        "streaming-response",
        "websocket-echo",
    }
    assert realtime_lesson_ids <= set(lesson_ids)
    realtime_coverage = [entry for entry in entries if entry["module_id"] == "m10-realtime"]
    assert len(realtime_coverage) == 5
    assert all(entry["status"] == "ready" and entry["lesson_id"] in realtime_lesson_ids for entry in realtime_coverage)
    testing_lesson_ids = {
        "testclient-basics",
        "dependency-overrides-testing",
        "testing-lifespan-events",
        "async-http-tests",
        "testing-websockets",
        "testing-database-isolation",
        "debugging-entrypoint",
    }
    assert testing_lesson_ids <= set(lesson_ids)
    testing_coverage = [entry for entry in entries if entry["module_id"] == "m11-testing"]
    advanced_lesson_ids = {
        "api-metadata-docs", "advanced-operation-configuration", "dynamic-status-codes",
        "direct-custom-responses", "additional-openapi-responses", "response-cookies",
        "response-headers", "direct-request-access", "openapi-callbacks", "openapi-webhooks",
        "sdk-generation-contract", "advanced-union-types", "json-base64-bytes",
        "strict-content-type", "graphql-strawberry", "custom-gzip-route",
        "conditional-openapi", "extend-openapi-schema", "separate-io-schemas",
        "self-hosted-docs-assets", "configure-swagger-ui",
    }
    assert advanced_lesson_ids <= set(lesson_ids)
    advanced_coverage = [entry for entry in entries if entry["module_id"] == "m12-advanced"]
    deployment_lesson_ids = {
        "fastapi-version-policy", "fastapi-cloud-options", "production-server-command",
        "deployment-concepts", "https-termination", "proxy-root-path",
        "server-workers", "container-readiness", "cloud-provider-readiness",
    }
    assert deployment_lesson_ids <= set(lesson_ids)
    deployment_coverage = [entry for entry in entries if entry["module_id"] == "m13-deployment"]
    modeling_lesson_ids = {"dataclass-models", "pydantic-v2-migration"}
    assert modeling_lesson_ids <= set(lesson_ids)
    modeling_closure = [entry for entry in entries if entry["lesson_id"] in modeling_lesson_ids]
    assert {entry["id"] for entry in modeling_closure} == {"advanced-dataclasses", "recipe-pydantic-v2"}
    assert len(entries) == 105
    assert all(entry["status"] == "ready" and entry["lesson_id"] for entry in entries)
    assert len(testing_coverage) == 7
    assert all(entry["status"] == "ready" and entry["lesson_id"] in testing_lesson_ids for entry in testing_coverage)
    assert len(advanced_coverage) == 24
    assert all(entry["status"] == "ready" and entry["lesson_id"] in advanced_lesson_ids for entry in advanced_coverage)
    assert len(deployment_coverage) == 10
    assert all(entry["status"] == "ready" and entry["lesson_id"] in deployment_lesson_ids for entry in deployment_coverage)
    assert {entry["id"] for entry in entries if entry["source_url"] in {
        "https://fastapi.tiangolo.com/editor-support/",
        "https://fastapi.tiangolo.com/advanced/security/",
        "https://fastapi.tiangolo.com/deployment/",
        "https://fastapi.tiangolo.com/how-to/general/",
        "https://fastapi.tiangolo.com/how-to/authentication-error-status-code/",
    }} == {
        "editor-support",
        "advanced-security-overview",
        "deployment-overview",
        "recipe-general",
        "recipe-authentication-403",
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
