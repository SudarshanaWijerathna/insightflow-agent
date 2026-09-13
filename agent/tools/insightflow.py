"""
InsightFlow tool client.
Communicates with the InsightFlow backend adapter to fetch transcripts, structured notes,
and action items. Includes smart offline heuristic fallback if the backend server is offline.
"""
from __future__ import annotations

import re
import httpx
from typing import Dict, Any, Optional, List
from config import settings


def _heuristic_extract_action_items(transcript_text: str) -> List[Dict[str, Any]]:
    """Rule-based extractor for when backend or LLM is offline."""
    items = []
    lines = transcript_text.splitlines()
    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        
        match_ts = re.search(r'\[(\d+):(\d+)\]', cleaned)
        ts_sec = 0.0
        if match_ts:
            ts_sec = float(match_ts.group(1)) * 60 + float(match_ts.group(2))
        
        lower = cleaned.lower()
        if any(cue in lower for cue in [
            "action item", "open a github issue", "open an issue", "will begin", "will fix", 
            "will implement", "can you add", "can you update", "homework assignment", 
            "due this", "update our runbook", "update the api", "file an issue", "track the"
        ]):
            speaker = None
            speaker_match = re.search(r'\]\s*([A-Za-z]+(?:\s*\([^\)]+\))?):', cleaned)
            if speaker_match:
                speaker = speaker_match.group(1).split()[0]

            title_text = cleaned
            if speaker_match:
                title_text = cleaned[speaker_match.end():].strip()
            elif match_ts:
                title_text = cleaned[match_ts.end():].strip()

            title_text = re.sub(r'^(?:(?:first|second|third|fourth)\s+)?action item(?:\s+for\s+[a-z]+)?:?\s*', '', title_text, flags=re.IGNORECASE)
            title_text = re.sub(r'^(?:I will\s*|Please\s*)', '', title_text, flags=re.IGNORECASE).strip()
            title_text = title_text[:80].capitalize()
            if title_text.endswith('.'):
                title_text = title_text[:-1]

            labels = ["action-item"]
            if any(w in lower for w in ["database", "index", "postgres", "sql"]):
                labels.append("database")
            if any(w in lower for w in ["backend", "api", "redis", "ttl"]):
                labels.append("backend")
            if any(w in lower for w in ["frontend", "ux", "ui", "css", "component"]):
                labels.append("frontend")
            if any(w in lower for w in ["alert", "cert", "security", "p0", "auth", "outage"]):
                labels.append("security")
            if any(w in lower for w in ["homework", "lecture", "student", "algorithm"]):
                labels.append("homework")
            if any(w in lower for w in ["docs", "documentation", "guide", "runbook"]):
                labels.append("docs")

            items.append({
                "title": title_text or "Follow-up deliverable",
                "description": cleaned,
                "timestamp": ts_sec,
                "context_text": cleaned,
                "suggested_labels": labels,
                "assignee_hint": speaker,
                "priority": "high" if any(w in lower for w in ["p0", "p1", "urgent", "critical"]) else "medium"
            })
    
    if not items:
        items = [{
            "title": "Review lecture materials & action items",
            "description": "Follow up on key technical decisions discussed.",
            "timestamp": 0.0,
            "suggested_labels": ["general"],
            "priority": "medium"
        }]
    return items


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
                raw_text = transcript_text or ""
                return {
                    "status": "fallback",
                    "source": "http_error",
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "notes_markdown": f"# {title}\n\nProcessed locally via fallback.",
                    "action_items": _heuristic_extract_action_items(raw_text),
                    "mermaid_blocks": []
                }
    except Exception as e:
        # Fallback if InsightFlow server is offline during evaluation/mocking
        raw_text = transcript_text or ""
        return {
            "status": "fallback",
            "source": "local_resilience",
            "error": str(e),
            "title": title,
            "transcript_text": raw_text,
            "notes_markdown": f"# {title}\n\n## Summary\n{(raw_text or 'No transcript provided')[:600]}...",
            "action_items": _heuristic_extract_action_items(raw_text),
            "mermaid_blocks": [
                "graph TD;\n  A[Meeting] --> B[Notes Created];\n  B --> C[Tasks Dispatched];"
            ]
        }
