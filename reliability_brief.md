# InsightAgent — Reliability & Evaluation Architecture Brief

**Multi-App Agent Hackathon Submission (September 2026)**  
*Target Judging Category: Reliability & Quantitative Evaluation (25% Weight)*

---

## 1. System Philosophy: Zero Unhandled Failures

In real-world multi-app agent deployments, external third-party APIs fail frequently due to:
- Missing or expired user credentials (OAuth/tokens)
- Cloud rate limits (HTTP 429)
- Downstream outages on third-party SaaS platforms
- Network disconnects during long audio/video ingestion

InsightAgent was engineered from day one with a **Two-Tier Resilient Fallback Hierarchy**:

```
                  ┌────────────────────────────────────────┐
                  │ Recording / Video Ingestion Request    │
                  └──────────────────┬─────────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────────┐
                  │ Tier 1: Gemini 2.5 Function-Calling    │
                  │ Dynamic Loop with Tool Declarations    │
                  └──────┬───────────────────────────┬─────┘
                         │                           │
                   (Tool Success)             (Gemini/API Drop)
                         │                           │
                         ▼                           ▼
       ┌──────────────────────────────┐   ┌──────────────────────────────┐
       │ External App Dispatch:       │   │ Tier 2: Deterministic        │
       │ • Notion API (Pages/Blocks)  │   │ Resilient Fallback Queue     │
       │ • GitHub API (Issues/Labels) │   │ • Local Markdown Artifacts   │
       │ • Slack API (Block Kit)      │   │ • Offline Queued Dispatches  │
       └──────────────────────────────┘   └──────────────────────────────┘
```

---

## 2. Multi-App Tool Reliability Matrix

| Platform | Primary Transport | Failure Mode Handled | Resilient Fallback Behavior |
| :--- | :--- | :--- | :--- |
| **Notion** | REST API v1 (`/v1/pages`) | Missing token, 401, rate limit (429), block limit > 100 | Saves structured Markdown + Mermaid diagrams into `artefacts/notion/*.md` and returns local artifact link. |
| **GitHub** | GitHub Issues REST API | Token missing, invalid repo name, rate limit | Writes issues into timestamped `artefacts/github/*.json` and returns reproducible issue payloads. |
| **Slack** | Block Kit (Webhooks / Bot Token) | Missing webhook, invalid channel, network drop | Serializes Block Kit JSON to `artefacts/slack/*.json` and echoes summary to system log. |
| **InsightFlow Engine** | Adapter API (`/agent/process`) | Backend offline, STT service queue full | Embedded heuristic analyzer extracts action items and generates summary without failing job. |

---

## 3. Quantitative Evaluation Suite

InsightAgent includes a native, automated benchmark test suite (`python main.py --eval`) covering 5 distinct domain scenarios:

1. **Engineering Sprint Standup (`scenario_01`)**: Tests technical bug triage, P1 priorities, and database schema migrations.
2. **Computer Science Lecture (`scenario_02`)**: Tests academic homework extraction, complex algorithms (Dijkstra), and student deadlines.
3. **Product Design & UX Review (`scenario_03`)**: Tests UI component deliverables, microcopy edits, and frontend tasks.
4. **Production Incident Postmortem (`scenario_04`)**: Tests security certificate rotations, SRE alerts, and runbook updates.
5. **Ad-hoc Quick Sync (`scenario_05`)**: Tests fast 1-minute conversations with minimal action items.

### Evaluated Metrics

- **Tool Call Coverage:** Ratio of expected target apps successfully invoked (`%`).
- **Action Item Recall:** Ratio of required action items accurately identified (`%`).
- **Reliability Score:** Zero unhandled crashes, factoring in graceful fallbacks (`%`).
- **End-to-End Latency:** Total dispatch time in milliseconds (`ms`).

---

## 4. Reproducing the Evaluation

To execute the benchmark suite and generate the latest score report:

```bash
cd insightflow-agent
python main.py --eval
```

Or trigger programmatically via the API:
```bash
curl -X POST http://localhost:8010/api/eval
```
