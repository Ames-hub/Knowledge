from library import settings
import os

#==============CONFIG==============#
WEB_PORT = settings.get.web_port()
#============END CONFIG============#

if __name__ == "__main__":
    if not os.path.exists(settings.SETTINGS_PATH):
        print("We've detected this is the first time the app has started.")
        print("So we'll need to ask a couple questions to get you started.\n")

        print("Question 1: Do you want us to use SSL? (It makes your connection secure and safer from hackers)\nAnswer 'Yes' or 'No'")
        if (use_ssl := input(">>> ").lower()) == "yes":
            print("Enabling SSL.")
            settings.save("use_ssl", True)
        else:
            print("Keeping SSL Disabled.")
            settings.save("use_ssl", False)

        while True:
            print("Question 2: What is your preferred port for the webserver? (Default: 8020)")
            WEB_PORT = input(">>> ")
            if WEB_PORT == "":
                WEB_PORT = 8020
            elif not str(WEB_PORT).isdigit():
                print("Invalid port type. Must be a number.")
                continue
            WEB_PORT = int(WEB_PORT)
            break

        print("""
============================================================
                     SECURITY DISCLAIMER
============================================================

Knowledge is a fairly advanced app, with multiple security
features to help keep users safe, including salting passwords,
SSL setup, permissions management, and more.

That said, it is your responsibility to ensure this app is not
compromised. Knowledge is secure only when our effort is combined
with yours.

- You are responsible for ensuring SSL is configured, that
  firewall rules are set, user access is set, etc. etc..
- We can provide advice if you ask, but we are not liable 
  for any breaches, data loss, or misuse.
- Running this app on an exposed network or with incorrect 
  settings may put your data and users at risk.
              
The data at
risk may be:
1. Internal finance documents
2. The names, addresses, phone numbers, etc. of whoever is recorded in the "Central Files" Module
3.  

If you don't know if its secure, I'd honestly rather
that you ask an AI than you ask nobody.
              
For any questions or inquiries about Knowledge app:
My discord is: @friendlyfox.exe
              
Please make sure your system is secure before going live.
============================================================
        """)
        print("Configuration Complete. Further configuration available in 'settings' module of web app.\n")
        print("Thank you for choosing us, And welcome to Knowledge!\n")

from library.auth import setup_selfsigned, setup_certbot_ssl, get_ssl_filepaths
from fastapi.responses import HTMLResponse, PlainTextResponse
from modules.browser.routes import show_apps as apps_route
from modules.login.routes import show_login as login_route
from fastapi.staticfiles import StaticFiles
from library.logbook import LogBookHandler
from library.database import database
from fastapi import Request, FastAPI
from library.auth import get_user
from fastapi import Depends
import importlib
import uvicorn
import asyncio
import secrets

fastapi = FastAPI()
if __name__ == "__main__":
    database.modernize()
logbook = LogBookHandler('root')
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

@fastapi.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request):
    logbook.info(f"{request.client.host} Is asking for the robots.txt")
    with open('robots.txt') as f:
        data = f.read()
    return data

# noinspection PyUnusedLocal
@fastapi.exception_handler(401)
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
<p>All this means, most likely, is that your login has expired or its your first time viewing this app on this device</p>
<script>
    window.location.href = "/";
</script>
</body>
    """
    return HTMLResponse(content, status_code=401)

@fastapi.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    logbook.info(f"IP {request.client.host} Attempted to connect but was Forbidden")
    if str(exc) == "403: Account is arrested":
        with open("modules/403-arrested.html", "r") as file:
            content = file.read()
    else:
        with open("modules/403.html", "r") as file:
            content = file.read()
    return HTMLResponse(content, status_code=403)

# noinspection PyUnusedLocal
@fastapi.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logbook.info(f"IP {request.client.host} Attempted to connect but was Not Found")
    with open("modules/404.html", "r") as file:
        content = file.read()
    return HTMLResponse(content, status_code=404)

fastapi.mount(
    "/static/login",
    StaticFiles(directory=os.path.join("modules", "login", "static")),
    name="register_static"
)

# Fake to the browser's that /favicon.ico exists
@fastapi.get("/favicon.ico", include_in_schema=False)
async def favicon():
    image_path = "favicon.png"
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            return HTMLResponse(content=image_file.read(), media_type="image/png")
    else:
        raise FileNotFoundError("No favicon.png found")

@fastapi.get("/")
async def show_login_or_browser(request: Request, user = Depends(get_user)):
    logbook.info(f"IP {request.client.host} accessed the root route.")

    if user['token'] == None or user['username'] is None:
        # Route to login
        result = await login_route(request)
    else:
        # Route to the app browser
        result = await apps_route(request)

    return result

modules_dir = "modules"
disabled_modules = []

loaded_routers = set()
mounted_statics = set()
checked_route_modules = set()
loaded_middlewares = set()

for root, dirs, files in os.walk(modules_dir):
    rel_path = os.path.relpath(root, modules_dir)
    if rel_path == ".":
        continue

    module_parts = rel_path.split(os.sep)
    top_level_module = module_parts[0]

    if top_level_module in disabled_modules:
        logbook.info(f"[!] Skipping disabled module: {top_level_module}")
        dirs[:] = []
        continue

    if "__pycache__" in module_parts:
        continue

    # Static Mounting
    static_path = os.path.join(root, "static")
    if os.path.isdir(static_path):
        mount_key = rel_path.replace(os.sep, "/")
        if mount_key not in mounted_statics:
            mount_path = f"/static/{mount_key}"
            fastapi.mount(
                mount_path,
                StaticFiles(directory=static_path),
                name=f"{mount_key}_static"
            )
            mounted_statics.add(mount_key)
            logbook.info(f"[✓] Mounted static files for {mount_key} at {mount_path}")

    # Middleware Handling
    if top_level_module == "middleware" and "middleware.py" in files:
        module_import_path = "modules." + ".".join(module_parts) + ".middleware"

        if module_import_path not in loaded_middlewares:
            try:
                module = importlib.import_module(module_import_path)

                if hasattr(module, "middleware"):
                    fastapi.middleware("http")(module.middleware)
                    loaded_middlewares.add(module_import_path)
                    logbook.info(f"[✓] Loaded middleware from {module_import_path}")
                else:
                    logbook.info(f"[!] No 'middleware' callable in {module_import_path}")

            except Exception as err:
                logbook.error(
                    f"[✗] Failed to load middleware {module_import_path}: {err}",
                    exception=err
                )

        continue  # don't also try to treat middleware as router

    # Router Handling
    if "routes.py" in files:
        module_import_path = "modules." + ".".join(module_parts) + ".routes"

        if module_import_path in checked_route_modules:
            continue

        checked_route_modules.add(module_import_path)

        try:
            module = importlib.import_module(module_import_path)
            if hasattr(module, "router"):
                fastapi.include_router(module.router)
                loaded_routers.add(module_import_path)
                logbook.info(f"[✓] Loaded router from {module_import_path}")
            else:
                logbook.info(f"[!] No 'router' found in {module_import_path}")
        except Exception as err:
            logbook.error(
                f"[✗] Failed to load {module_import_path}: {err}",
                exception=err
            )

def is_running_as_sudo():
    """
    Specifically for checking if we can run certbot without problems.
    """
    if os.name != "nt":
        return os.geteuid() == 0
    return -1

if __name__ == "__main__":
    # The forcekey should never be revealed.
    FORCE_KEY = secrets.token_urlsafe(16)
    print(f"THE FORCE KEY FOR THIS SESSION IS: {FORCE_KEY}")

    # Save it for use elsewhere
    with open('forcekey', 'w') as f:
        f.write(FORCE_KEY)

    if settings.get.use_ssl() is True:
        ssl_keyfile_dir, ssl_certfile_dir = get_ssl_filepaths()
        setup_ssl = not (os.path.exists(ssl_certfile_dir) and os.path.exists(ssl_keyfile_dir))

        if setup_ssl:
            if settings.get.domain() is not None:
                logbook.info(f"Running server under domain {settings.get.domain()}")

            print("To setup server certificates, do you want to use certbot? (Recommended) (y/n)")
            use_certbot = input(">>> ") == "y"

            if use_certbot:
                is_sudo = is_running_as_sudo()
                continue_certbot = False
                if not is_sudo:
                    raise PermissionError("We need sudo to setup certbot certificates. Please run as sudo.")
                elif is_sudo == -1:
                    print("Certbot is only available on Linux systems. Defaulting to self-signed certificates.")
                    setup_selfsigned()
                else:
                    continue_certbot = True

                if continue_certbot:
                    setup_certbot_ssl()
            else:
                setup_selfsigned()
    else:
        ssl_certfile_dir = None
        ssl_keyfile_dir = None

    config = uvicorn.Config(
        "knowledge:fastapi",
        host="0.0.0.0",
        port=WEB_PORT,
        loop="asyncio",
        lifespan="on",
        reload=True,
        ssl_certfile=ssl_certfile_dir,
        ssl_keyfile=ssl_keyfile_dir
    )
    server = uvicorn.Server(config)

    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("Interrupt signal detected, Stopping server and shutting down.")
