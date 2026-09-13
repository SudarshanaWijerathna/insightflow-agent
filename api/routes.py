"""
FastAPI routes for InsightAgent API service.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Request
from pathlib import Path
from typing import Dict, Any
import httpx

from schemas.models import AgentJobRequest, AgentRunResult
from agent.runner import AgentRunner
from evals.runner import run_all_evals
from config import settings

router = APIRouter()
runner = AgentRunner()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_model": settings.GEMINI_MODEL,
        "mock_mode": settings.MOCK_INTEGRATIONS_IF_UNCONFIGURED
    }


@router.post("/run", response_model=AgentRunResult)
async def run_agent_job(payload: AgentJobRequest):
    """Run full agent multi-app dispatch workflow."""
    try:
        result = await runner.run(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe")
async def transcribe_media(file: UploadFile = File(...)):
    """Forward uploaded media file to InsightFlow AssemblyAI transcription service."""
    target_url = f"{settings.INSIGHTFLOW_API_URL.rstrip('/')}/agent/transcribe"
    headers = {
        "X-Agent-Key": settings.INSIGHTFLOW_AGENT_KEY
    }
    try:
        async def file_stream():
            await file.seek(0)
            while True:
                chunk = await file.read(65536)
                if not chunk:
                    break
                yield chunk

        # Upload and transcribe timeout: up to 5 minutes
        timeout = httpx.Timeout(connect=20.0, write=300.0, read=300.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            files = {"file": (file.filename, await file.read(), file.content_type or "video/mp4")}
            res = await client.post(target_url, headers=headers, files=files)
            if res.status_code != 200:
                return {
                    "status": "error",
                    "text": "",
                    "error": f"InsightFlow returned HTTP {res.status_code}: {res.text}"
                }
            return res.json()
    except Exception as e:
        return {
            "status": "error",
            "text": "",
            "error": f"Failed to forward to InsightFlow backend: {str(e)}"
        }


@router.post("/summarize")
async def summarize_media(payload: Dict[str, Any]):
    """Forward summary request to InsightFlow main application."""
    target_url = f"{settings.INSIGHTFLOW_API_URL.rstrip('/')}/agent/summarize"
    headers = {
        "X-Agent-Key": settings.INSIGHTFLOW_AGENT_KEY,
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(target_url, headers=headers, json=payload)
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=res.text)
            return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"InsightFlow summary failed: {str(e)}")


@router.post("/chat")
async def chat_with_media(payload: Dict[str, Any]):
    """Forward chat query to InsightFlow main application."""
    target_url = f"{settings.INSIGHTFLOW_API_URL.rstrip('/')}/agent/chat"
    headers = {
        "X-Agent-Key": settings.INSIGHTFLOW_AGENT_KEY,
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(target_url, headers=headers, json=payload)
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=res.text)
            return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"InsightFlow chat failed: {str(e)}")


@router.post("/eval")
async def trigger_evals():
    """Trigger the 5-scenario evaluation suite."""
    try:
        report = await run_all_evals()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eval/latest")
async def get_latest_eval():
    """Retrieve the latest evaluation report content."""
    report_file = Path(__file__).resolve().parent.parent / "evals" / "latest_eval_report.md"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="No evaluation report found. Run /eval first.")
    return {"markdown": report_file.read_text(encoding="utf-8")}

