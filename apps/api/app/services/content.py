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
    "dependency-basics": _request("get", "/items?q=api&skip=2&limit=3"),
    "class-dependencies": _request("get", "/items?q=api&skip=1&limit=4"),
    "callable-dependencies": _request("get", "/check?q=Learn%20FastAPI"),
    "sub-dependencies": _request("get", "/search?q=request"),
    "dependency-caching": _request("get", "/cached"),
    "decorator-dependencies": _request("get", "/items", 'headers={"x-token": "lab-secret"}'),
    "router-dependencies": _request("get", "/admin/status", 'headers={"x-key": "admin-key"}'),
    "global-dependencies": _request("get", "/items", 'headers={"x-key": "global-key"}'),
    "yield-dependencies": _request("get", "/resource"),
    "oauth2-password-bearer": _request("get", "/token-info", 'headers={"authorization": "Bearer abc"}'),
    "current-user-dependency": _request("get", "/users/me", 'headers={"authorization": "Bearer alice"}'),
    "oauth2-password-form": _request("post", "/token", 'data={"username": "alice", "password": "swordfish"}'),
    "password-hashing": _request("post", "/verify", 'data={"username": "alice", "password": "swordfish"}'),
    "active-user": _request("get", "/users/me", 'headers={"authorization": "Bearer alice"}'),
    "legacy-authentication-403": '''from fastapi.testclient import TestClient

client = TestClient(app)
missing = client.get("/me")
authenticated = client.get("/me", headers={"authorization": "Bearer abc"})
print(missing.status_code, missing.json())
print(authenticated.status_code, authenticated.json())''',
    "sqlmodel-table": _request("post", "/heroes", 'json={"name": "Ada", "secret_name": "Code"}'),
    "sqlite-engine-tables": _request("get", "/db-info"),
    "session-dependency": _request("get", "/session-check"),
    "create-rows": _request("post", "/heroes", 'json={"name": "Ada"}'),
    "read-pagination": _request("get", "/heroes?offset=1&limit=1"),
    "data-model-separation": _request("post", "/heroes", 'json={"name": "Ada", "age": 36, "secret_name": "Code"}'),
    "update-delete": _request("get", "/heroes/1"),
    "middleware-process-time": _request("get", "/ping"),
    "cors-origins": _request("get", "/profile", 'headers={"origin": "https://learn.example.com"}'),
    "bigger-applications": _request("get", "/api/items/"),
    "static-files": _request("get", "/static/hello.txt", text=True),
    "frontend-spa": _request("get", "/api/ping"),
    "sub-applications": _request("get", "/subapi/reports"),
    "jinja-templates": _request("get", "/hello/Leo", text=True),
    "settings-environment": _request("get", "/info"),
    "wsgi-mount": _request("get", "/legacy/?name=Leo", text=True),
    "background-tasks": _request("post", "/notifications/leo@example.com"),
    "stream-json-lines": _request("get", "/items/stream", text=True),
    "server-sent-events": _request("get", "/progress", text=True),
    "streaming-response": _request("get", "/logs/stream", text=True),
    "testclient-basics": _request("get", "/items/7"),
    "async-http-tests": _request("get", "/ping"),
    "debugging-entrypoint": _request("get", "/debug-info"),
}

FASTAPI_OBSERVATIONS["jwt-authentication"] = '''from fastapi.testclient import TestClient

client = TestClient(app)
login = client.post("/token", data={"username": "alice", "password": "swordfish"})
token = login.json()["access_token"]
response = client.get("/users/me", headers={"authorization": f"Bearer {token}"})
print(response.status_code)
print(response.json())'''

FASTAPI_OBSERVATIONS["oauth2-scopes"] = '''from fastapi.testclient import TestClient

client = TestClient(app)
login = client.post("/token", data={"username": "alice", "password": "secret", "scope": "profile:read items:read"})
token = login.json()["access_token"]
response = client.get("/items", headers={"authorization": f"Bearer {token}"})
print(response.status_code)
print(response.json())'''

FASTAPI_OBSERVATIONS["lifespan-resources"] = '''from fastapi.testclient import TestClient

with TestClient(app) as client:
    response = client.get("/ready")
    print(response.status_code)
    print(response.json())'''

FASTAPI_OBSERVATIONS["websocket-echo"] = '''from fastapi.testclient import TestClient

client = TestClient(app)
with client.websocket_connect("/ws") as websocket:
    websocket.send_text("hello")
    message = websocket.receive_json()
    print(message)'''

FASTAPI_OBSERVATIONS["dependency-overrides-testing"] = '''from fastapi.testclient import TestClient

app.dependency_overrides[get_current_user] = override_current_user
try:
    response = TestClient(app).get("/users/me")
    print(response.status_code)
    print(response.json())
finally:
    app.dependency_overrides.clear()'''

FASTAPI_OBSERVATIONS["testing-lifespan-events"] = '''from fastapi.testclient import TestClient

events.clear()
with TestClient(app) as client:
    response = client.get("/ready")
    print(response.status_code)
    print(response.json())
print(events)'''

FASTAPI_OBSERVATIONS["testing-websockets"] = '''from fastapi.testclient import TestClient

client = TestClient(app)
with client.websocket_connect("/ws") as websocket:
    websocket.send_text("hello")
    message = websocket.receive_json()
    print(message)'''

FASTAPI_OBSERVATIONS["testing-database-isolation"] = '''from fastapi.testclient import TestClient

client = TestClient(app)
client.post("/heroes", json={"name": "Grace"})
response = client.get("/heroes")
print(response.status_code)
print(response.json())'''

FASTAPI_OBSERVATIONS.update({
    "api-metadata-docs": '''from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/items")
schema = app.openapi()
print(response.status_code)
print(response.json())
print(schema["info"])
print(schema["tags"])''',
    "advanced-operation-configuration": '''from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/items/7")
operation = app.openapi()["paths"]["/items/{item_id}"]["get"]
print(response.status_code)
print(response.json())
print({"operationId": operation["operationId"], "x-audience": operation["x-audience"]})''',
    "dynamic-status-codes": '''from fastapi.testclient import TestClient

client = TestClient(app)
created = client.put("/items/pen", json={"name": "Pen"})
updated = client.put("/items/pen", json={"name": "Blue Pen"})
print(created.status_code, created.json())
print(updated.status_code, updated.json())''',
    "direct-custom-responses": '''from fastapi.testclient import TestClient

response = TestClient(app).get("/legacy")
print(response.status_code)
print(response.headers["content-type"])
print(response.text)''',
    "additional-openapi-responses": '''from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/items/99")
responses = app.openapi()["paths"]["/items/{item_id}"]["get"]["responses"]
print(response.status_code)
print(response.json())
print(sorted(responses))''',
    "response-cookies": '''from fastapi.testclient import TestClient

response = TestClient(app).post("/login")
print(response.status_code)
print(response.json())
print(response.headers["set-cookie"])''',
    "response-headers": '''from fastapi.testclient import TestClient

response = TestClient(app).get("/items")
print(response.status_code)
print(response.json())
print(response.headers["x-trace-id"])''',
    "direct-request-access": '''from fastapi.testclient import TestClient

response = TestClient(app).get("/inspect", headers={"x-request-id": "abc"})
print(response.status_code)
print(response.json())''',
    "openapi-callbacks": '''from fastapi.testclient import TestClient

client = TestClient(app)
response = client.post("/invoices", json={"id": "inv-1", "callback_url": "https://client.example/hook"})
callbacks_schema = app.openapi()["paths"]["/invoices"]["post"]["callbacks"]
print(response.status_code)
print(response.json())
print(list(callbacks_schema))''',
    "openapi-webhooks": '''from fastapi.testclient import TestClient

response = TestClient(app).post("/subscriptions", json={"username": "leo"})
print(response.status_code)
print(response.json())
print(list(app.openapi()["webhooks"]))''',
    "sdk-generation-contract": '''from fastapi.testclient import TestClient

response = TestClient(app).get("/users/7")
operation = app.openapi()["paths"]["/users/{user_id}"]["get"]
print(response.status_code)
print(response.json())
print({"operationId": operation["operationId"], "tags": operation["tags"]})''',
    "advanced-union-types": '''from fastapi.testclient import TestClient

client = TestClient(app)
valid = client.get("/greet?name=Leo")
missing = client.get("/greet")
print(valid.status_code, valid.json())
print(missing.status_code, missing.json())''',
    "json-base64-bytes": '''from fastapi.testclient import TestClient

response = TestClient(app).post("/decode", json={"data": "SGVsbG8="})
print(response.status_code)
print(response.json())''',
    "strict-content-type": '''from fastapi.testclient import TestClient

client = TestClient(app)
valid = client.post("/items", json={"name": "Pen"})
missing = client.post("/items", content='{"name":"Pen"}')
print(valid.status_code, valid.json())
print(missing.status_code, missing.json())''',
    "graphql-strawberry": '''from fastapi.testclient import TestClient

response = TestClient(app).post("/graphql", json={"query": "{ user { name age } }"})
print(response.status_code)
print(response.json())''',
    "custom-gzip-route": '''import gzip
from fastapi.testclient import TestClient

body = gzip.compress(b'{"name":"Pen"}')
response = TestClient(app).post(
    "/items",
    content=body,
    headers={"content-type": "application/json", "content-encoding": "gzip"},
)
print(response.status_code)
print(response.json())''',
    "conditional-openapi": '''from fastapi.testclient import TestClient

client = TestClient(app)
items = client.get("/items")
schema = client.get("/openapi.json")
print(items.status_code, items.json())
print(schema.status_code)''',
    "extend-openapi-schema": '''from fastapi.testclient import TestClient

response = TestClient(app).get("/items")
first = app.openapi()
second = app.openapi()
print(response.status_code, response.json())
print(first["info"]["x-logo"])
print(first is second)''',
    "separate-io-schemas": '''from fastapi.testclient import TestClient

response = TestClient(app).post("/items", json={"name": "Pen"})
operation = app.openapi()["paths"]["/items"]["post"]
print(response.status_code, response.json())
print(operation["requestBody"]["content"]["application/json"]["schema"])
print(operation["responses"]["200"]["content"]["application/json"]["schema"])''',
    "self-hosted-docs-assets": '''from fastapi.testclient import TestClient

response = TestClient(app).get("/docs")
print(response.status_code)
print("/static/swagger-ui-bundle.js" in response.text)
print("/static/swagger-ui.css" in response.text)''',
    "configure-swagger-ui": '''from fastapi.testclient import TestClient

response = TestClient(app).get("/docs")
print(response.status_code)
print('"deepLinking": false' in response.text)
print('"theme": "obsidian"' in response.text)''',
    "fastapi-version-policy": _request("get", "/build"),
    "fastapi-cloud-options": '''from fastapi.testclient import TestClient

client = TestClient(app)
managed = client.get("/deployment-choice?managed=true")
self_managed = client.get("/deployment-choice?managed=false")
print(managed.status_code, managed.json())
print(self_managed.status_code, self_managed.json())''',
    "production-server-command": _request("get", "/server-config"),
    "deployment-concepts": '''from fastapi.testclient import TestClient

client = TestClient(app)
live = client.get("/live")
ready = client.get("/ready")
print(live.status_code, live.json())
print(ready.status_code, ready.json())''',
    "https-termination": '''from fastapi.testclient import TestClient

http = TestClient(app, follow_redirects=False).get("/secure")
https = TestClient(app, base_url="https://testserver").get("/secure")
print(http.status_code, http.headers.get("location"))
print(https.status_code, https.json())''',
    "proxy-root-path": '''from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get("/info")
schema = client.get("/openapi.json").json()
print(response.status_code, response.json())
print(schema.get("servers"))''',
    "server-workers": '''from fastapi.testclient import TestClient

client = TestClient(app)
cpu_bound = client.get("/worker-plan?cpu=4&memory_mb=1024&per_worker_mb=256")
memory_bound = client.get("/worker-plan?cpu=8&memory_mb=1024&per_worker_mb=300")
print(cpu_bound.status_code, cpu_bound.json())
print(memory_bound.status_code, memory_bound.json())''',
    "container-readiness": _request("get", "/healthz"),
    "cloud-provider-readiness": _request("get", "/release"),
})


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
