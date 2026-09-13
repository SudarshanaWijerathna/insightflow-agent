"""
Evaluation metrics for InsightAgent.
Calculates objective scores for Tool Calling Accuracy, Action Item Extraction Recall,
and System Reliability.
"""
from typing import Dict, Any, List
from schemas.models import AgentRunResult


def evaluate_run(scenario: Dict[str, Any], result: AgentRunResult) -> Dict[str, Any]:
    """Score a single agent run against scenario benchmarks."""
    expected_apps = set(scenario.get("expected_target_apps", ["notion", "github", "slack"]))
    min_actions = scenario.get("expected_min_action_items", 1)

    # 1. Tool Call Coverage
    executed_tools = {rec.tool_name for rec in result.tools_executed}
    tool_app_mapping = {
        "create_notion_document": "notion",
        "create_github_issues_batch": "github",
        "send_slack_notification": "slack"
    }
    covered_apps = {tool_app_mapping[t] for t in executed_tools if t in tool_app_mapping}
    
    app_coverage_pct = (len(covered_apps.intersection(expected_apps)) / len(expected_apps)) * 100.0 if expected_apps else 100.0

    # 2. Action Items Count
    github_issues = result.artefacts.get("github_issues", [])
    action_items_found = len(github_issues)
    action_item_score = min(100.0, (action_items_found / min_actions) * 100.0) if min_actions > 0 else 100.0

    # 3. Reliability & Fallback Gracefulness
    failed_tools = [rec for rec in result.tools_executed if rec.status == "failed"]
    fallback_tools = [rec for rec in result.tools_executed if rec.status == "fallback"]
    success_tools = [rec for rec in result.tools_executed if rec.status == "success"]

    if failed_tools:
        reliability_score = max(0.0, 100.0 - (len(failed_tools) * 33.3))
    else:
        reliability_score = 100.0

    # 4. Overall Weighted Score (40% Coverage, 30% Extraction, 30% Reliability)
    overall_score = (app_coverage_pct * 0.40) + (action_item_score * 0.30) + (reliability_score * 0.30)

    return {
        "scenario_id": scenario.get("id"),
        "scenario_name": scenario.get("name"),
        "overall_score": round(overall_score, 1),
        "app_coverage_pct": round(app_coverage_pct, 1),
        "action_items_found": action_items_found,
        "action_items_expected_min": min_actions,
        "action_item_score": round(action_item_score, 1),
        "reliability_score": round(reliability_score, 1),
        "latency_ms": round(result.total_duration_ms, 1),
        "tools_success_count": len(success_tools),
        "tools_fallback_count": len(fallback_tools),
        "tools_failed_count": len(failed_tools),
        "passed": overall_score >= 80.0
    }
