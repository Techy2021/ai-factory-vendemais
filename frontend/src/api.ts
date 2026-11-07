import { resolveApiBase } from "./apiConfig";

const API_BASE = resolveApiBase(import.meta.env.VITE_API_BASE_URL, import.meta.env.DEV);

export interface Lead {
  deal_id: string | null;
  company_name: string | null;
  industry: string | null;
  size_employees: string | null;
  tech_stack: string[] | null;
  icp_match_score: number | null;
  enriched_at: string | null;
}

export interface LeadsResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
}

export interface MetricsResponse {
  leads_total: number;
  average_score: number | null;
  unique_deals: number;
  missing_score_count: number;
}

export interface Period {
  startDate: string;
  endDate: string;
}

export class ApiError extends Error {
  constructor(public readonly status: number) {
    super(`HTTP ${status}`);
  }
}

export async function login(password: string): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) throw new ApiError(response.status);
}

export async function logout(): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new ApiError(response.status);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function count(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function score(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100);
}

function isLead(value: unknown): value is Lead {
  return isObject(value)
    && nullableString(value.deal_id)
    && nullableString(value.company_name)
    && nullableString(value.industry)
    && nullableString(value.size_employees)
    && (value.tech_stack === null || (Array.isArray(value.tech_stack) && value.tech_stack.every((item: unknown) => typeof item === "string")))
    && score(value.icp_match_score)
    && nullableString(value.enriched_at);
}

function isLeadsResponse(value: unknown): value is LeadsResponse {
  return isObject(value)
    && Array.isArray(value.items) && value.items.every(isLead)
    && count(value.total) && count(value.page) && value.page >= 1
    && count(value.page_size) && value.page_size >= 1 && value.page_size <= 100;
}

function isMetricsResponse(value: unknown): value is MetricsResponse {
  return isObject(value)
    && count(value.leads_total) && score(value.average_score)
    && count(value.unique_deals) && count(value.missing_score_count);
}

async function get(path: string, params: URLSearchParams, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(`${API_BASE}${path}?${params}`, {
    credentials: "include",
    signal,
  });
  if (!response.ok) throw new ApiError(response.status);
  return response.json();
}

function periodParams(period: Period): URLSearchParams {
  const params = new URLSearchParams();
  if (period.startDate) params.set("start_date", period.startDate);
  if (period.endDate) params.set("end_date", period.endDate);
  return params;
}

export async function fetchMetrics(period: Period, signal: AbortSignal): Promise<MetricsResponse> {
  const result = await get("/api/metrics", periodParams(period), signal);
  if (!isMetricsResponse(result)) throw new Error("Resposta de métricas inválida.");
  return result;
}

export async function fetchLeads(period: Period, page: number, signal: AbortSignal): Promise<LeadsResponse> {
  const params = periodParams(period);
  params.set("page", String(page));
  params.set("page_size", "10");
  const result = await get("/api/leads", params, signal);
  if (!isLeadsResponse(result)) throw new Error("Resposta de leads inválida.");
  return result;
}

export async function fetchDashboard(
  period: Period,
  page: number,
  signal: AbortSignal,
  onUnauthenticated: () => void,
): Promise<[PromiseSettledResult<MetricsResponse>, PromiseSettledResult<LeadsResponse>]> {
  function watchSession<T>(request: Promise<T>): Promise<T> {
    return request.catch((error: unknown) => {
      if (!signal.aborted && error instanceof ApiError && error.status === 401) {
        onUnauthenticated();
      }
      throw error;
    });
  }
  return Promise.allSettled([
    watchSession(fetchMetrics(period, signal)),
    watchSession(fetchLeads(period, page, signal)),
  ]);
}
