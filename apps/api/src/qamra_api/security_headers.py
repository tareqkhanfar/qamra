"""Security headers on every API response (defence in depth behind the nginx edge)."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_ALWAYS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"),
    (b"cross-origin-resource-policy", b"same-origin"),
    (b"x-robots-tag", b"noindex, nofollow"),
]
# personal/admin data must never sit in shared or browser caches
_PRIVATE_PREFIXES = ("/api/auth", "/api/admin", "/api/children", "/api/books")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        private = str(scope.get("path", "")).startswith(_PRIVATE_PREFIXES)
        docs = str(scope.get("path", "")).startswith("/api/docs")

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [h for h in message.get("headers", []) if h[0].lower() != b"server"]
                present = {h[0].lower() for h in headers}
                for name, value in _ALWAYS:
                    if docs and name == b"content-security-policy":
                        continue  # the dev-only Swagger UI needs its own scripts
                    if name not in present:
                        headers.append((name, value))
                if private:
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
