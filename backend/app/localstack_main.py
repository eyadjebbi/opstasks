"""LocalStack ECS entry point that serves the API and built React UI together."""

import os

from fastapi.staticfiles import StaticFiles

from .main import app

frontend_directory = os.getenv("FRONTEND_DIR", "/app/frontend")
app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
