# ⚡ InsightAgent: The Autonomous Multi-App Dispatcher

> **Built for the Multi-App Agent Hackathon (September 2026)**  
> Autonomously transforms raw meeting & lecture recordings into structured knowledge, GitHub issues, and Slack digests across **Notion**, **GitHub**, and **Slack**.

---

## 🌟 Overview

When team meetings or university lectures conclude, high-value decisions, action items, and technical context often get lost in 60-minute recordings. 

**InsightAgent** solves this by pairing:
1. **InsightFlow's Multimodal Engine**: Local-first transcription, Gemini multimodal note generation, and Mermaid diagram synthesis.
2. **Gemini 2.5 Function-Calling Agent Loop**: An autonomous dispatcher with tool schemas for Notion, GitHub, and Slack that plans and executes cross-platform workflows.
3. **Resilient Two-Tier Fallback Hierarchy**: Guarantees zero unhandled failures even if third-party tokens expire, rate limits trigger, or network connectivity drops.

---

## 🏗️ Architecture

```
                                  ┌───────────────────────────┐
                                  │  Lecture / Meeting Audio  │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │  InsightFlow Intelligence  │
                                  │  • AssemblyAI STT         │
                                  │  • Action Item Extractor  │
                                  │  • Mermaid Diagram Synthes│
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │      InsightAgent Core Orchestrator          │
                         │    (Gemini 2.5 Function-Calling Loop)        │
                         └──────┬───────────────┬───────────────┬───────┘
                                │               │               │
                                ▼               ▼               ▼
                       ┌────────────────┐┌──────────────┐┌──────────────┐
                       │     Notion     ││ GitHub Issues││    Slack     │
                       │  • Formatted   ││ • Timestamped││ • Block Kit  │
                       │    Notes &     ││   Tasks &    ││   Executive  │
                       │    Mermaid     ││   Labels     ││   Digest     │
                       └────────────────┘└──────────────┘└──────────────┘
```

---

## 🚀 Quickstart

### 1. Installation

```bash
# Clone or enter repository
cd insightflow-agent

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 2. Run Interactive Demo (Zero Configuration Required)

InsightAgent includes built-in mock resilience, allowing full demonstration even before setting up API keys:

```bash
python main.py --demo
```

### 3. Run Benchmark Evaluation Suite

Execute the 5-scenario evaluation suite to verify accuracy, tool coverage, and reliability:

```bash
python main.py --eval
```

### 4. Start API Server

```bash
python main.py --port 8010
```
Interactive Swagger docs available at: `http://localhost:8010/docs`

---

## 📊 Evaluation & Reliability

See [reliability_brief.md](file:///c:/Users/User/Projects/insightflow/insightflow-agent/reliability_brief.md) for the complete architecture breakdown addressing the hackathon's **25% Reliability & Evaluation** criterion.
