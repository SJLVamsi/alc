from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.browser import browser_service
from app.services.course_navigator import course_navigator
from app.core.logging import logger

router = APIRouter(prefix="/api/automation", tags=["automation"])


class NavigateRequest(BaseModel):
    url: str


class ContentResponse(BaseModel):
    title: str
    text: str


@router.post("/start")
async def start_browser():
    try:
        await browser_service.start()
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_browser():
    await browser_service.close()
    return {"status": "stopped"}


@router.post("/navigate")
async def navigate(req: NavigateRequest):
    try:
        await browser_service.navigate(req.url)
        return {"status": "navigated", "url": req.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content", response_model=ContentResponse)
async def get_content():
    try:
        content = await course_navigator.extract_lesson_content()
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect-completion")
async def detect_completion():
    try:
        completed = await course_navigator.detect_lesson_completion()
        return {"completed": completed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/next-lesson")
async def next_lesson():
    try:
        url = await course_navigator.open_next_lesson()
        return {"next_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules")
async def get_modules():
    try:
        modules = await course_navigator.get_module_list()
        return {"modules": modules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
