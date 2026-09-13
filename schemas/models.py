"""
Pydantic data models for InsightAgent.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ActionItem(BaseModel):
    title: str = Field(..., description="Action item title")
    description: str = Field("", description="Detailed explanation")
    timestamp: float = Field(0.0, description="Timestamp in seconds from media")
    context_text: str = Field("", description="Context or quote from transcript")
    suggested_labels: List[str] = Field(default_factory=list, description="Labels e.g. bug, feature, docs")
    assignee_hint: Optional[str] = Field(None, description="Person assigned")
    priority: Literal["low", "medium", "high"] = Field("medium", description="Priority level")


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class AgentJobRequest(BaseModel):
    title: str = Field("Meeting Recording", description="Title of lecture or meeting")
    audio_url: Optional[str] = Field(None, description="Audio/video file URL or R2 object key")
    transcript_text: Optional[str] = Field(None, description="Raw transcript text")
    transcript_segments: Optional[List[TranscriptSegment]] = Field(None, description="Diarized segments")
    target_apps: List[str] = Field(default_factory=lambda: ["notion", "github", "slack"], description="Apps to dispatch to")
    github_repo: Optional[str] = Field(None, description="Target GitHub repo (owner/repo)")
    slack_channel: Optional[str] = Field(None, description="Target Slack channel")
    notion_parent_id: Optional[str] = Field(None, description="Notion database or parent page ID")


class ToolExecutionRecord(BaseModel):
    tool_name: str
    status: Literal["success", "fallback", "failed"]
    inputs: Dict[str, Any]
    output: Dict[str, Any]
    error: Optional[str] = None
    duration_ms: float = 0.0


class AgentRunResult(BaseModel):
    job_id: str
    status: Literal["completed", "partial_failure", "failed"]
    title: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tools_executed: List[ToolExecutionRecord] = Field(default_factory=list)
    artefacts: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    total_duration_ms: float = 0.0
