from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import PlainTextResponse
from fastapi import FastAPI, Request
from collections import defaultdict
import asyncio
import time

app = FastAPI()

# Global client tracker
client_data = defaultdict(lambda: {
    "timestamps": [],
    "score": 0,
    "called_login_api": False,
    "normal_requests": 0,  # Track normal requests for decay
    "last_request": 0.0  # Store timestamp of last request in seconds
})

class BotDetectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, request_window: int = 60, decay_threshold: int = 10, reaction_threshold: float = 0.15):
        super().__init__(app)
        self.request_window = request_window
        self.decay_threshold = decay_threshold
        self.reaction_threshold = reaction_threshold  # 150ms

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        path = request.url.path

        #  Ignore static files, and API Calls (as API Calls can often be numerous even from a normal user)
        if path.startswith("/static/") or path == "/favicon.ico" or path.startswith("/api/"):
            return await call_next(request)

        now = time.time()
        data = client_data[client_ip]

        #  High request rate check with reaction threshold 
        time_since_last = now - data["last_request"]
        data["timestamps"] = [t for t in data["timestamps"] if now - t <= self.request_window]
        data["timestamps"].append(now)
        triggered = False

        # Only count as bot if last request was < reaction threshold
        if len(data["timestamps"]) > 20 and time_since_last < self.reaction_threshold:
            data["score"] = min(10, data["score"] + 3)
            triggered = True

        #  /api/user/login before /login 
        if path == "/api/user/login":
            data["called_login_api"] = True
        if path == "/login" and data["called_login_api"]:
            data["score"] = 10
            triggered = True

        #  Accessing backend files 
        backend_files = ["/robots.txt", "/.env", "/config.json"]
        if path in backend_files:
            data["score"] = 10
            triggered = True

        #  Decay logic 
        if not triggered:
            data["normal_requests"] += 1
            if data["normal_requests"] >= self.decay_threshold:
                data["score"] = max(0, data["score"] - 1)
                data["normal_requests"] = 0
        else:
            data["normal_requests"] = 0

        # Update last_request timestamp
        data["last_request"] = now
        client_data[client_ip] = data

        # print(f"[BotDetection] {client_ip} score: {data['score']}, last_request_interval: {time_since_last:.3f}s")

        # Block if score >=10, except for robots.txt
        if data["score"] >= 10 and path != "/robots.txt":
            return PlainTextResponse(
                "You have been identified as a bot account and have been timed out from this webapp.",
                status_code=403
            )

        if data['score'] >= 5:
            # At 5 or above, start to add 25ms of delay for each point of lag
            additional_lag = data['score'] * 0.025
            
            # Start rate limiting
            await asyncio.sleep(additional_lag)

        response = await call_next(request)
        return response

def middleware(request: Request, call_next):
    blocker = BotDetectionMiddleware(request.app)
    return blocker.dispatch(request, call_next)