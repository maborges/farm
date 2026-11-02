"""Loopback-only HTTP allowlist for the development RLS canary."""

from __future__ import annotations

from main import app as deepfarms_app


class RLSCanaryAllowlist:
    """Expose only the three approved method/path pairs from the real API."""

    _ALLOWED = {
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/notificacoes/"),
        ("GET", "/api/v1/notificacoes/"),
    }

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            key = (scope.get("method", "").upper(), scope.get("path", ""))
            if key not in self._ALLOWED:
                body = b'{"detail":"Not Found"}'
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"cache-control", b"no-store"),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return
        elif scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return

        await self.app(scope, receive, send)


app = RLSCanaryAllowlist(deepfarms_app)
