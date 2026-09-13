"""
FastAPI routes for InsightAgent API service.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import Dict, Any

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
