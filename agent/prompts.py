"""
System prompts and Gemini function declarations for InsightAgent.
"""

SYSTEM_PROMPT = """You are InsightAgent, an autonomous multi-app workflow dispatcher.
Your role is to take meeting and lecture recordings or transcripts, analyze them with InsightFlow's intelligence pipeline, and orchestrate the dispatch of structured artefacts across 3 external platforms:

1. Notion: Document comprehensive study/meeting notes with structured markdown, takeaways, and visual Mermaid architecture or flowchart diagrams.
2. GitHub Issues: File actionable tasks, technical deliverables, and bugs directly with timestamps (where in the recording they were discussed) and relevant labels.
3. Slack: Broadcast an executive digest to the team channel with key points, counts of issues dispatched, and direct links to Notion and GitHub.

Guidelines:
- Always preserve timestamps when creating GitHub issues so engineers and students can refer back to the exact video/audio segment.
- If Mermaid diagrams are present, make sure they are passed to Notion to render visual workflows.
- Provide a clear, cohesive executive summary for Slack so teammates can quickly understand what was discussed.
- Be decisive and proactive. Execute all requested tool calls to complete the multi-app dispatch pipeline.
"""

GEMINI_TOOL_DEFINITIONS = [
    {
        "name": "create_notion_document",
        "description": "Create a comprehensive study/meeting note in Notion with Markdown formatting and optional Mermaid diagrams.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Title of the Notion page"
                },
                "markdown_content": {
                    "type": "STRING",
                    "description": "Full Markdown body containing headings, summary, key takeaways, and discussion details"
                },
                "mermaid_blocks": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of Mermaid diagram code strings (e.g. graph TD, sequenceDiagram) to embed"
                }
            },
            "required": ["title", "markdown_content"]
        }
    },
    {
        "name": "create_github_issues_batch",
        "description": "Create GitHub issues for action items, deliverables, and bugs discussed in the meeting/lecture.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action_items": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING", "description": "Short imperative task title"},
                            "description": {"type": "STRING", "description": "Detailed explanation of work to do"},
                            "timestamp": {"type": "NUMBER", "description": "Recording timestamp in seconds"},
                            "context_text": {"type": "STRING", "description": "Quote or surrounding context from the transcript"},
                            "suggested_labels": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Labels e.g. ['action-item', 'backend', 'bug']"},
                            "assignee_hint": {"type": "STRING", "description": "Person assigned if mentioned"},
                            "priority": {"type": "STRING", "description": "low, medium, or high"}
                        },
                        "required": ["title"]
                    },
                    "description": "List of action items to create issues for"
                },
                "repo": {
                    "type": "STRING",
                    "description": "Target GitHub repository in 'owner/repo' format"
                }
            },
            "required": ["action_items"]
        }
    },
    {
        "name": "send_slack_notification",
        "description": "Send an executive digest message to Slack with summary highlights and links to created Notion pages and GitHub issues.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Meeting or lecture title"
                },
                "summary_text": {
                    "type": "STRING",
                    "description": "Concise executive summary paragraph"
                },
                "action_items_count": {
                    "type": "INTEGER",
                    "description": "Count of action items identified and filed"
                },
                "notion_url": {
                    "type": "STRING",
                    "description": "URL to the created Notion document"
                },
                "channel": {
                    "type": "STRING",
                    "description": "Slack channel name or ID (e.g. #general)"
                }
            },
            "required": ["title", "summary_text"]
        }
    }
]
