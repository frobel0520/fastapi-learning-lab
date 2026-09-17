from fastapi import Request
from fastapi.responses import Response
from workers import asgi

from app.main import app


Default = asgi.entrypoint(app)


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str, request: Request) -> Response:
    """Serve React through Cloudflare Static Assets after API routes are checked."""
    env = request.scope["env"]
    asset_path = path or "index.html"
    asset_response = await env.ASSETS.fetch(f"https://assets.local/{asset_path}")
    if asset_response.status == 404 and "." not in asset_path:
        asset_response = await env.ASSETS.fetch("https://assets.local/index.html")
    return Response(
        content=await asset_response.bytes(),
        status_code=asset_response.status,
        headers=asset_response.headers,
    )

