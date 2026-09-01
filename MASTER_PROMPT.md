# 🛡️ REVENUE GUARDIAN 

You are building **Revenue Guardian** — an AI-powered revenue protection system for ad operations.

**Ground rules for the agent:**
1. Build in the phase order given in §19. After each phase, the app must **run and be demoable**.
2. Everything runs **100% locally with mock data**. No cloud credentials required. Ever.
3. If an LLM API key is absent, the AI layer must **transparently fall back** to a deterministic reasoning engine that produces identical-shaped output. The demo must never break.
4. Do not invent metrics in the UI. Every number rendered must trace back to a computed field from the backend.
5. Prefer boring, reliable code. This is a demo that must survive a live audience.

**Existing state of the repo:** a Next.js 14 + TypeScript + Tailwind + Recharts frontend with 5 pages and in-memory mock data, no backend. You will **keep the design language**, rebuild the data layer to be API-driven, and add the Python backend.

---

## §1. THE MISSION

**One sentence (memorize this):**

> Revenue Guardian is an AI-powered revenue protection system that continuously monitors campaign and supply signals, detects delivery anomalies, identifies their likely root cause, quantifies the revenue at risk, recommends corrective action, and tracks whether that action actually recovered the threatened revenue.

**The six-step north star.** Every feature must serve one of these:

```
DETECT → DIAGNOSE → QUANTIFY → RECOMMEND → ACT → MEASURE
```

**The pain point being solved:** today an underdelivering campaign is discovered by a human, hours or days late, after checking pacing, targeting, line items, inventory, creatives, VAST errors, supply, and competing campaigns by hand. By then the revenue is gone.

---

## §2. THE NON-NEGOTIABLE ARCHITECTURAL PRINCIPLE

There are **two kinds of intelligence** in this system and they must live in separate modules.

### Layer A — Deterministic engineering logic (NEVER the LLM)
Pacing, delivery %, fill rate, error rate, z-scores, baselines, thresholds, severity, health score, revenue-at-risk maths, data validation, candidate-cause scoring.
→ Pure Python functions. Unit tested. Reproducible. Zero randomness at request time.

### Layer B — AI reasoning (the LLM)
Interpreting the evidence bundle, writing the human explanation, ranking narrative causes, drafting the recommendation, writing the JIRA description, answering copilot questions.
→ Receives a **structured evidence package only**. Never raw data. Never asked "what's wrong?" from scratch.

**Say this to judges:** *"The LLM is not hallucinating root causes from raw data. Our analytics engine identifies evidence-backed candidate causes, and the LLM synthesizes that evidence into a human-readable diagnosis."*

Enforce it in code: `app/analytics/**` must have **zero** imports from `app/ai/**`.

---

## §3. TECH STACK

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.11 + FastAPI + Pydantic v2 + Uvicorn** | Fast to build, auto OpenAPI docs, typed contracts |
| Analytics | **pandas + numpy** | Baselines, rolling windows, z-scores |
| Store | **In-memory singleton + SQLite (`data/guardian.db`)** | Survives reload, zero setup |
| Realtime | **Server-Sent Events (SSE)** at `/api/stream` | Live incident feed during demo, no WS complexity |
| LLM | **Adapter interface** (`LLMProvider`) with 3 impls: OpenAI, Gemini, `DeterministicProvider` | Demo never depends on network |
| Frontend | **Next.js 14 App Router + TypeScript + Tailwind + Recharts + lucide-react + framer-motion** | Already in repo; add framer-motion |
| Data fetch | **SWR** + typed `lib/api.ts` client | Polling + revalidation for the live feel |
| Tests | **pytest** (backend), a smoke script (frontend) | Prove the maths |

Add to frontend: `framer-motion`, `swr`, `cmdk` (command palette), `sonner` (toasts), `@radix-ui/react-dialog`, `@radix-ui/react-tabs`, `@radix-ui/react-tooltip`.

---

## §4. REPOSITORY LAYOUT (build exactly this)

```
revenue-guardian/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app, CORS, routers, startup seed
│   │   ├── config.py                    # Settings via pydantic-settings + .env
│   │   ├── deps.py                      # DI: store, clock, llm provider
│   │   │
│   │   ├── models/                      # Pydantic v2 domain models (§5)
│   │   │   ├── campaign.py
│   │   │   ├── supply.py
│   │   │   ├── incident.py
│   │   │   ├── evidence.py
│   │   │   ├── diagnosis.py
│   │   │   ├── recommendation.py
│   │   │   └── action.py
│   │   │
│   │   ├── ingestion/                   # Adapters — one interface, mock + real impls
│   │   │   ├── base.py                  # DataSource protocol
│   │   │   ├── gam_client.py            # MockGAMClient | LiveGAMClient (stub)
│   │   │   ├── springserve_client.py    # MockSpringServeClient | Live (stub)
│   │   │   ├── athena_client.py         # MockAthenaClient (historical baselines)
│   │   │   └── normalizer.py            # → CampaignHealthRecord (§5.4)
│   │   │
│   │   ├── quality/
│   │   │   └── data_quality.py          # §8 gate — runs BEFORE analytics
│   │   │
│   │   ├── analytics/                   # ⛔ NO AI IMPORTS ALLOWED
│   │   │   ├── pacing.py
│   │   │   ├── fill_rate.py
│   │   │   ├── errors.py
│   │   │   ├── baseline.py              # rolling mean / stddev / z-score
│   │   │   ├── anomaly.py
│   │   │   ├── health_score.py
│   │   │   ├── revenue_risk.py
│   │   │   └── prioritization.py        # risk score + P0..P3
│   │   │
│   │   ├── diagnosis/
│   │   │   ├── evidence_builder.py      # builds EvidencePackage (§13)
│   │   │   ├── root_cause_rules.py      # deterministic candidate causes (§9)
│   │   │   ├── cause_scoring.py         # weight → normalized confidence
│   │   │   └── investigator.py          # orchestrates rules → LLM → Diagnosis
│   │   │
│   │   ├── ai/
│   │   │   ├── provider.py              # LLMProvider protocol + factory
│   │   │   ├── openai_provider.py
│   │   │   ├── gemini_provider.py
│   │   │   ├── deterministic_provider.py # template-based fallback — MUST be good
│   │   │   ├── prompts.py               # system prompts, versioned
│   │   │   ├── schemas.py               # strict JSON output schemas
│   │   │   └── grounding.py             # rejects any claim not in evidence
│   │   │
│   │   ├── recommendations/
│   │   │   ├── engine.py
│   │   │   ├── recovery_estimator.py    # conservative / expected / worst case
│   │   │   └── what_if.py               # simulate targeting changes (§16.4)
│   │   │
│   │   ├── actions/
│   │   │   ├── approval.py              # human-in-the-loop state machine
│   │   │   ├── slack.py                 # builds Block Kit payload (dry-run)
│   │   │   ├── jira.py                  # builds JIRA issue payload (dry-run)
│   │   │   └── gam_action.py            # simulated remediation
│   │   │
│   │   ├── impact/
│   │   │   └── tracker.py               # risk burn-down, revenue protected ledger
│   │   │
│   │   ├── tools/                       # MCP-style tool registry (§16.6)
│   │   │   ├── registry.py
│   │   │   └── definitions.py
│   │   │
│   │   ├── simulation/
│   │   │   ├── clock.py                 # virtual clock (pause / speed / seek)
│   │   │   ├── scenarios.py             # THE GOLDEN INCIDENT (§14)
│   │   │   └── engine.py                # ticks the world forward, emits events
│   │   │
│   │   ├── events/
│   │   │   └── bus.py                   # async pub/sub → SSE
│   │   │
│   │   ├── store/
│   │   │   ├── memory.py
│   │   │   └── seed.py                  # deterministic seeded mock universe
│   │   │
│   │   └── api/
│   │       ├── routes_campaigns.py
│   │       ├── routes_incidents.py
│   │       ├── routes_analysis.py
│   │       ├── routes_actions.py
│   │       ├── routes_copilot.py
│   │       ├── routes_simulation.py
│   │       ├── routes_metrics.py
│   │       └── routes_stream.py
│   │
│   ├── data/
│   │   ├── campaigns.csv
│   │   ├── supply_tags.csv
│   │   ├── vast_errors.csv
│   │   └── historical_daily.csv         # 30 days of baselines
│   │
│   ├── tests/
│   │   ├── test_pacing.py
│   │   ├── test_anomaly.py
│   │   ├── test_health_score.py
│   │   ├── test_revenue_risk.py
│   │   ├── test_root_cause.py
│   │   ├── test_data_quality.py
│   │   └── test_grounding.py
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/                            # existing Next.js app moves here (or stays at root)
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx                 # Mission Control (executive)
│       │   ├── campaigns/page.tsx
│       │   ├── campaigns/[id]/page.tsx  # War Room (investigation)
│       │   ├── incidents/page.tsx
│       │   ├── incidents/[id]/page.tsx
│       │   ├── impact/page.tsx          # Revenue Protected ledger
│       │   ├── agent/page.tsx           # Agent trace / tool-call viewer
│       │   └── settings/page.tsx
│       ├── components/
│       │   ├── layout/{Sidebar,Header,CommandPalette,DemoControlBar}.tsx
│       │   ├── charts/{RiskBurndown,PacingChart,FillRateChart,CauseWaterfall,SignalSparkline,HealthGauge}.tsx
│       │   ├── incident/{DiagnosisCard,EvidenceTable,RecommendationCard,WhatIfSimulator,ApprovalFlow,ImpactTimeline}.tsx
│       │   ├── integrations/{SlackPreview,JiraPreview}.tsx
│       │   ├── copilot/{Copilot,AgentTrace}.tsx
│       │   └── ui/…                     # keep + extend existing primitives
│       ├── lib/
│       │   ├── api.ts                   # typed fetch client
│       │   ├── types.ts                 # generated from backend OpenAPI
│       │   ├── format.ts                # money/pct/duration formatters
│       │   └── stream.ts                # SSE hook
│       └── hooks/{useCampaigns,useIncident,useLiveEvents,useSimClock}.ts
│
├── docker-compose.yml                   # optional one-command run
├── Makefile                             # make dev / make seed / make demo
└── README.md
```

---

## §5. DOMAIN MODEL — EXACT SCHEMAS

Implement as Pydantic v2 models. Mirror as TS types in `frontend/src/lib/types.ts`.

### 5.1 Campaign
```python
class Campaign(BaseModel):
    campaign_id: str            # "ACME-CTV-123"
    line_item_id: str
    name: str                   # "Acme Sports CTV"
    advertiser: str
    start_date: date
    end_date: date
    goal_impressions: int       # 10_000_000
    ecpm: float                 # 12.0  (expected monetization rate, $)
    priority: int               # GAM line item priority 1-16
    status: Literal["ACTIVE","PAUSED","COMPLETED"]
    targeting: Targeting
    created_at: datetime

class Targeting(BaseModel):
    geos: list[str]             # ["UK"]
    devices: list[str]          # ["CTV"]
    platforms: list[str]        # ["Roku","Samsung TV"]
    content_categories: list[str]  # ["Sports"]
    frequency_cap: int | None
    last_changed_at: datetime | None   # ← critical diagnostic signal
```

### 5.2 DeliverySnapshot (time series, hourly)
```python
class DeliverySnapshot(BaseModel):
    campaign_id: str
    ts: datetime
    impressions: int
    clicks: int
    revenue: float
    viewability_rate: float
    eligible_inventory: int     # forecasted addressable impressions
    auction_pressure_index: float  # 1.0 = normal, >1 = more competition
```

### 5.3 SupplySignal (SpringServe shape)
```python
class SupplySignal(BaseModel):
    tag_id: str
    tag_name: str
    campaign_id: str | None
    ts: datetime
    requests: int
    responses: int
    errors: int
    device: str
    country: str
    platform: str
    vast_error_breakdown: dict[str,int]   # {"VAST_303": 4211, "VAST_403": 118, ...}
```

### 5.4 CampaignHealthRecord (the normalized universal record — everything downstream uses ONLY this)
```python
class CampaignHealthRecord(BaseModel):
    campaign_id: str
    line_item_id: str
    campaign_name: str
    ts: datetime
    # delivery
    expected_impressions: int
    actual_impressions: int
    delivery_pct: float
    pacing_pct: float
    pacing_gap_pts: float
    # supply
    fill_rate: float
    baseline_fill_rate: float
    error_rate: float
    baseline_error_rate: float
    # revenue
    expected_revenue: float
    actual_revenue: float
    # context
    eligible_inventory_change_pct: float
    auction_pressure_change_pct: float
    targeting_changed_recently: bool
    # scoring
    health_score: float          # 0-100
    health_band: Literal["HEALTHY","WARNING","HIGH_RISK","CRITICAL"]
    data_quality: DataQualityReport
```

### 5.5 Incident
```python
class Incident(BaseModel):
    incident_id: str            # "INC-1024"
    campaign_id: str
    campaign_name: str
    severity: Literal["CRITICAL","HIGH","MEDIUM","LOW"]
    priority: Literal["P0","P1","P2","P3"]
    status: Literal["OPEN","INVESTIGATING","AWAITING_APPROVAL","ACTIONED","RESOLVED","FALSE_POSITIVE"]
    detected_at: datetime
    signals: list[str]          # ["pacing_down","fill_rate_down","vast_errors_up"]
    health_score: float
    revenue_risk: RevenueRisk
    risk_score: float
    diagnosis: Diagnosis | None
    recommendation: Recommendation | None
    timeline: list[TimelineEvent]
    detection_latency_seconds: int
```

### 5.6 RevenueRisk
```python
class RevenueRisk(BaseModel):
    impression_gap: int
    ecpm: float
    conservative: float
    expected: float
    worst_case: float
    currency: str = "USD"
    method: str                 # human-readable formula string, shown in UI tooltip
```

### 5.7 Diagnosis
```python
class CandidateCause(BaseModel):
    cause: Literal["TARGETING_RESTRICTION","SUPPLY_SHORTAGE","VAST_PLAYBACK_ERRORS",
                   "GAM_COMPETITION","CREATIVE_ISSUE","FREQUENCY_CAP","DATA_QUALITY","BUDGET_PACING"]
    weight: float               # raw rule weight
    confidence: float           # normalized 0-1
    evidence_ids: list[str]     # ← MUST reference EvidenceItem.id
    label: str

class Diagnosis(BaseModel):
    incident_id: str
    primary_cause: CandidateCause
    secondary_causes: list[CandidateCause]
    confidence: float
    confidence_breakdown: list[ConfidenceContribution]
    narrative: str              # LLM-written, evidence-grounded
    evidence_used: list[str]
    generated_by: Literal["llm:openai","llm:gemini","deterministic"]
    model: str | None
    generated_at: datetime
    grounding_passed: bool
```

### 5.8 Recommendation
```python
class Recommendation(BaseModel):
    incident_id: str
    title: str                              # "Remove Roku platform restriction"
    action_type: Literal["EXPAND_TARGETING","PAUSE_TAG","RAISE_PRIORITY",
                          "ADJUST_FREQ_CAP","REPLACE_CREATIVE","INVESTIGATE_ONLY"]
    current_state: dict
    proposed_state: dict
    predicted_impression_gain: int
    predicted_recovery: RevenueRisk         # reuse the 3-point range
    confidence: float
    rationale: str
    requires_approval: bool = True
```

### 5.9 EvidenceItem — **the anti-hallucination primitive**
```python
class EvidenceItem(BaseModel):
    id: str                     # "EV-07"
    metric: str                 # "fill_rate"
    label: str                  # "Fill rate dropped 29% vs 7-day baseline"
    current_value: float
    baseline_value: float | None
    delta_pct: float | None
    z_score: float | None
    source: Literal["GAM","SPRINGSERVE","ATHENA","DERIVED"]
    window: str                 # "2026-08-08 08:00–09:00 UTC"
    strength: Literal["STRONG","MODERATE","WEAK"]
```

---

## §6. MOCK DATA UNIVERSE (deterministic — `random.Random(42)`)

Generate on startup into SQLite + CSV. **The same seed must produce the same demo every single time.**

| Entity | Count | Notes |
|---|---|---|
| Campaigns | **247** | matches the "247 monitored" headline |
| Advertisers | 30 | Acme, Nike, Disney, Sony, Samsung, Adidas, Toyota, HSBC… |
| Delivery snapshots | 247 × 30 days × 24h | hourly; use realistic diurnal curve (peak 19:00–22:00) |
| Supply tags | 1,200 | mapped to campaigns many-to-one |
| Historical baselines | 30 days | Athena mock — feeds z-scores |

**Health distribution must land at:** ~193 healthy, 32 warning, 15 high risk, **7 critical**.

**Realism rules — non-negotiable, this is what makes judges believe it:**
- Diurnal + weekly seasonality on impressions (sine curve + weekend dip).
- Fill rate hovers 68–74% with ±2% noise for healthy campaigns.
- VAST error rate baseline 1.8–2.4%.
- eCPM varies by type: CTV $18–24, Sports $12–16, News $6–9, Web $3–5.
- 3 campaigns must have **deliberate data-quality failures** (missing hours, stale feed, null revenue) so the DQ gate visibly fires and produces a *DATA_QUALITY* incident, **not** a campaign incident. Judges love this.
- 1 campaign is **overdelivering** (pacing 138%) — proves it's not just a "low = bad" threshold.
- 2 campaigns look bad but recovered by themselves → system marks them **FALSE_POSITIVE / auto-closed**. Proves precision.

---

## §7. DETERMINISTIC ANALYTICS — EXACT FORMULAS

Implement each as a pure function with a docstring containing the formula. Unit test each.

```
delivery_pct        = actual_impressions / expected_impressions * 100

elapsed_pct         = (now - start) / (end - start) * 100
expected_impressions= goal_impressions * elapsed_pct / 100
pacing_pct          = actual_impressions / expected_impressions * 100
pacing_gap_pts      = delivery_pct - elapsed_pct        # e.g. 31 - 50 = -19 pts

fill_rate           = responses / requests * 100
error_rate          = errors / requests * 100

baseline(metric)    = rolling mean over trailing 7 days, excluding current window
stddev(metric)      = rolling sample stddev over same window
z_score             = (current - baseline) / stddev      # guard stddev < 1e-6
deviation_pct       = (current - baseline) / baseline * 100
```

### Health score (weights are **config**, not magic numbers — put in `config.py`)
```
health_score = 100 - (
      40 * penalty(pacing_gap_pts, floor=-30)
    + 25 * penalty(fill_deviation_pct, floor=-40)
    + 20 * penalty(error_deviation_pct_inverted, ceil=+300)
    + 10 * penalty(supply_signal_degradation)
    +  5 * penalty(data_quality_score)
)
# penalty() clamps to [0,1]; expose every component in the API response so the UI
# can render the exact contribution bar chart.

bands:  0–30 CRITICAL · 31–50 HIGH_RISK · 51–70 WARNING · 71–100 HEALTHY
```

### Anomaly detection (multi-signal, must agree)
Raise an anomaly only when **≥2** of these fire:
1. `|z_score| >= 2.5` on any core metric
2. `deviation_pct` breaches business threshold (pacing −15 pts, fill −20%, errors +100%)
3. `health_score` crosses a band downward
4. sustained for ≥2 consecutive windows (kills flapping)

This is your false-positive defence. **Say it out loud in the demo.**

### Revenue at risk
```
impression_gap = max(0, expected_impressions - actual_impressions)
expected_risk  = impression_gap / 1000 * ecpm
conservative   = expected_risk * 0.65      # assumes partial natural recovery
worst_case     = expected_risk * 1.35      # assumes continued degradation to end date
```
Always label it **"Estimated revenue at risk"** in the UI. Never "revenue lost". Store `method` as a string and show it in a tooltip — judges will ask "where did that number come from?" and you click and show them.

### Prioritization
```
risk_score = normalize(expected_risk) * severity_weight * confidence * urgency
urgency    = days_remaining_factor    # less time left = harder to recover = more urgent

P0: risk_score >= 0.75   P1: >= 0.5   P2: >= 0.25   P3: rest
```

---

## §8. DATA QUALITY GATE (runs BEFORE anything else)

```python
checks = [
  campaign_id_present, timestamp_valid, impressions_numeric_non_negative,
  expected_impressions_gt_zero, revenue_valid, no_duplicate_records,
  freshness_within_sla(minutes=90), no_missing_hours_in_window,
  monotonic_cumulative_counters,
]
```
Output `DataQualityReport(score: float, failed_checks: list[str], verdict: OK|DEGRADED|BAD)`.

**If verdict == BAD → create a `DATA_QUALITY` incident and STOP.** Do not run diagnosis. Do not report underdelivery.

> Demo line: *"The system refuses to tell you a campaign is failing when the truth is the feed didn't land. That distinction is the difference between a tool people trust and a tool people mute."*

---

## §9. ROOT CAUSE ENGINE — HYBRID (rules first, LLM second)

### Step 1 — Deterministic rules produce candidates + weights
```python
RULES = [
  Rule("SUPPLY_SHORTAGE",       when=lambda e: e.fill_deviation_pct <= -20,          weight=lambda e: min(1.0, abs(e.fill_deviation_pct)/40)),
  Rule("VAST_PLAYBACK_ERRORS",  when=lambda e: e.error_rate >= 2*e.baseline_error_rate, weight=lambda e: min(1.0, e.error_rate/(e.baseline_error_rate*5))),
  Rule("TARGETING_RESTRICTION", when=lambda e: e.eligible_inventory_change_pct <= -15 or e.targeting_changed_recently, weight=...),
  Rule("GAM_COMPETITION",       when=lambda e: e.auction_pressure_change_pct >= 20,   weight=...),
  Rule("FREQUENCY_CAP",         when=lambda e: e.unique_reach_saturation >= 0.85,     weight=...),
  Rule("CREATIVE_ISSUE",        when=lambda e: e.creative_error_share >= 0.4,         weight=...),
  Rule("BUDGET_PACING",         when=lambda e: e.pacing_pct > 130,                    weight=...),
]
```
Each fired rule **must attach the `EvidenceItem` ids** that caused it to fire. No evidence → rule cannot fire.

### Step 2 — Normalize to confidences
```
confidence_i = weight_i / Σ weights      →   Targeting 0.61 · VAST 0.27 · Inventory 0.12
```

### Step 3 — LLM synthesizes (never selects the cause; it explains the ranked causes)

---

## §10. THE AI LAYER

### System prompt (`ai/prompts.py`, version it)
```
You are an advertising operations diagnostic analyst.

You will receive a structured EVIDENCE PACKAGE and a RANKED LIST OF CANDIDATE CAUSES
that were produced by a deterministic analytics engine.

Your job is to SYNTHESIZE, not to speculate.

Rules:
- Use ONLY the numbers present in the evidence package.
- Every claim you make must cite an evidence id (e.g. [EV-03]).
- Do NOT invent metrics, dates, platforms, or percentages.
- Do NOT change the ranking of causes. Explain the ranking you were given.
- If the evidence is insufficient for a confident diagnosis, say so explicitly
  and set "insufficient_evidence": true.
- Write for a busy Ad Ops manager: direct, specific, no filler, no marketing language.

Return ONLY valid JSON matching the provided schema.
```

### Strict output schema
```json
{
  "narrative": "string, 2-4 sentences, each claim cites [EV-xx]",
  "primary_cause_explanation": "string",
  "secondary_notes": ["string"],
  "recommended_action_summary": "string",
  "evidence_cited": ["EV-03", "EV-07"],
  "insufficient_evidence": false
}
```

### Grounding validator (`ai/grounding.py`) — **the killer detail**
After the LLM responds:
1. Extract every `[EV-xx]` citation → all must exist in the package. Else reject.
2. Extract every number/percentage in the narrative via regex → each must appear (within 1% tolerance) in the evidence package. Else reject.
3. On rejection: retry once with the violation appended, then fall back to `DeterministicProvider`.
4. Record `grounding_passed` on the Diagnosis and **render a ✅ "Evidence-grounded" badge in the UI.**

> Demo line: *"We programmatically verify that the AI didn't make up a single number. If it does, we reject the output and fall back."*

### DeterministicProvider (the safety net)
Template-based narrative built from the top causes and evidence. It must read *well* — judges may never know the key was missing. Example output:

> "Delivery is tracking 19 points behind schedule (62% vs 100% expected) [EV-01]. The dominant contributor is a 34% contraction in eligible inventory following a targeting change on 06 Aug [EV-04, EV-05]. A secondary factor is a 4.1× increase in VAST errors concentrated on Roku [EV-07]. Together these account for the majority of the delivery gap."

---

## §11. RECOMMENDATION + RECOVERY ESTIMATION

For each `primary_cause`, map to an action template, then compute predicted gain:

```
TARGETING_RESTRICTION → EXPAND_TARGETING
    predicted_impression_gain = eligible_inventory_recovered * historical_fill_rate * remaining_time_factor

VAST_PLAYBACK_ERRORS → PAUSE_TAG (worst offending tags) 
    predicted_impression_gain = error_impressions_recoverable * 0.8

GAM_COMPETITION → RAISE_PRIORITY
    predicted_impression_gain = auction_win_delta_estimate
```

Render as:
```
RECOMMENDED ACTION
Current:   UK + CTV + Sports + Roku
Proposed:  UK + CTV + Sports
Expected impact:  +420,000 impressions
Estimated recovery: $3.8K – $5.1K
Confidence: 87%
```

---

## §12. ACTION LAYER — HUMAN IN THE LOOP (never auto-execute)

State machine:
```
OPEN → INVESTIGATING → AWAITING_APPROVAL → ACTIONED → RESOLVED
                                  ↓
                            FALSE_POSITIVE
```

Every transition writes an immutable `AuditLogEntry(actor, action, before, after, ts, incident_id)`.

- **Slack**: build a real **Block Kit** JSON payload. `DRY_RUN=true` by default → return the payload, render it in the UI as a pixel-accurate Slack message preview. If `SLACK_WEBHOOK_URL` is set, actually post it.
- **JIRA**: build a real JIRA REST v3 issue payload with ADF description. Same dry-run pattern.
- **GAM action**: simulated only. Applies the proposed targeting to the mock world, which **actually changes the numbers** the simulation engine generates going forward. This is what makes §13 magical.

### Slack Block Kit content (exact)
```
🚨 REVENUE GUARDIAN — CRITICAL
Acme Sports CTV
Revenue at risk: 💰 $24,300
Pacing: 62% vs expected 100%
Primary suspected cause: 🎯 Targeting restriction — 61%
Secondary: 📺 Roku VAST errors — 27%
Recommended action: Review Roku targeting restriction
Potential recovery: $3.8K–$5.1K
Confidence: 94%
[Investigate] [Create JIRA] [View Campaign]
```

---

## §13. IMPACT TRACKING — the part everyone else skips

After an action is approved, the simulation applies it and the tracker records:

```python
ImpactRecord(
    incident_id, action_id,
    risk_at_detection=24_300,
    risk_timeline=[(t0, 24300), (t1, 18700), (t2, 7200), (t3, 0)],
    impressions_recovered=411_204,
    revenue_protected=4_934.45,
    time_to_detect_seconds=1080,      # 18 min
    time_to_resolve_seconds=8_100,
    outcome="RECOVERED" | "PARTIAL" | "NO_EFFECT"
)
```

Global ledger powers the headline metric:

> **"Revenue Guardian identified $84.2K of revenue at risk and protected an estimated $61.7K."**
> *(Label clearly: figures from simulated demo dataset.)*

---

## §14. THE GOLDEN INCIDENT (build ONE perfect scenario, not 20 mediocre ones)

**`ACME-CTV-123 — Acme Sports CTV`**

Scripted cascade over the simulated timeline:

| T | Event |
|---|---|
| T-48h | Healthy. Fill 72%, VAST errors 2.1%, pacing 100%, delivery on track |
| T-6h | A targeting change adds a Roku-only platform restriction |
| T-5h | `eligible_inventory` drops 34% |
| T-4h | Fill rate slides 72% → 51% |
| T-3h | Roku VAST_303 errors spike 2.1% → 8.7% (4.1×) |
| T-2h | Delivery diverges from forecast; pacing falls to 62% |
| **T-0** | 2 signals agree for 2 windows → **INC-1024 CRITICAL created**, 18 min after onset |
| T+1 | Evidence package built (9 evidence items) |
| T+2 | Diagnosis: Targeting 61% / VAST 27% / Inventory 12%, confidence 91% |
| T+3 | Revenue at risk: $15.8K / **$24.3K** / $31.4K |
| T+4 | Recommendation: remove Roku restriction, +420K imps, $3.8K–$5.1K |
| T+5 | Human approves → JIRA `REV-1024` created, Slack posted |
| T+6 | Simulation applies change → fill recovers 51% → 68% |
| T+7 | Risk burns down $24.3K → $18.7K → $7.2K → **$0** |
| T+8 | Impact: **$4.9K protected**, incident RESOLVED |

**This entire cascade must be replayable on demand via `POST /api/simulation/scenario/golden/replay`.**

---

## §15. THE SIMULATION ENGINE — your demo superpower

```
POST /api/simulation/start            {speed: 1|10|60|300}
POST /api/simulation/pause
POST /api/simulation/seek             {to: "2026-08-08T06:00:00Z"}
POST /api/simulation/inject           {scenario: "vast_spike"|"targeting_change"|"supply_collapse"|"data_outage"}
POST /api/simulation/scenario/golden/replay
GET  /api/simulation/state
```

A background asyncio task advances a **virtual clock**, regenerates metrics, runs the full pipeline each tick, and publishes events on the bus → SSE → the UI updates live **while you are talking**.

**Demo Control Bar** (frontend, collapsible, top of screen, toggle with `⌘.`):
```
[▶ Play] [⏸] [1× 10× 60× 300×] [⏮ Reset] [💥 Inject Incident ▾] [⚡ Replay Golden Incident]
Sim clock: 2026-08-08 08:14:00 UTC        ● LIVE
```

> This is the single highest-leverage feature. Judges see incidents appear **live on screen**, not a static screenshot.

---

## §16. FRONTEND SPECIFICATION

### 16.0 Design system (keep + elevate existing dark theme)
- Base `#0B1020` → `#0F172A` mesh gradient, glassmorphism cards `bg-white/[0.03] backdrop-blur border-white/[0.08]`.
- Accents: emerald `#10B981` healthy · amber `#F59E0B` warning · orange `#F97316` high · red `#EF4444` critical · blue `#3B82F6` primary.
- Typography: Inter/Geist. Numbers in **tabular-nums**. Big KPI figures at `text-4xl font-semibold tracking-tight`.
- Motion: framer-motion. Numbers **count up** on change. New incidents **slide in with a red pulse**. Risk burn-down **animates downward**.
- Every card that shows a computed number has an **ⓘ tooltip revealing the formula and the source window**.
- Skeleton loaders, empty states, and error states for every panel. No layout shift.
- Fully keyboard navigable. `⌘K` command palette with actions: *Go to campaign*, *Replay golden incident*, *Inject VAST spike*, *Open incident*, *Toggle demo bar*.

### 16.1 `/` — Mission Control
- Hero KPI strip (animated): **Campaigns Monitored 247 · Healthy 193 · Warning 32 · High Risk 15 · Critical 7**
- Two hero cards: **Revenue at Risk $84.2K** and **Revenue Protected $61.7K** with sparkline + delta vs yesterday.
- **Risk Burn-down chart** — stacked area of at-risk vs protected over the last 7 simulated days.
- **Live Signal Feed** (SSE) — right rail, streaming timestamped events: `08:14:03 · INC-1024 created · Acme Sports CTV · CRITICAL`.
- **Priority Queue** — top 5 incidents as rich rows: severity chip, campaign, $risk, confidence ring, primary cause chip, `Investigate →`.
- **System Performance**: avg detection time 18m · precision 94% · incidents auto-closed 6 · data quality 99.2%.

### 16.2 `/campaigns` — Campaign Health
- Virtualized table, 247 rows, sortable on every column, filter chips (status / type / region / platform / advertiser), free-text search, saved views.
- Columns: Health gauge (mini radial) · Campaign · Advertiser · Pacing (inline bar vs expected) · Fill (sparkline) · VAST err (sparkline) · Risk $ · Priority.
- Row hover → mini popover with 24h sparkline. Row click → War Room.
- Density toggle, CSV export.

### 16.3 `/campaigns/[id]` — **THE WAR ROOM** (the money shot)
Layout: left = evidence, right = AI.

**Left column**
1. Header: campaign, advertiser, flight dates, status chip, **HealthGauge** 0–100 with band color.
2. Four stat tiles: Expected · Actual · Delivery Gap · Estimated Revenue at Risk (with the 3-point range on hover).
3. **Pacing chart** — expected vs actual cumulative, with a **vertical divergence marker** annotated *"Divergence detected 13:00"*.
4. **Signal panel** — three synced small-multiples: Fill Rate, VAST Error Rate, Eligible Inventory. Baseline shown as a dashed band (mean ± 2σ) so anomalies are *visually obvious*.
5. **Evidence table** — every `EvidenceItem`: id, label, current, baseline, Δ%, z, source, window, strength chip. Clicking an evidence row **highlights the corresponding region on the charts**.

**Right column**
6. **AI Diagnosis card**
   - Primary cause + confidence ring (91%)
   - **Cause waterfall bar**: Targeting 61% ▓▓▓▓▓▓ · VAST 27% ▓▓▓ · Inventory 12% ▓
   - Narrative with **clickable [EV-xx] citation chips** that scroll to and flash the evidence row ← *this is the detail that wins hackathons*
   - Badges: `✅ Evidence-grounded` `⚙ Deterministic engine` / `🤖 gpt-4o`
   - **Confidence breakdown** popover: Targeting +0.40, Inventory +0.25, VAST +0.25, Other +0.01 = 91%
7. **Recommendation card** — current vs proposed diff (red strike-through → green), predicted gain, recovery range, confidence.
8. **What-If Simulator** — toggles for each targeting dimension; as you flip Roku off, the predicted impressions/recovery **recompute live** from the backend. Fully interactive.
9. **Action bar**: `Approve & Simulate Fix` · `Create JIRA` · `Send to Slack` · `Mark False Positive`. Each opens a preview modal showing the **exact JSON payload** that would be sent (tab: Preview | Payload).
10. **Impact timeline** — after approval, animates the risk burn-down to $0 and reveals **"$4,934 protected"**.

### 16.4 `/incidents` + `/incidents/[id]`
- Kanban or table toggle by status. Bulk approve. Severity filters.
- Detail view = War Room scoped to the incident, plus full audit log and timeline.

### 16.5 `/impact` — Revenue Protected Ledger
- Cumulative protected revenue chart, per-incident table (detected → resolved, risk, protected, outcome, MTTD, MTTR), outcome distribution donut.
- Headline: **"$61.7K protected across 24 resolved incidents · avg detection 18 min"**.

### 16.6 `/agent` — Agent Trace Viewer (the "we're MCP-ready" flex)
Shows the tool registry and, for any investigation, the **actual sequence of tool calls** made:
```
USER: Why is Acme underdelivering?
 ├─ get_campaign_metrics(campaign_id="ACME-CTV-123")        142ms  ✓
 ├─ get_historical_pacing(days=7)                            89ms  ✓
 ├─ get_supply_tag_health(campaign_id=...)                  201ms  ✓
 ├─ get_vast_errors(platform="Roku")                        118ms  ✓
 ├─ calculate_revenue_risk(...)                              12ms  ✓
 └─ synthesize_diagnosis(evidence=9 items)                  1.8s   ✓ grounded
```
Expandable request/response JSON per call. Registry defined in `app/tools/definitions.py` with MCP-compatible JSON Schema — so the story is *"these tools are already MCP-shaped; exposing them as an MCP server is a config change, not a rewrite."*

### 16.7 Guardian Copilot (floating, `⌘/`)
- Streams tokens. Answers from **live backend state**, not hardcoded strings.
- Suggested prompts: *"What's my biggest risk right now?"* · *"Why is Acme underdelivering?"* · *"How much revenue have we protected today?"* · *"Which platform has the worst VAST errors?"*
- Every answer shows the tool calls it made (link to `/agent`) and cites evidence ids.
- Handles "I don't know" gracefully — if the data isn't there, it says so.

### 16.8 `/settings`
- Integration status grid: GAM `Mock` · SpringServe `Mock` · Athena `Mock` · LLM `Deterministic|OpenAI|Gemini` · Slack `Dry-run` · JIRA `Dry-run`.
- **Live tunable business rules**: health score weights, anomaly thresholds, severity bands — editing them **re-runs the pipeline instantly**. Judges: *"the weights aren't magic numbers, they're configurable business rules"* — then you change one and the dashboard re-scores live.
- Demo mode banner + reset-world button.

---

## §17. API CONTRACT

```
GET  /api/health
GET  /api/metrics/overview                → executive KPIs
GET  /api/metrics/timeseries?days=7       → risk vs protected

GET  /api/campaigns?status&type&region&q&sort&page
GET  /api/campaigns/{id}
GET  /api/campaigns/{id}/timeseries?metric=impressions|fill|errors&hours=48
GET  /api/campaigns/{id}/health           → full health record + score components

POST /api/analysis/run                    → run full pipeline over all campaigns
POST /api/analysis/run/{campaign_id}      → single campaign, returns step-by-step trace

GET  /api/incidents?status&severity&priority
GET  /api/incidents/{id}
GET  /api/incidents/{id}/evidence
POST /api/incidents/{id}/diagnose         → evidence → rules → LLM → Diagnosis
POST /api/incidents/{id}/recommend
POST /api/incidents/{id}/what-if          {proposed_targeting} → predicted impact
POST /api/incidents/{id}/approve
POST /api/incidents/{id}/false-positive
GET  /api/incidents/{id}/impact
GET  /api/incidents/{id}/audit

POST /api/actions/slack/preview           → Block Kit payload
POST /api/actions/slack/send
POST /api/actions/jira/preview            → JIRA issue payload
POST /api/actions/jira/create

POST /api/copilot/ask                     → SSE token stream + tool trace
GET  /api/tools                           → MCP-shaped tool registry

POST /api/simulation/*                    → see §15
GET  /api/stream                          → SSE: incident.created, incident.updated,
                                            metric.tick, action.executed, impact.recorded
```

Every response envelope: `{ data, meta: { generated_at, sim_clock, source: "mock", version } }`.

---

## §18. TEST PLAN (7 tests — no more, no less)

| # | Test | Expected |
|---|---|---|
| 1 | Healthy campaign | No incident |
| 2 | Underdelivery, pacing −19 pts | CRITICAL incident, risk > 0 |
| 3 | Fill rate −29% | `SUPPLY_SHORTAGE` in candidates |
| 4 | VAST errors 4.1× baseline | `VAST_PLAYBACK_ERRORS` in candidates |
| 5 | Multi-signal cascade | Ranked causes, targeting first |
| 6 | Revenue maths | 1.9M gap @ $12 eCPM → expected exactly $22,800 |
| 7 | Missing/stale data | `DATA_QUALITY` incident, **NOT** a campaign incident |

Plus: `test_grounding.py` — a fabricated LLM response containing an invented number must be **rejected**.

Add a CI-less `make test` that runs pytest and prints a green summary you can show on screen.

---

## §19. BUILD ORDER (each phase ends in a runnable demo)

**Phase 1 — Skeleton + data (foundation)**
`models/` → `store/seed.py` (247-campaign universe) → `ingestion/normalizer.py` → FastAPI up with `/api/campaigns`, `/api/metrics/overview` → frontend `lib/api.ts` swapped in, dashboard + campaigns table reading real API.
✅ *Demo: dashboard and table are live from a real backend.*

**Phase 2 — The brain**
`quality/` → `analytics/*` (all formulas + tests) → incident engine → `/api/analysis/run`.
✅ *Demo: click "Run Analysis", incidents appear with real health scores and risk figures.*

**Phase 3 — Diagnosis**
`evidence_builder` → `root_cause_rules` → `cause_scoring` → AI layer + grounding + deterministic fallback → War Room page with diagnosis card, cause waterfall, clickable evidence citations.
✅ *Demo: the money shot page.*

**Phase 4 — Recommend + Act**
recommendation engine → recovery estimator → what-if simulator → approval flow → Slack/JIRA payload previews → audit log.
✅ *Demo: full detect→act loop.*

**Phase 5 — Measure + Live**
impact tracker → `/impact` ledger → SSE event bus → simulation clock → Demo Control Bar → golden incident replay.
✅ *Demo: incidents appear live; risk burns down to zero on stage.*

**Phase 6 — Polish (the multiplier)**
Copilot on live state → `/agent` trace viewer → `⌘K` palette → framer-motion → tooltips with formulas → settings live-tuning → empty/error/loading states → README + one-command run.

---

## §20. GUARDRAILS — WHAT NOT TO BUILD

Do **not** build, at any point:
- Real GAM/SpringServe API calls (write the adapter interface + a stubbed `LiveClient`, nothing more)
- Auth, users, RBAC, multi-tenancy
- Prophet, ARIMA, or any ML forecasting — rolling baselines + z-scores are correct and defensible for this stage
- A real MCP server (make the tools MCP-*shaped*; that's the story)
- Kubernetes, Terraform, cloud deployment
- Autonomous remediation without human approval — this is a **feature**, not a limitation. Say so.
- Dark/light theme toggle, i18n, mobile layouts

Security hygiene (judges/managers check this):
- No secrets in code. `.env` gitignored, `.env.example` committed with placeholders.
- All external calls default to `DRY_RUN=true`.
- Pydantic validation on every input. No f-string SQL.

---

## §21. RUN COMMANDS (must work from a clean clone)

```bash
make setup     # python -m venv + pip install -r backend/requirements.txt + npm install
make seed      # regenerate deterministic mock universe (seed=42)
make dev       # backend :8000 + frontend :3000 concurrently
make test      # pytest
make demo      # seed + dev + auto-open localhost:3000 with golden incident armed
```

`.env.example`:
```
LLM_PROVIDER=deterministic      # deterministic | openai | gemini
OPENAI_API_KEY=
GEMINI_API_KEY=
SLACK_WEBHOOK_URL=
JIRA_BASE_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
DRY_RUN=true
DEMO_MODE=true
RANDOM_SEED=42
```

---

## §22. THE 5-MINUTE DEMO SCRIPT (build the product to fit this)

**0:00 — The pain.** *"I'm an Ad Ops manager. I have 247 live campaigns. I cannot manually inspect any of them."*
→ `/` Mission Control. 247 monitored · 7 critical · **$84.2K at risk**.

**0:45 — Detection, live.** Hit `⚡ Replay Golden Incident` on the demo bar. The audience watches the signal feed stream and **INC-1024 slide in red**. *"Detected 18 minutes after onset. A human would have found this tomorrow."*

**1:30 — Prioritization.** *"It's not 7 alerts. It's a ranked queue by business impact."* P0 Acme $24.3K.

**2:00 — Diagnosis (the money shot).** Open the War Room. Pacing chart with divergence marker. Cause waterfall: Targeting 61% / VAST 27% / Inventory 12%. Read the narrative, then **click an [EV-04] chip** → the evidence row flashes. *"Every claim the AI makes is clickable back to the raw signal. And we programmatically reject any output containing a number that isn't in the evidence."*

**2:45 — Quantify.** Hover the risk tile → the 3-point range and the formula. *"Estimated revenue at risk — not 'lost'. It's still recoverable, and that's the whole point."*

**3:15 — Recommend + what-if.** Toggle Roku off in the What-If Simulator → **+420K impressions, $3.8K–$5.1K** recomputes live.

**3:45 — Act.** `Approve & Simulate Fix` → JIRA preview (flip to the Payload tab to prove it's real) → Slack Block Kit preview → approve. Audit log entry appears.

**4:15 — Measure.** Risk burn-down animates **$24.3K → $18.7K → $7.2K → $0**. **"$4,934 protected."**

**4:45 — The close.** `/impact`: *"Across this dataset: $84.2K identified, $61.7K protected, average detection 18 minutes instead of 2 days."* Then `/agent`: *"And these tools are already MCP-shaped — exposing them to an orchestrating agent is a config change, not a rewrite."*

**Answers to the three questions you will be asked:**
- *"How is this different from alerting?"* → "Alerting stops at 'metric down'. We go anomaly → cross-signal investigation → root cause → financial impact → recommended action → human approval → recovery measurement."
- *"How is this different from ChatGPT?"* → "ChatGPT explains what you paste into it. Revenue Guardian continuously gathers operational signals, runs deterministic anomaly detection, correlates multiple ad-tech sources, quantifies financial impact, and drives an operational workflow. The LLM is one component, and it's fenced in by an evidence grounding validator."
- *"Is the AI making things up?"* → click an evidence citation, then show `test_grounding.py` passing.

---

## §23. THE ROADMAP SLIDE

```
Phase 1  DETECT     (today)  monitoring · anomalies · basic root cause · revenue risk
Phase 2  DIAGNOSE            live GAM + SpringServe + VAST + supply signals
Phase 3  ACT                 JIRA · Slack · human-approved GAM actions
Phase 4  OPTIMIZE            predicted recovery · yield optimization · discrepancy reconciliation
Phase 5  AUTONOMOUS AD OPS   monitor → diagnose → recommend → act → learn
```

**Honest risk slide (say these before you're asked — it builds enormous credibility):**
| Risk | Mitigation |
|---|---|
| API field availability | Adapter pattern; mock → live is one class swap |
| Insufficient history for baselines | Athena historicals + rolling windows + synthetic scenarios |
| False positives | Multi-signal agreement + sustained-window + confidence + business-impact gating |
| LLM hallucination | Deterministic analytics + evidence grounding validator + fallback provider |
| Unsafe auto-remediation | Human-in-the-loop by design, full audit log |

---

## §24. DEFINITION OF DONE

- [ ] `make demo` works from a clean clone with **no API keys**
- [ ] All 7 tests + grounding test pass
- [ ] Golden incident replays end-to-end on demand, repeatably
- [ ] Every number on screen traces to a backend computation (tooltip shows the formula)
- [ ] Evidence citations are clickable and highlight the source signal
- [ ] Grounding validator demonstrably rejects a fabricated number
- [ ] Data-quality incident fires instead of a false underdelivery incident
- [ ] Risk burn-down animates to $0 and reports revenue protected
- [ ] Zero imports from `app/ai/**` inside `app/analytics/**`
- [ ] No secrets committed; `DRY_RUN=true` default
- [ ] README has the architecture diagram, the demo script, and the one-sentence pitch

---

### THE SENTENCE TO END ON

> *"Revenue Guardian doesn't just tell you something is wrong. It tells you why, how much it's costing you, what to do about it, and then proves whether the fix worked."*
```
```
