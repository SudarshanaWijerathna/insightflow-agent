"""
Main AgentRunner for InsightAgent.
Coordinates the Gemini function-calling loop and tool execution.
"""
from __future__ import annotations

import asyncio
import time
import uuid
import httpx
from typing import Dict, Any, List, Optional

from config import settings
from schemas.models import AgentJobRequest, AgentRunResult, ToolExecutionRecord
from agent.prompts import SYSTEM_PROMPT, GEMINI_TOOL_DEFINITIONS
from agent.tools import (
    call_insightflow_pipeline,
    create_notion_document,
    create_github_issues_batch,
    send_slack_notification
)


class AgentRunner:
    """Autonomous agent runner coordinating InsightFlow intelligence and multi-app dispatch."""

    def __init__(self):
        self.tools = {
            "create_notion_document": create_notion_document,
            "create_github_issues_batch": create_github_issues_batch,
            "send_slack_notification": send_slack_notification
        }

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> ToolExecutionRecord:
        """Safely execute an agent tool and track execution metrics."""
        start_t = time.perf_counter()
        fn = self.tools.get(tool_name)
        if not fn:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status="failed",
                inputs=tool_args,
                output={},
                error=f"Unknown tool: {tool_name}",
                duration_ms=(time.perf_counter() - start_t) * 1000
            )

        try:
            result = await fn(**tool_args)
            status = "fallback" if result.get("status") == "fallback" else "success"
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=status,
                inputs=tool_args,
                output=result,
                error=result.get("error"),
                duration_ms=(time.perf_counter() - start_t) * 1000
            )
        except Exception as e:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status="failed",
                inputs=tool_args,
                output={},
                error=str(e),
                duration_ms=(time.perf_counter() - start_t) * 1000
            )

    async def _call_gemini_api(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call Google Gemini generateContent endpoint with function declarations."""
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
        params = {"key": api_key}
        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": contents,
            "tools": [
                {"function_declarations": GEMINI_TOOL_DEFINITIONS}
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()

    async def run(self, request: AgentJobRequest) -> AgentRunResult:
        """Run the end-to-end InsightAgent workflow."""
        start_time = time.perf_counter()
        job_id = f"ia_{uuid.uuid4().hex[:10]}"
        tool_records: List[ToolExecutionRecord] = []
        artefacts: Dict[str, Any] = {}

        # ── Step 1: Intelligence Extraction via InsightFlow ───────────────────
        insightflow_data = await call_insightflow_pipeline(
            title=request.title,
            audio_url=request.audio_url,
            transcript_text=request.transcript_text,
            transcript_segments=[s.model_dump() for s in request.transcript_segments] if request.transcript_segments else None
        )

        notes_markdown = insightflow_data.get("notes_markdown", "")
        action_items = insightflow_data.get("action_items", [])
        mermaid_blocks = insightflow_data.get("mermaid_blocks", [])

        # ── Step 2: Multi-App Dispatch Loop ──────────────────────────────────
        has_gemini = bool(settings.GEMINI_API_KEY.strip())

        if has_gemini:
            try:
                # Build initial user message for the agent
                initial_prompt = (
                    f"Please process and dispatch the following meeting/lecture materials:\n\n"
                    f"Title: {request.title}\n"
                    f"Target Apps: {', '.join(request.target_apps)}\n\n"
                    f"Notes Markdown Summary:\n{notes_markdown[:2500]}\n\n"
                    f"Extracted Action Items ({len(action_items)} total):\n"
                    f"{action_items}\n\n"
                    f"Mermaid Blocks ({len(mermaid_blocks)} total):\n"
                    f"{mermaid_blocks}\n\n"
                    f"Target GitHub Repo: {request.github_repo or settings.GITHUB_REPO}\n"
                    f"Target Slack Channel: {request.slack_channel or settings.SLACK_DEFAULT_CHANNEL}\n\n"
                    f"Dispatch the documentation to Notion, the issues to GitHub, and the summary to Slack."
                )

                contents = [{
                    "role": "user",
                    "parts": [{"text": initial_prompt}]
                }]

                max_turns = 6
                final_summary_text = ""

                for _ in range(max_turns):
                    gemini_resp = await self._call_gemini_api(contents)
                    candidates = gemini_resp.get("candidates", [])
                    if not candidates:
                        break

                    candidate = candidates[0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])

                    function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
                    text_parts = [p["text"] for p in parts if "text" in p]

                    if text_parts:
                        final_summary_text += "\n".join(text_parts)

                    if not function_calls:
                        # Model finished tool calls and returned final answer
                        break

                    # Add model turn to contents
                    contents.append(content)

                    # Execute all function calls emitted in this turn
                    response_parts = []
                    for fc in function_calls:
                        call_name = fc.get("name")
                        call_args = fc.get("args", {})
                        
                        rec = await self._execute_tool(call_name, call_args)
                        tool_records.append(rec)
                        
                        # Store artefacts
                        if call_name == "create_notion_document" and "url" in rec.output:
                            artefacts["notion_url"] = rec.output.get("url")
                        elif call_name == "create_github_issues_batch":
                            artefacts["github_issues"] = rec.output.get("issues_created", [])
                        elif call_name == "send_slack_notification":
                            artefacts["slack_status"] = rec.output.get("status")

                        response_parts.append({
                            "functionResponse": {
                                "name": call_name,
                                "response": {"result": rec.output}
                            }
                        })

                    contents.append({
                        "role": "tool",
                        "parts": response_parts
                    })

            except Exception as loop_err:
                # Graceful deterministic fallback if Gemini call fails
                final_summary_text = f"Agent completed dispatch via deterministic reliability fallback ({loop_err})."
                has_gemini = False

        # If Gemini is not configured or failed, run deterministic reliability fallback
        if not has_gemini:
            # 1. Notion
            if "notion" in request.target_apps:
                rec_notion = await self._execute_tool("create_notion_document", {
                    "title": request.title,
                    "markdown_content": notes_markdown,
                    "mermaid_blocks": mermaid_blocks,
                    "parent_id": request.notion_parent_id
                })
                tool_records.append(rec_notion)
                artefacts["notion_url"] = rec_notion.output.get("url")

            # 2. GitHub
            if "github" in request.target_apps and action_items:
                rec_github = await self._execute_tool("create_github_issues_batch", {
                    "action_items": action_items,
                    "repo": request.github_repo or settings.GITHUB_REPO
                })
                tool_records.append(rec_github)
                artefacts["github_issues"] = rec_github.output.get("issues_created", [])

            # 3. Slack
            if "slack" in request.target_apps:
                rec_slack = await self._execute_tool("send_slack_notification", {
                    "title": request.title,
                    "summary_text": notes_markdown[:600] if notes_markdown else "Meeting completed and notes processed.",
                    "action_items_count": len(action_items),
                    "notion_url": artefacts.get("notion_url"),
                    "channel": request.slack_channel or settings.SLACK_DEFAULT_CHANNEL
                })
                tool_records.append(rec_slack)
                artefacts["slack_status"] = rec_slack.output.get("status")

            final_summary_text = (
                f"Successfully dispatched artefacts for '{request.title}' across "
                f"{len(tool_records)} platforms (Notion, GitHub, Slack)."
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        has_failures = any(r.status == "failed" for r in tool_records)

        return AgentRunResult(
            job_id=job_id,
            status="partial_failure" if has_failures else "completed",
            title=request.title,
            tools_executed=tool_records,
            artefacts=artefacts,
            summary=final_summary_text,
            total_duration_ms=duration_ms
        )
