import os


DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:4173",
    "http://127.0.0.1:4173",
)


def allowed_origins(raw: str | None = None) -> list[str]:
    configured = os.getenv("FASTAPI_LAB_ALLOWED_ORIGINS") if raw is None else raw
    candidates = configured.split(",") if configured else DEFAULT_ALLOWED_ORIGINS
    origins: list[str] = []
    for candidate in candidates:
        origin = candidate.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins
