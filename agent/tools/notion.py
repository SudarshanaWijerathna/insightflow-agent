"""
Notion tool implementation.
Creates rich study/meeting pages with Markdown content, callouts, and Mermaid diagrams.
Provides graceful fallback if Notion API token is missing or network fails.
"""
from __future__ import annotations

import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from config import settings


def _markdown_to_notion_blocks(markdown_text: str, mermaid_blocks: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Convert simple markdown lines and mermaid diagrams to Notion API block format."""
    blocks: List[Dict[str, Any]] = []
    
    # Callout header
    blocks.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{
                "type": "text",
                "text": {"content": "⚡ Auto-dispatched by InsightAgent • Autonomous Lecture & Meeting Assistant"}
            }],
            "icon": {"emoji": "🤖"}
        }
    })

    # Paragraphs / headings
    for line in markdown_text.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": trimmed[2:].strip()[:2000]}}]}
            })
        elif trimmed.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": trimmed[3:].strip()[:2000]}}]}
            })
        elif trimmed.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": trimmed[4:].strip()[:2000]}}]}
            })
        elif trimmed.startswith("- ") or trimmed.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": trimmed[2:].strip()[:2000]}}]}
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": trimmed[:2000]}}]}
            })

    # Append Mermaid diagrams as code blocks
    if mermaid_blocks:
        for idx, diagram in enumerate(mermaid_blocks):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": f"📊 Architecture / Flow Diagram {idx+1}"}}]}
            })
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "language": "mermaid",
                    "rich_text": [{"type": "text", "text": {"content": diagram[:2000]}}]
                }
            })

    # Limit Notion children array to max 100 blocks per request
    return blocks[:95]


async def create_notion_document(
    title: str,
    markdown_content: str,
    mermaid_blocks: Optional[List[str]] = None,
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new page in Notion.
    Falls back cleanly to a local artifact file if unconfigured or unreachable.
    """
    token = settings.NOTION_API_KEY.strip()
    target_parent = parent_id or settings.NOTION_PAGE_ID.strip()

    if not token or not target_parent or settings.MOCK_INTEGRATIONS_IF_UNCONFIGURED and not token:
        # Graceful fallback: write local markdown artifact
        backup_dir = Path("artefacts/notion")
        backup_dir.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        file_path = backup_dir / f"{safe_title}_{int(datetime.now().timestamp())}.md"
        
        full_content = f"# {title}\n\n" + markdown_content
        if mermaid_blocks:
            for b in mermaid_blocks:
                full_content += f"\n\n```mermaid\n{b}\n```\n"
        
        file_path.write_text(full_content, encoding="utf-8")

        return {
            "status": "fallback",
            "provider": "notion_local_fallback",
            "page_id": f"notion_mock_{int(datetime.now().timestamp())}",
            "url": f"https://notion.so/insightflow/{safe_title.replace(' ', '-')}",
            "title": title,
            "backup_file": str(file_path),
            "message": "Notion API key not set or mocked; document saved to local backup artifact."
        }

    # Real Notion API request
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    blocks = _markdown_to_notion_blocks(markdown_content, mermaid_blocks)

    payload = {
        "parent": {"page_id": target_parent},
        "properties": {
            "title": {
                "title": [{"text": {"content": title[:100]}}]
            }
        },
        "children": blocks
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post("https://api.notion.com/v1/pages", json=payload, headers=headers)
            if resp.status_code in (200, 201):
                data = resp.json()
                page_id = data.get("id")
                url = data.get("url")
                return {
                    "status": "success",
                    "provider": "notion",
                    "page_id": page_id,
                    "url": url,
                    "title": title
                }
            else:
                return {
                    "status": "fallback",
                    "provider": "notion",
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}",
                    "url": f"https://notion.so/insightflow/fallback-{int(datetime.now().timestamp())}",
                    "title": title
                }
    except Exception as e:
        return {
            "status": "fallback",
            "provider": "notion",
            "error": str(e),
            "url": f"https://notion.so/insightflow/fallback-{int(datetime.now().timestamp())}",
            "title": title
        }
