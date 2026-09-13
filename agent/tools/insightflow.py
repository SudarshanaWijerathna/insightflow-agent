"""
InsightFlow tool client.
Communicates with the InsightFlow backend adapter to fetch transcripts, structured notes,
and action items.
"""
from __future__ import annotations

import httpx
from typing import Dict, Any, Optional, List
from config import settings


async def call_insightflow_pipeline(
    title: str,
    audio_url: Optional[str] = None,
    transcript_text: Optional[str] = None,
    transcript_segments: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Call InsightFlow /agent/process endpoint.
    If server is unreachable, falls back to a graceful local mock representation.
    """
    url = f"{settings.INSIGHTFLOW_API_URL.rstrip('/')}/agent/process"
    headers = {
        "X-Agent-Key": settings.INSIGHTFLOW_AGENT_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "title": title,
        "audio_url": audio_url,
        "transcript_text": transcript_text,
        "transcript_segments": transcript_segments
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "source": "insightflow_api",
                    "job_id": data.get("job_id"),
                    "title": data.get("title", title),
                    "transcript_text": data.get("transcript_text", transcript_text or ""),
                    "notes_markdown": data.get("notes_markdown", ""),
                    "action_items": data.get("action_items", []),
                    "mermaid_blocks": data.get("mermaid_blocks", []),
                    "duration_seconds": data.get("duration_seconds", 0.0)
                }
            else:
                return {
                    "status": "fallback",
                    "source": "http_error",
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "notes_markdown": f"# {title}\n\nProcessed locally via fallback.",
                    "action_items": [],
                    "mermaid_blocks": []
                }
    except Exception as e:
        # Fallback if InsightFlow server is offline during evaluation/mocking
        return {
            "status": "fallback",
            "source": "local_resilience",
            "error": str(e),
            "title": title,
            "transcript_text": transcript_text or "",
            "notes_markdown": f"# {title}\n\n## Summary\n{(transcript_text or 'No transcript provided')[:600]}...",
            "action_items": [
                {
                    "title": "Review lecture materials & action items",
                    "description": "Follow up on key technical decisions discussed.",
                    "timestamp": 0.0,
                    "suggested_labels": ["general"],
                    "priority": "medium"
                }
            ],
            "mermaid_blocks": [
                "graph TD;\n  A[Meeting] --> B[Notes Created];\n  B --> C[Tasks Dispatched];"
            ]
        }
