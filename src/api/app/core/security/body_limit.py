"""Reject oversized request bodies while they arrive at Adept's API.

Two checks, both before the route parses anything:

1. A declared Content-Length above the limit is rejected immediately.
2. Every body chunk is counted as it is received, so requests *without* Content-Length
   (chunked transfer) are stopped at the limit too, before multipart parsing writes more
   to a temporary file or JSON parsing buffers more in memory.

Pure ASGI (not BaseHTTPMiddleware) because it has to wrap `receive`. When the limit is hit
mid-stream, the app usually turns the read error into its own error response; that response
is replaced with our 413.
"""

from __future__ import annotations

import json

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Multipart overhead (boundaries, part headers) on top of the file itself.
_MULTIPART_SLACK = 64 * 1024


class _BodyTooLarge(Exception):
    pass


async def _send_error(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps({"error": {"code": code, "message": message}}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_json_bytes: int, max_upload_bytes: int) -> None:
        self.app = app
        self.max_json_bytes = max_json_bytes
        self.max_upload_bytes = max_upload_bytes + _MULTIPART_SLACK

    def limit_for(self, content_type: str) -> int:
        if content_type.startswith("multipart/form-data"):
            return self.max_upload_bytes
        return self.max_json_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        limit = self.limit_for(headers.get("content-type", ""))
        declared = headers.get("content-length")
        if declared is not None:
            if not declared.isdigit():
                await _send_error(send, 400, "bad_request", "Invalid Content-Length header.")
                return
            if int(declared) > limit:
                await _send_error(send, 413, "payload_too_large", "Request payload too large.")
                return

        received = 0
        too_large = False
        started = False

        async def limited_receive() -> Message:
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    too_large = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if too_large:
                if not started:
                    started = True
                    await _send_error(send, 413, "payload_too_large", "Request payload too large.")
                return  # drop the app's own response to the aborted read
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            pass
        if too_large and not started:
            await _send_error(send, 413, "payload_too_large", "Request payload too large.")
