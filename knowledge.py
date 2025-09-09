from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from library.logbook import LogBookHandler
from library.database import database
from fastapi import Request, FastAPI
import importlib
import uvicorn
import asyncio
import os

#==============CONFIG==============#
WEB_PORT = 8020
#============END CONFIG============#

fastapp = FastAPI()
database.modernize()
logbook = LogBookHandler('root')
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# noinspection PyUnusedLocal
@fastapp.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    logbook.info(f"IP {request.client.host} Attempted to connect but was Unauthorized")
    # A Basic web page with the entire purpose of redirecting the user away from the page.
    content = """
<!DOCTYPE html>
<html lang="en">
<head>
  <title>REDIRECTING</title>
</head>
<body>
<h1>You are being redirected after an unauthorized connection.</h1>
<script>
    window.location.href = "/login";
</script>
</body>
    """
    return HTMLResponse(content, status_code=401)

# noinspection PyUnusedLocal
@fastapp.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logbook.info(f"IP {request.client.host} Attempted to connect but was Not Found")
    with open("modules/404.html", "r") as file:
        content = file.read()
    return HTMLResponse(content, status_code=404)

fastapp.mount(
    "/static/login",
    StaticFiles(directory=os.path.join("modules", "login", "static")),
    name="register_static"
)

@fastapp.get("/favicon.ico", include_in_schema=False)
async def favicon():
    image_path = "favicon.png"
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            return HTMLResponse(content=image_file.read(), media_type="image/png")
    else:
        raise FileNotFoundError("No favicon.png found")

modules_dir = "modules"

for module_name in os.listdir(modules_dir):
    module_path = os.path.join(modules_dir, module_name)

    if os.path.isfile(module_path) or module_name == "__pycache__":
        continue
    if os.path.isdir(module_path):
        # 🔧 Mount static files if they exist
        static_path = os.path.join(module_path, "static")
        if os.path.isdir(static_path):
            mount_path = f"/static/{module_name}"
            fastapp.mount(mount_path, StaticFiles(directory=static_path), name=f"{module_name}_static")
            logbook.info(f"[✓] Mounted static files for {module_name} at {mount_path}")
        else:
            raise FileNotFoundError(f"No static directory found in {module_name}")

        # 📦 Import and register router
        routes_file = os.path.join(module_path, "routes.py")
        if os.path.exists(routes_file):
            try:
                module = importlib.import_module(f"modules.{module_name}.routes")
                if hasattr(module, "router"):
                    fastapp.include_router(module.router)
                    logbook.info(f"[✓] Loaded router from {module_name} module")
                else:
                    logbook.info(f"[!] No 'router' found in {module_name}.routes")
            except Exception as err:
                logbook.error(f"[✗] Failed to load {module_name}: {err}", exception=err)
        else:
            raise FileNotFoundError(f"No routes.py found in {module_name}")

if __name__ == "__main__":
    if __name__ == "__main__":
        config = uvicorn.Config(
            "knowledge:fastapp",
            host="0.0.0.0",
            port=WEB_PORT,
            loop="asyncio",
            lifespan="on",
            reload=True
        )
        server = uvicorn.Server(config)
        try:
            asyncio.run(server.serve())
        except KeyboardInterrupt:
            print("Interrupt signal detected, Stopping server and shutting down.")