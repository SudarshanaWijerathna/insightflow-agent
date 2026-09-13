"""
Evaluation Runner for InsightAgent.
Runs all benchmark scenarios, evaluates accuracy & reliability,
and outputs formatted results.
"""
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent.runner import AgentRunner
from schemas.models import AgentJobRequest
from evals.metrics import evaluate_run


async def run_all_evals() -> Dict[str, Any]:
    """Execute all scenario evaluations."""
    scenarios_dir = Path(__file__).resolve().parent / "scenarios"
    scenario_files = sorted(scenarios_dir.glob("scenario_*.json"))

    if not scenario_files:
        print("No scenarios found in", scenarios_dir)
        return {"error": "No scenarios found"}

    runner = AgentRunner()
    results = []

    print("=" * 70)
    print(f"🚀 Running InsightAgent Benchmark Evaluation ({len(scenario_files)} scenarios)...")
    print("=" * 70)

    for sf in scenario_files:
        try:
            scenario_data = json.loads(sf.read_text(encoding="utf-8"))
            print(f"\n▶ Evaluating: {scenario_data.get('name')} ({sf.name})...")

            req = AgentJobRequest(
                title=scenario_data.get("title", "Test Run"),
                transcript_text=scenario_data.get("transcript_text", ""),
                target_apps=scenario_data.get("expected_target_apps", ["notion", "github", "slack"])
            )

            run_result = await runner.run(req)
            score_data = evaluate_run(scenario_data, run_result)
            results.append(score_data)

            pass_status = "✅ PASS" if score_data["passed"] else "❌ FAIL"
            print(f"  {pass_status} | Score: {score_data['overall_score']}% | Apps: {score_data['app_coverage_pct']}% | Actions: {score_data['action_items_found']}/{score_data['action_items_expected_min']} | Latency: {score_data['latency_ms']}ms")

        except Exception as e:
            print(f"  ❌ Error running scenario {sf.name}: {e}")
            results.append({
                "scenario_name": sf.stem,
                "overall_score": 0.0,
                "passed": False,
                "error": str(e)
            })

    # Summary Statistics
    passed_count = sum(1 for r in results if r.get("passed"))
    avg_score = sum(r.get("overall_score", 0.0) for r in results) / len(results) if results else 0.0
    avg_latency = sum(r.get("latency_ms", 0.0) for r in results) / len(results) if results else 0.0

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios_total": len(results),
        "scenarios_passed": passed_count,
        "pass_rate_pct": round((passed_count / len(results)) * 100.0, 1) if results else 0.0,
        "average_score": round(avg_score, 1),
        "average_latency_ms": round(avg_latency, 1),
        "results": results
    }

    # Write Markdown Report
    report_file = Path(__file__).resolve().parent / "latest_eval_report.md"
    md_content = f"""# InsightAgent Benchmark Evaluation Report

**Date:** {summary['timestamp']}  
**Pass Rate:** `{summary['pass_rate_pct']}%` ({passed_count}/{len(results)} passed)  
**Average Score:** `{summary['average_score']}/100`  
**Average Latency:** `{summary['average_latency_ms']}ms`  

---

## Scenario Breakdown

| Scenario | Overall Score | App Coverage | Action Items | Reliability | Latency | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for r in results:
        status_icon = "✅ Pass" if r.get("passed") else "❌ Fail"
        md_content += f"| {r.get('scenario_name')} | **{r.get('overall_score', 0)}%** | {r.get('app_coverage_pct', 0)}% | {r.get('action_items_found', 0)} found | {r.get('reliability_score', 0)}% | {r.get('latency_ms', 0)}ms | {status_icon} |\n"

    md_content += """
---
*Automated evaluation suite validating multi-app coverage, action item extraction, and deterministic reliability fallbacks.*
"""
    report_file.write_text(md_content, encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"🏆 EVALUATION COMPLETE: {passed_count}/{len(results)} Passed ({summary['pass_rate_pct']}%) | Avg Score: {summary['average_score']}%")
    print(f"📄 Report written to {report_file}")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    asyncio.run(run_all_evals())
