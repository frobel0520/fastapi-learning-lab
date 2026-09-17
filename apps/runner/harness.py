import asyncio
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


def evaluate(lesson_id: str, namespace: dict[str, object]) -> list[dict[str, object]]:
    if lesson_id == "security-boundary-probe":
        return [
            check("Network disabled", lambda: namespace.get("network_blocked") is True, "container 不得建立外部網路連線"),
            check("Root filesystem read-only", lambda: namespace.get("root_read_only") is True, "root filesystem 不得可寫"),
            check("Non-root user", lambda: namespace.get("effective_uid") not in {None, 0}, "程式不得以 root 執行"),
        ]
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
