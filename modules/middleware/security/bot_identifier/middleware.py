from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import PlainTextResponse
from collections import defaultdict, deque
from library.logbook import LogBookHandler
from fastapi import FastAPI, Request
import asyncio
import time
import re

app = FastAPI()
logbook = LogBookHandler("security.bot_identification")

CLIENT_TTL = 600  # 10 minutes
CLEANUP_INTERVAL = 200  # every N requests
request_counter = 0


def make_client_id(request: Request):
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")[:60]
    return f"{ip}:{ua}"


client_data = defaultdict(lambda: {
    "window_start": 0.0,
    "request_count": 0,
    "score": 2,
    "normal_requests": 0,
    "last_request": 0.0,
    "reaction_threshold": 0.15,
    "paths": deque(maxlen=6)
})


class BotDetectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, request_window: int = 60, decay_threshold: int = 12):
        super().__init__(app)
        self.request_window = request_window
        self.decay_threshold = decay_threshold

    def cleanup_clients(self):
        now = time.time()
        to_delete = [
            k for k, v in client_data.items()
            if now - v["last_request"] > CLIENT_TTL
        ]
        for k in to_delete:
            del client_data[k]

    async def dispatch(self, request: Request, call_next):
        global request_counter
        request_counter += 1

        if request_counter % CLEANUP_INTERVAL == 0:
            self.cleanup_clients()

        path = request.url.path

        if path.startswith("/static/") or path == "/favicon.ico" or path.startswith("/api/"):
            return await call_next(request)

        client_id = make_client_id(request)
        now = time.time()
        data = client_data[client_id]

        triggered = False
        time_since_last = now - data["last_request"]

        # Rolling window counter
        if now - data["window_start"] > self.request_window:
            data["window_start"] = now
            data["request_count"] = 0

        data["request_count"] += 1

        # Reaction speed check
        if data["request_count"] > 25 and time_since_last < data["reaction_threshold"]:
            data["score"] = min(15, data["score"] + 3)
            data["reaction_threshold"] = max(0.08, data["reaction_threshold"] - 0.01)
            logbook.info(f"{client_id} | Fast reaction burst. score: {data['score']}")
            triggered = True

        # Backend / probe files
        backend_files = [
            "/robots.txt", "/.env", "/config.json", "/db.sql", "/backup.zip",
            "/wp-admin", "/phpmyadmin", "/.git", "/.git/config",
            "/server-status", "/openapi.json"
        ]

        if path in backend_files:
            data["score"] += 8
            logbook.info(f"{client_id} Accessed backend route. score: {data['score']}")
            triggered = True

        # Method signal
        if request.method not in ("GET", "POST"):
            data["score"] += 1
            triggered = True

        # Path randomness / entropy
        if len(path) > 20 and re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", path.lower()):
            data["score"] += 2
            triggered = True

        # Burst unique path detection
        data["paths"].append(path)
        if len(set(data["paths"])) == data["paths"].maxlen and time_since_last < 0.3:
            data["score"] += 3
            triggered = True

        # Decay / reward logic
        if not triggered:
            data["normal_requests"] += 1
            data["reaction_threshold"] = min(0.25, data["reaction_threshold"] + 0.002)

            if data["normal_requests"] >= self.decay_threshold:
                data["score"] = max(0, data["score"] - 1)
                data["normal_requests"] = 0
        else:
            data["normal_requests"] = 0

        data["last_request"] = now
        client_data[client_id] = data

        # Track if this is their first request ever
        is_first_request = data["request_count"] == 1

        response = await call_next(request)

        # If FIRST request is 404 → instant bot
        if is_first_request and response.status_code == 404:
            data["score"] = 15
            logbook.info(f"{client_id} | First request was 404. Instant bot flag.")
            return PlainTextResponse(
                "You have been identified as a bot account and have been timed out from this webapp.",
                status_code=403
            )

        # Hard block
        if data["score"] >= 12 and path != "/robots.txt":
            return PlainTextResponse(
                "You have been identified as a bot account and have been timed out from this webapp.",
                status_code=403
            )

        # Soft lag curve
        if data["score"] >= 5:
            lag = (data["score"] ** 2) * 0.01
            await asyncio.sleep(min(lag, 2.0))

        return response


def middleware(request: Request, call_next):
    blocker = BotDetectionMiddleware(request.app)
    return blocker.dispatch(request, call_next)