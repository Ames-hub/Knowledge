from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone, timedelta
from fastapi.responses import PlainTextResponse
from fastapi import Request
from pathlib import Path
import urllib.parse
import asyncio
import os

# Do not serve
DNS_list = {}
dns_lock = asyncio.Lock()

BASE_DIR = Path(os.getcwd()).resolve()

class PathTraversalBlocker(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        now = datetime.now(timezone.utc)

        # Check if IP is blocked
        async with dns_lock:
            blocked_until = DNS_list.get(ip)
            if blocked_until:
                if blocked_until > now:
                    return PlainTextResponse("Access denied.", status_code=403)
                else:
                    del DNS_list[ip]

        # Decode URL path
        raw_path = request.url.path
        decoded_path = urllib.parse.unquote(raw_path)

        # Check for path traversal
        try:
            requested_path = (BASE_DIR / decoded_path.lstrip("/")).resolve()
        except Exception:
            return PlainTextResponse("Bad path.")

        if not str(requested_path).startswith(str(BASE_DIR)):
            # Block IP for 2 days
            async with dns_lock:
                DNS_list[ip] = now + timedelta(days=2)
            return PlainTextResponse(
                "Your IP has been temporarily blocked for attempted path traversal.\n"
                "Seriously man, get a job. This cant be all there is for you.",
                status_code=403
            )

        # All clear, continue processing
        return await call_next(request)

# This is what the middleware loader expects
def middleware(request: Request, call_next):
    blocker = PathTraversalBlocker(request.app, dispatch=None)
    return blocker.dispatch(request, call_next)
