import type { Envelope } from "./types";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new ApiError(`${init?.method ?? "GET"} ${path} failed`, res.status);
  }
  const body = (await res.json()) as Envelope<T>;
  return body.data;
}

export const fetcher = <T,>(path: string) => request<T>(path);

export const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export const api = {
  overview: () => fetcher("/api/metrics/overview"),
  trend: (days = 7) => fetcher(`/api/metrics/timeseries?days=${days}`),
  priorityQueue: (limit = 5) => fetcher(`/api/metrics/priority-queue?limit=${limit}`),
  campaigns: (qs = "") => fetcher(`/api/campaigns${qs}`),
  campaign: (id: string) => fetcher(`/api/campaigns/${id}`),
  series: (id: string, hours = 48) => fetcher(`/api/campaigns/${id}/timeseries?hours=${hours}`),
  incidents: (qs = "") => fetcher(`/api/incidents${qs}`),
  incident: (id: string) => fetcher(`/api/incidents/${id}`),
  diagnose: (id: string) => post(`/api/incidents/${id}/diagnose`),
  whatIf: (id: string, proposed: Record<string, string[]>) =>
    post(`/api/incidents/${id}/what-if`, proposed),
  approve: (id: string, actor = "ad.ops@demo") => post(`/api/incidents/${id}/approve`, { actor }),
  falsePositive: (id: string) => post(`/api/incidents/${id}/false-positive`, {}),
  slackPreview: (id: string) => post(`/api/actions/slack/preview`, { incident_id: id }),
  slackSend: (id: string) => post(`/api/actions/slack/send`, { incident_id: id }),
  jiraPreview: (id: string) => post(`/api/actions/jira/preview`, { incident_id: id }),
  jiraCreate: (id: string) => post(`/api/actions/jira/create`, { incident_id: id }),
  runAnalysis: (campaignId?: string) =>
    post(`/api/analysis/run${campaignId ? `?campaign_id=${campaignId}` : ""}`),
  simState: () => fetcher("/api/simulation/state"),
  simStart: (speed: number) => post("/api/simulation/start", { speed }),
  simPause: () => post("/api/simulation/pause", {}),
  simReset: () => post("/api/simulation/reset", {}),
  simInject: (scenario: string) => post("/api/simulation/inject", { scenario }),
  replayGolden: () => post("/api/simulation/scenario/golden/replay", {}),
  impact: () => fetcher("/api/impact"),
  settings: () => fetcher("/api/settings"),
  updateWeights: (weights: Record<string, number>) => post("/api/settings/weights", weights),
  tools: () => fetcher("/api/tools"),
  events: (limit = 40) => fetcher(`/api/events/recent?limit=${limit}`),
  ask: (question: string) => post("/api/copilot/ask", { question }),
};
