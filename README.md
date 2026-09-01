# Xperi RevGuard

> Catch campaign problems before they become revenue problems.

Xperi RevGuard is an AI-assisted Campaign Health & Revenue Protection platform designed for advertising and ad-operations organizations. It transforms technical campaign signals into prioritized business intelligence, estimating revenue at risk and providing actionable next steps.

## The Problem

Campaign problems (like targeting restrictions, VAST errors, or inventory shortages) are often discovered *after* they have already affected delivery and revenue. Operators must manually sift through multiple systems to correlate pacing drops with technical errors.

## The Solution

Instead of saying "Campaign X is underdelivering," Xperi RevGuard says:
> "Campaign X is underdelivering by 38%. Targeting restriction is the strongest suspected cause. Estimated revenue at risk: $24.3K. Recommended action: Review Roku targeting."

**Core Flow:**
Monitor -> Detect -> Diagnose -> Quantify Impact -> Recommend Action

## Architecture & Tech Stack

The repository is split into two standalone applications:

- `frontend/`: Next.js 14 application, Tailwind UI, charts, and the local API proxy.
- `backend/`: FastAPI application, deterministic analytics, seeded mock data, simulation, and tests.

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **Backend**: Python 3.11, FastAPI, Pydantic, numpy, pandas
- **Data**: Deterministic seeded mock data (Demo Mode)

## Features (Prototype)

- **Executive Overview Dashboard**: Prioritized "Needs Attention" queue ranked by business impact.
- **Campaign Health Table**: Filterable and searchable monitoring of all campaigns.
- **AI Diagnosis Engine (Mocked)**: Correlates multiple signals (VAST, Pacing, Fill) into a natural language explanation.
- **Revenue at Risk Calculation**: Converts impression gaps into dollar figures using CPMs.
- **Investigation Workflow**: Timeline of events leading up to an anomaly.
- **Simulated Integrations**: One-click JIRA ticket creation and Slack alerts.
- **Guardian AI Copilot**: Context-aware chat panel to query campaign health.

## How to Run

1. Start the API in one terminal:
	```bash
	cd backend
	source .venv/bin/activate
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
	```
2. Start the frontend in a second terminal:
	```bash
	cd frontend
	npm run dev
	```
3. Open [http://localhost:3000](http://localhost:3000). The Next.js rewrite proxies `/api/*` requests to the local FastAPI server.

*Note: The application starts in "Demo Mode" with simulated data to ensure 100% reliability during the hackathon presentation.*

## Hackathon Demo Script (< 5 Minutes)

1. **Dashboard (0:00-1:00)**: Start on the Executive Overview. Emphasize that we monitor 200+ campaigns but only surface the 5 that matter right now.
2. **Prioritization (1:00-1:30)**: Point out the "Revenue At Risk" column. We aren't sorting by technical severity; we are sorting by business impact.
3. **Investigation (1:30-3:00)**: Click into "Acme Sports CTV". Show the delivery chart where expected and actual diverged. Scroll to the "AI Diagnosis" and read the natural language explanation. Emphasize: *This takes technical signals and translates them for business users.*
4. **Action (3:00-4:00)**: Show the "Recommended Action". Click "Create Incident" (JIRA mock) or "Slack" (from the incident center) to show how quickly an operator can act on this intelligence.
5. **Conclusion (4:00-5:00)**: "Instead of finding problems after revenue is lost, Xperi RevGuard helps teams identify, understand, and prioritize problems earlier."

## Limitations & Future Integrations

- **Data Sources**: Currently using deterministic mock data. Production versions would connect to GAM, SpringServe, and data lakes (Athena/Snowflake).
- **AI Engine**: Currently uses a deterministic rule-engine simulation. Production would route alerts to an LLM (e.g., Gemini) with specific context payloads for summarization.
- **Alerting**: Production would require OAuth integrations with Slack and Atlassian.

## Hackathon Idea Mapping

Xperi RevGuard is a unified platform that solves and combines functionality from multiple seed ideas:

- **#6 Underdelivery Early-Warning Agent**: Core of the system — campaign monitoring, anomaly detection, health scoring, root-cause analysis, prioritized incidents.
- **#8 Anomaly Detection with LLM Narratives**: Statistical anomaly detection + AI-generated explanation backed by evidence.
- **#14 Bid Request Signal Auditor**: Supply-health analysis, inventory degradation and supply-related diagnosis.
- **#15 VAST Error Triage Copilot**: VAST error monitoring, VAST-related root-cause analysis and remediation recommendations.
- **#5 Campaign Performance Chatbot**: The RevGuard Copilot can answer campaign/risk/performance questions.
- **#1, #2, #3, #9, #17, #18**: The architecture supports these as natural extensions (e.g., mock supply layers represent #2, warehouse data mocks represent #3, and the Copilot sets the foundation for #17/#18).
