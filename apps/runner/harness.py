import asyncio
import dataclasses
import inspect
import json
import runpy
import sys
import traceback
from pathlib import Path
from typing import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient


RESULT_MARKER = "__FASTAPI_LAB_RESULT__="


HTTP_CASES: dict[str, list[dict[str, object]]] = {
    "path-enum-values": [
        {"name": "接受 Enum 值", "path": "/models/resnet", "status": 200, "json": {"model_name": "resnet"}},
        {"name": "拒絕未知值", "path": "/models/unknown", "status": 422},
    ],
    "query-parameters": [
        {"name": "Query 分頁", "path": "/items?skip=1&limit=2", "status": 200, "json": ["b", "c"]},
        {"name": "Query 型別驗證", "path": "/items?skip=nope", "status": 422},
    ],
    "request-body": [
        {"name": "合法 JSON body", "method": "POST", "path": "/items", "json_body": {"name": "Pen", "price": 1.5}, "status": 200, "json": {"name": "Pen", "price": 1.5}},
        {"name": "缺少必填欄位", "method": "POST", "path": "/items", "json_body": {"name": "Pen"}, "status": 422},
    ],
    "body-multiple-params": [
        {"name": "多組 body", "method": "PUT", "path": "/items/7", "json_body": {"item": {"name": "Pen"}, "user": {"username": "ada"}, "importance": 2}, "status": 200, "json": {"item_id": 7, "item": {"name": "Pen"}, "user": {"username": "ada"}, "importance": 2}},
        {"name": "Body 數值限制", "method": "PUT", "path": "/items/7", "json_body": {"item": {"name": "Pen"}, "user": {"username": "ada"}, "importance": 0}, "status": 422},
    ],
    "query-string-validation": [
        {"name": "合法搜尋字串", "path": "/search?q=fastapi", "status": 200, "json": {"q": "fastapi"}},
        {"name": "拒絕過短字串", "path": "/search?q=x", "status": 422},
    ],
    "path-numeric-validation": [
        {"name": "合法數值範圍", "path": "/items/100", "status": 200, "json": {"item_id": 100}},
        {"name": "拒絕超出範圍", "path": "/items/101", "status": 422},
    ],
    "query-param-models": [
        {"name": "Query model", "path": "/items?limit=2&order_by=updated_at", "status": 200, "json": {"limit": 2, "order_by": "updated_at"}},
        {"name": "拒絕額外 query", "path": "/items?tool=unknown", "status": 422},
    ],
    "body-fields": [
        {"name": "合法欄位", "method": "POST", "path": "/items", "json_body": {"name": "Pen", "price": 2}, "status": 200, "json": {"name": "Pen", "price": 2.0}},
        {"name": "拒絕零價格", "method": "POST", "path": "/items", "json_body": {"name": "Pen", "price": 0}, "status": 422},
    ],
    "nested-models": [
        {"name": "巢狀 model", "method": "POST", "path": "/items", "json_body": {"name": "Pen", "tags": ["blue", "blue"], "image": {"url": "https://example.com/pen.png", "name": "pen"}}, "status": 200},
        {"name": "拒絕無效 URL", "method": "POST", "path": "/items", "json_body": {"name": "Pen", "image": {"url": "bad", "name": "pen"}}, "status": 422},
    ],
    "request-examples": [
        {"name": "範例不影響驗證", "method": "POST", "path": "/items", "json_body": {"name": "Book", "price": 3}, "status": 200, "json": {"name": "Book", "price": 3.0}},
    ],
    "extra-data-types": [
        {"name": "UUID 與 datetime", "method": "POST", "path": "/events", "json_body": {"id": "12345678-1234-5678-1234-567812345678", "starts_at": "2026-01-02T03:04:05Z"}, "status": 200},
        {"name": "拒絕無效 UUID", "method": "POST", "path": "/events", "json_body": {"id": "bad", "starts_at": "2026-01-02T03:04:05Z"}, "status": 422},
    ],
    "dataclass-models": [
        {"name": "巢狀 dataclass", "method": "POST", "path": "/catalogs", "json_body": {"owner": "Leo", "items": [{"name": "Pen", "price": 1.5, "tags": ["blue"]}]}, "status": 200, "json": {"owner": "Leo", "items": [{"name": "Pen", "price": 1.5, "tags": ["blue"]}]}},
        {"name": "拒絕錯誤 dataclass 欄位", "method": "POST", "path": "/catalogs", "json_body": {"owner": "Leo", "items": [{"name": "Pen", "price": "wrong"}]}, "status": 422},
    ],
    "pydantic-v2-migration": [
        {"name": "v2 model 設定", "method": "POST", "path": "/items", "json_body": {"name": "  Pen  ", "price": 2}, "status": 200, "json": {"name": "Pen", "price": 2.0}},
        {"name": "拒絕額外欄位", "method": "POST", "path": "/items", "json_body": {"name": "Pen", "price": 2, "legacy": True}, "status": 422},
        {"name": "拒絕非正價格", "method": "POST", "path": "/items", "json_body": {"name": "Pen", "price": 0}, "status": 422},
    ],
    "cookie-parameters": [
        {"name": "讀取 cookie", "path": "/session", "cookies": {"session_id": "abc"}, "status": 200, "json": {"session_id": "abc"}},
        {"name": "選填 cookie", "path": "/session", "status": 200, "json": {"session_id": None}},
    ],
    "header-parameters": [
        {"name": "讀取 header", "path": "/agent", "headers": {"user-agent": "lab-check"}, "status": 200, "json": {"user_agent": "lab-check"}},
    ],
    "cookie-param-models": [
        {"name": "Cookie model", "path": "/cookies", "cookies": {"session_id": "abc", "fatebook_tracker": "t1"}, "status": 200, "json": {"session_id": "abc", "fatebook_tracker": "t1"}},
        {"name": "Cookie 必填欄位", "path": "/cookies", "status": 422},
    ],
    "header-param-models": [
        {"name": "Header model", "path": "/headers", "headers": {"host": "api.example", "save-data": "true"}, "status": 200, "json": {"host": "api.example", "save_data": True}},
    ],
    "form-data": [
        {"name": "Form fields", "method": "POST", "path": "/login", "data": {"username": "ada", "password": "abcd"}, "status": 200, "json": {"username": "ada", "password_length": "4"}},
        {"name": "Form 必填欄位", "method": "POST", "path": "/login", "data": {"username": "ada"}, "status": 422},
    ],
    "form-models": [
        {"name": "Form model", "method": "POST", "path": "/login", "data": {"username": "ada", "password": "abcd"}, "status": 200, "json": {"username": "ada"}},
        {"name": "拒絕額外 form 欄位", "method": "POST", "path": "/login", "data": {"username": "ada", "password": "abcd", "extra": "x"}, "status": 422},
    ],
    "request-files": [
        {"name": "UploadFile", "method": "POST", "path": "/files", "files": {"file": ["hello.txt", "hello", "text/plain"]}, "status": 200, "json": {"filename": "hello.txt", "content_type": "text/plain", "size": 5}},
        {"name": "File 必填", "method": "POST", "path": "/files", "status": 422},
    ],
    "forms-and-files": [
        {"name": "Form 與 File", "method": "POST", "path": "/assets", "data": {"description": "notes"}, "files": {"file": ["note.txt", "abc", "text/plain"]}, "status": 200, "json": {"description": "notes", "filename": "note.txt", "size": 3}},
        {"name": "Form 必填", "method": "POST", "path": "/assets", "files": {"file": ["note.txt", "abc", "text/plain"]}, "status": 422},
    ],
    "response-model": [
        {"name": "過濾敏感欄位", "path": "/users/me", "status": 200, "json": {"username": "ada"}},
    ],
    "extra-models": [
        {"name": "Input/Output models", "method": "POST", "path": "/users", "json_body": {"username": "ada", "password": "secret"}, "status": 200, "json": {"username": "ada"}},
    ],
    "response-status-code": [
        {"name": "201 Created", "method": "POST", "path": "/items", "status": 201, "json": {"created": True}},
    ],
    "handling-errors": [
        {"name": "存在的資源", "path": "/items/1", "status": 200, "json": {"id": 1, "name": "Pen"}},
        {"name": "404 契約", "path": "/items/99", "status": 404, "json": {"detail": "Item not found"}},
    ],
    "path-operation-configuration": [
        {"name": "舊版 endpoint 可呼叫", "path": "/legacy", "status": 200, "json": {"deprecated": True}},
    ],
    "json-compatible-encoder": [
        {"name": "datetime 可 JSON 化", "path": "/payload", "status": 200, "json": {"created_at": "2026-01-02T00:00:00+00:00"}},
    ],
    "body-updates": [
        {"name": "只更新提供欄位", "method": "PATCH", "path": "/items/1", "json_body": {"price": 5}, "status": 200, "json": {"name": "Pen", "price": 5.0}},
        {"name": "明確 null", "method": "PATCH", "path": "/items/1", "json_body": {"name": None}, "status": 200, "json": {"name": None, "price": 2.0}},
    ],
}


def check(name: str, assertion: Callable[[], bool], message: str) -> dict[str, object]:
    try:
        passed = bool(assertion())
        return {"name": name, "passed": passed, "message": "通過" if passed else message}
    except Exception as error:
        return {"name": name, "passed": False, "message": f"{message} ({type(error).__name__})"}


def load_namespace() -> dict[str, object]:
    return runpy.run_path("/tmp/main.py")


def app_from(namespace: dict[str, object]) -> FastAPI:
    app = namespace.get("app")
    if not isinstance(app, FastAPI):
        raise AssertionError("找不到名為 app 的 FastAPI instance")
    return app


def evaluate_http_cases(lesson_id: str, app: FastAPI) -> list[dict[str, object]]:
    client = TestClient(app)
    results: list[dict[str, object]] = []
    for case in HTTP_CASES[lesson_id]:
        kwargs: dict[str, object] = {}
        for source, target in (("json_body", "json"), ("data", "data"), ("files", "files"), ("headers", "headers"), ("cookies", "cookies")):
            if source in case:
                value = case[source]
                if source == "files":
                    value = {key: tuple(file_value) for key, file_value in value.items()}
                kwargs[target] = value
        response = client.request(str(case.get("method", "GET")), str(case["path"]), **kwargs)
        passed = response.status_code == case["status"]
        if "json" in case:
            try:
                passed = passed and response.json() == case["json"]
            except Exception:
                passed = False
        if "text" in case:
            passed = passed and response.text == case["text"]
        if "text_contains" in case:
            passed = passed and str(case["text_contains"]) in response.text
        results.append({"name": str(case["name"]), "passed": passed, "message": "通過" if passed else f"得到 HTTP {response.status_code}: {response.text[:160]}"})

    schema = app.openapi()
    if lesson_id == "request-examples":
        examples = schema["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"].get("examples", {})
        results.append(check("OpenAPI example", lambda: "normal" in examples, "找不到 normal request example"))
    if lesson_id == "path-operation-configuration":
        operation = schema["paths"]["/legacy"]["get"]
        results.append(check("Operation metadata", lambda: operation.get("deprecated") is True and operation.get("summary") == "舊版入口" and "legacy" in operation.get("tags", []), "OpenAPI metadata 不完整"))
    return results


def evaluate(lesson_id: str, namespace: dict[str, object]) -> list[dict[str, object]]:
    if lesson_id == "security-boundary-probe":
        return [
            check("Network disabled", lambda: namespace.get("network_blocked") is True, "container 不得建立外部網路連線"),
            check("Root filesystem read-only", lambda: namespace.get("root_read_only") is True, "root filesystem 不得可寫"),
            check("Non-root user", lambda: namespace.get("effective_uid") not in {None, 0}, "程式不得以 root 執行"),
        ]
    if lesson_id in HTTP_CASES:
        results = evaluate_http_cases(lesson_id, app_from(namespace))
        if lesson_id == "dataclass-models":
            item_type = namespace.get("Item")
            catalog_type = namespace.get("Catalog")
            results.append(check("Dataclass models", lambda: dataclasses.is_dataclass(item_type) and dataclasses.is_dataclass(catalog_type), "Item 與 Catalog 必須是 dataclass"))
            results.append(check(
                "Independent list defaults",
                lambda: item_type is not None and item_type(name="A", price=1).tags is not item_type(name="B", price=2).tags,
                "可變 list 預設值必須使用 default_factory",
            ))
            results.append(check(
                "Nested OpenAPI schemas",
                lambda: {"Item", "Catalog"} <= set(app_from(namespace).openapi().get("components", {}).get("schemas", {})),
                "OpenAPI 必須包含 Item 與 Catalog schemas",
            ))
        if lesson_id == "pydantic-v2-migration":
            item_type = namespace.get("Item")
            results.append(check(
                "Pydantic v2 APIs",
                lambda: item_type is not None and item_type.model_validate({"name": " Pen ", "price": 1}).model_dump() == {"name": "Pen", "price": 1.0},
                "必須使用可運作的 model_validate、model_dump 與字串去空白設定",
            ))
            results.append(check(
                "Forbid extra fields",
                lambda: item_type is not None and item_type.model_config.get("extra") == "forbid",
                "model_config 必須設定 extra='forbid'",
            ))
        return results
    if lesson_id == "python-type-hints":
        greeting = namespace.get("greeting")
        signature = inspect.signature(greeting) if callable(greeting) else None
        return [
            check("參數型別", lambda: signature is not None and signature.parameters["name"].annotation is str, "name 必須標註為 str"),
            check("回傳內容", lambda: greeting("Ada") == {"message": "Hello Ada"}, "greeting 必須保留指定行為"),
            check("回傳型別", lambda: signature is not None and signature.return_annotation == dict[str, str], "回傳型別必須是 dict[str, str]"),
        ]
    if lesson_id == "async-await":
        fetch_user = namespace.get("fetch_user")
        return [
            check("Coroutine function", lambda: inspect.iscoroutinefunction(fetch_user), "fetch_user 必須使用 async def"),
            check("非同步結果", lambda: asyncio.run(fetch_user()) == {"id": 7}, "await 完成後必須回傳 id 7"),
        ]
    if lesson_id == "http-api-mental-model":
        request, response = namespace.get("request"), namespace.get("response")
        return [
            check("Request", lambda: request == {"method": "GET", "path": "/items/42", "body": None}, "request 的 method、path、body 不完整"),
            check("Response", lambda: response == {"status": 200, "body": {"id": 42}}, "response 的 status 或 body 不正確"),
        ]
    app = app_from(namespace)
    client = TestClient(app)
    if lesson_id in {"first-fastapi-app", "fastapi-cli"}:
        response = client.get("/health")
        return [
            check("GET /health", lambda: response.status_code == 200, "必須回傳 HTTP 200"),
            check("JSON body", lambda: response.json() == {"status": "ok"}, "JSON 必須是 {status: ok}"),
        ]
    if lesson_id == "path-operation":
        valid, invalid = client.get("/items/42"), client.get("/items/not-a-number")
        return [
            check("整數路徑", lambda: valid.status_code == 200 and valid.json() == {"item_id": 42}, "整數 item_id 必須被解析"),
            check("驗證錯誤", lambda: invalid.status_code == 422, "非整數 item_id 必須回傳 422"),
        ]
    if lesson_id == "automatic-docs-openapi":
        schema = app.openapi()
        operation = schema.get("paths", {}).get("/items/{item_id}", {}).get("get", {})
        return [
            check("API metadata", lambda: schema["info"]["title"] == "Catalog API" and schema["info"]["version"] == "1.0.0", "title 或 version 不正確"),
            check("Operation summary", lambda: bool(operation.get("summary")), "route 必須具有 summary"),
        ]
    raise ValueError(f"Unsupported lesson: {lesson_id}")


def main() -> None:
    payload = json.loads(sys.stdin.read())
    Path("/tmp/main.py").write_text(payload["code"], encoding="utf-8")
    try:
        namespace = load_namespace()
        checks = evaluate(payload["lesson_id"], namespace)
        observation_code = payload.get("observation_code")
        if observation_code:
            try:
                exec(observation_code, namespace)
                checks.append({"name": "Print output", "passed": True, "message": "已印出實際執行結果"})
            except Exception as error:
                checks.append({"name": "Print output", "passed": False, "message": f"觀察程式執行失敗：{type(error).__name__}: {error}"})
        status = "passed" if checks and all(item["passed"] for item in checks) else "failed"
        result = {"status": status, "checks": checks, "stdout": "", "stderr": "", "duration_ms": 0, "runner": "local-container"}
    except Exception:
        result = {"status": "failed", "checks": [], "stdout": "", "stderr": traceback.format_exc(limit=4), "duration_ms": 0, "runner": "local-container"}
    # Keep learner stdout separate from the machine-readable runner result.
    # The leading newline also handles print(..., end="") without corrupting
    # the result frame. The host always selects the final marker occurrence.
    sys.stdout.write(f"\n{RESULT_MARKER}{json.dumps(result, ensure_ascii=False)}\n")


if __name__ == "__main__":
    main()
