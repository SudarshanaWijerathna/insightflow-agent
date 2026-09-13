"""
GitHub tool implementation.
Dispatches action items and bugs to GitHub Issues with timestamp references and tags.
Provides graceful fallback if GitHub token is missing or network fails.
"""
from __future__ import annotations

import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from config import settings


def _format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


async def create_github_issues_batch(
    action_items: List[Dict[str, Any]],
    repo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create GitHub issues for each extracted action item.
    """
    token = settings.GITHUB_TOKEN.strip()
    target_repo = repo or settings.GITHUB_REPO.strip()

    results = []

    # Check if mock or real
    if not token or not target_repo or (settings.MOCK_INTEGRATIONS_IF_UNCONFIGURED and not token):
        backup_dir = Path("artefacts/github")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = int(datetime.now().timestamp())
        file_path = backup_dir / f"dispatched_issues_{timestamp_str}.json"

        simulated_issues = []
        for idx, item in enumerate(action_items):
            issue_number = 100 + idx + 1
            ts = item.get("timestamp", 0.0)
            labels = list(set(["action-item"] + item.get("suggested_labels", [])))
            simulated_issues.append({
                "number": issue_number,
                "title": item.get("title", "Action Item"),
                "url": f"https://github.com/{target_repo or 'demo/repo'}/issues/{issue_number}",
                "labels": labels,
                "timestamp": ts,
                "timestamp_formatted": _format_timestamp(ts),
                "assignee": item.get("assignee_hint"),
                "priority": item.get("priority", "medium")
            })

        file_path.write_text(json.dumps(simulated_issues, indent=2), encoding="utf-8")

        return {
            "status": "fallback",
            "provider": "github_local_fallback",
            "repo": target_repo or "demo/repo",
            "issues_created": simulated_issues,
            "backup_file": str(file_path),
            "message": "GitHub token not configured; issues saved to local backup artifact."
        }

    # Real GitHub API calls
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "InsightAgent-Dispatcher"
    }

    url = f"https://api.github.com/repos/{target_repo}/issues"

    async with httpx.AsyncClient(timeout=20.0) as client:
        for idx, item in enumerate(action_items):
            ts = item.get("timestamp", 0.0)
            ts_str = _format_timestamp(ts)
            
            body_content = (
                f"### 🤖 Action Item Dispatched by InsightAgent\n\n"
                f"**Description:**\n{item.get('description', 'No details provided.')}\n\n"
                f"**Media Timestamp:** `{ts_str}` ({ts:.1f}s)\n\n"
            )
            if item.get("context_text"):
                body_content += f"> **Context from recording:**\n> \"{item.get('context_text')}\"\n\n"

            body_content += f"*Priority: `{item.get('priority', 'medium').upper()}`*"

            labels = list(set(["action-item"] + item.get("suggested_labels", [])))

            payload = {
                "title": item.get("title", f"Action item #{idx+1}"),
                "body": body_content,
                "labels": labels
            }
            if item.get("assignee_hint"):
                # If assignee is provided, attempt to assign
                payload["assignees"] = [item.get("assignee_hint")]

            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 201:
                    data = resp.json()
                    results.append({
                        "number": data.get("number"),
                        "title": data.get("title"),
                        "url": data.get("html_url"),
                        "labels": labels,
                        "status": "created"
                    })
                else:
                    results.append({
                        "title": item.get("title"),
                        "error": f"HTTP {resp.status_code}: {resp.text[:150]}",
                        "status": "failed"
                    })
            except Exception as ex:
                results.append({
                    "title": item.get("title"),
                    "error": str(ex),
                    "status": "failed"
                })

    return {
        "status": "success",
        "provider": "github",
        "repo": target_repo,
        "issues_created": results
    }
