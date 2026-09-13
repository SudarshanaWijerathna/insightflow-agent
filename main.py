"""
InsightAgent — Autonomous Multi-App Dispatcher for Lectures & Meetings.
Entry point for FastAPI server and CLI runner.
"""
import sys
import asyncio
import argparse

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings
from api.routes import router as api_router
from evals.runner import run_all_evals
from agent.runner import AgentRunner
from schemas.models import AgentJobRequest


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=settings.APP_VERSION,
    description="Autonomous Multi-App Agent Dispatcher for Notion, GitHub, and Slack."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(api_router)

from pathlib import Path
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the built-in InsightAgent Web Dashboard."""
    html_path = Path(__file__).resolve().parent / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>InsightAgent API</h1><p>Visit <a href='/docs'>/docs</a> for API documentation.</p>")


async def run_demo():
    """Run a quick terminal demonstration."""
    print("\n" + "=" * 60)
    print("🤖 RUNNING INSIGHTAGENT INTERACTIVE DEMO")
    print("=" * 60)
    
    runner = AgentRunner()
    sample_transcript = (
        "[00:00] Alice: Welcome to the InsightFlow Architecture Sync.\n"
        "[00:20] Bob: I investigated the AssemblyAI key rotation bug. The fix is to add backoff retries when all slots are occupied.\n"
        "[00:50] Alice: Great Bob, open a GitHub issue with high priority for the AssemblyAI backoff queue.\n"
        "[01:15] Charlie: I will update the Notion integration documentation to show how webhook fallbacks work.\n"
        "[01:40] Alice: Thanks team. Please broadcast our sprint progress to #general on Slack."
    )
    
    req = AgentJobRequest(
        title="InsightFlow Architecture & Reliability Sync",
        transcript_text=sample_transcript,
        target_apps=["notion", "github", "slack"]
    )
    
    print("\n▶ Ingesting transcript and dispatching to Notion, GitHub, and Slack...")
    result = await runner.run(req)
    
    print("\n✅ Agent Run Completed!")
    print(f"Job ID: {result.job_id}")
    print(f"Status: {result.status}")
    print(f"Latency: {result.total_duration_ms:.1f}ms")
    print(f"Tools Executed: {len(result.tools_executed)}")
    for t in result.tools_executed:
        print(f"  • {t.tool_name} -> {t.status.upper()} ({t.duration_ms:.1f}ms)")
        
    print("\nArtefacts Created:")
    for k, v in result.artefacts.items():
        print(f"  • {k}: {v}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="InsightAgent Service & CLI")
    parser.add_argument("--eval", action="store_true", help="Run benchmark evaluation suite")
    parser.add_argument("--demo", action="store_true", help="Run a quick terminal demonstration")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to run FastAPI server")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Host to run FastAPI server")

    args = parser.parse_args()

    if args.eval:
        asyncio.run(run_all_evals())
    elif args.demo:
        asyncio.run(run_demo())
    else:
        print(f"Starting {settings.APP_NAME} on {args.host}:{args.port}...")
        uvicorn.run("main:app", host=args.host, port=args.port, reload=settings.DEBUG)


if __name__ == "__main__":
    main()
