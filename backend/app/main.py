from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.logging import setup_logging, logger
from app.core.exceptions import ALCException
from app.config import settings
from app.database import engine, Base
from app.api.routes import (
    automation, courses, lessons, notes,
    flashcards, coding, mcq, analytics, extension, page,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    Base.metadata.create_all(bind=engine)
    logger.info("application_started", model=settings.ollama_model)
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="AI Learning Copilot",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # "*" covers content-script fetches, which carry the host page's origin
    # (chrome-extension://<id> and http://localhost:3000 included).
    # No credentials are used, so a wildcard is a valid CORS response.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(ALCException)
async def alc_exception_handler(request: Request, exc: ALCException):
    logger.error("application_error", error=str(exc))
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/api/health")
async def health():
    return {"status": "healthy", "model": settings.ollama_model}


app.include_router(automation.router)
app.include_router(courses.router)
app.include_router(lessons.router)
app.include_router(notes.router)
app.include_router(flashcards.router)
app.include_router(coding.router)
app.include_router(mcq.router)
app.include_router(analytics.router)
app.include_router(extension.router)
app.include_router(page.router)
