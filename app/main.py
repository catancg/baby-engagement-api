from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.routers.health import router as health_router
from app.routers.signup import router as signup_router
from app.routers.unsubscribe import router as unsubscribe_router
from app.routers.admin import router as admin_router
app = FastAPI(title="Baby Store Engagement API")

app.include_router(health_router)
app.include_router(signup_router)
app.include_router(unsubscribe_router)
app.include_router(admin_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/join")
def join():
    return FileResponse(Path("app/static/join.html"))