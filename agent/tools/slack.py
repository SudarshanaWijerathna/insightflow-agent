"""
Slack tool implementation.
Sends Block Kit formatted executive summaries and action item notifications to Slack.
Supports both Incoming Webhooks and Bot Token (chat.postMessage) with local fallback.
"""
from __future__ import annotations

import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from config import settings


def _build_slack_blocks(
    title: str,
    summary_text: str,
    action_items_count: int,
    notion_url: Optional[str] = None,
    github_issues: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Build Slack Block Kit structure."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎙️ InsightAgent Digest: {title[:80]}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Executive Summary:*\n{summary_text[:1200]}"
            }
        },
        {"type": "divider"}
    ]

    # Action items callout
    actions_desc = f"📋 *{action_items_count} Action Items* were extracted and dispatched."
    if github_issues:
        actions_desc += f"\n• Tracked in GitHub Issues: {len(github_issues)} created."
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": actions_desc
        }
    })

    # Action buttons / links
    elements = []
    if notion_url:
        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "📖 View Notion Notes", "emoji": True},
            "url": notion_url,
            "style": "primary"
        })

    if elements:
        blocks.append({
            "type": "actions",
            "elements": elements
        })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "⚡ *InsightAgent* Multi-App Autonomous Dispatcher • Powered by InsightFlow & Gemini"
            }
        ]
    })

    return blocks


async def send_slack_notification(
    title: str,
    summary_text: str,
    action_items_count: int = 0,
    notion_url: Optional[str] = None,
    github_issues: Optional[List[Dict[str, Any]]] = None,
    channel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send Slack notification via Webhook or Bot Token.
    Falls back gracefully if Slack credentials are not configured.
    """
    webhook_url = settings.SLACK_WEBHOOK_URL.strip()
    bot_token = settings.SLACK_BOT_TOKEN.strip()
    target_channel = channel or settings.SLACK_DEFAULT_CHANNEL

    blocks = _build_slack_blocks(title, summary_text, action_items_count, notion_url, github_issues)

    # Local Fallback check
    if not webhook_url and not bot_token:
        backup_dir = Path("artefacts/slack")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = int(datetime.now().timestamp())
        file_path = backup_dir / f"slack_message_{timestamp_str}.json"
        
        message_data = {
            "channel": target_channel,
            "text": f"🎙️ InsightAgent Digest: {title}",
            "blocks": blocks,
            "created_at": datetime.now().isoformat()
        }
        file_path.write_text(json.dumps(message_data, indent=2), encoding="utf-8")

        return {
            "status": "fallback",
            "provider": "slack_local_fallback",
            "channel": target_channel,
            "backup_file": str(file_path),
            "blocks_count": len(blocks),
            "message": "Slack credentials not configured; message saved to local backup artifact."
        }

    # If Webhook URL is configured
    if webhook_url:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(webhook_url, json={"blocks": blocks})
                if resp.status_code == 200:
                    return {
                        "status": "success",
                        "provider": "slack_webhook",
                        "channel": target_channel
                    }
                else:
                    return {
                        "status": "fallback",
                        "provider": "slack_webhook",
                        "error": f"HTTP {resp.status_code}: {resp.text[:200]}"
                    }
        except Exception as e:
            return {
                "status": "fallback",
                "provider": "slack_webhook",
                "error": str(e)
            }

    # If Bot Token is configured
    if bot_token:
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    json={"channel": target_channel, "blocks": blocks, "text": f"InsightAgent Digest: {title}"},
                    headers=headers
                )
                data = resp.json()
                if data.get("ok"):
                    return {
                        "status": "success",
                        "provider": "slack_api",
                        "channel": target_channel,
                        "ts": data.get("ts")
                    }
                else:
                    return {
                        "status": "fallback",
                        "provider": "slack_api",
                        "error": data.get("error", "Unknown Slack error")
                    }
        except Exception as e:
            return {
                "status": "fallback",
                "provider": "slack_api",
                "error": str(e)
            }

    return {"status": "failed", "error": "Unable to dispatch to Slack"}
