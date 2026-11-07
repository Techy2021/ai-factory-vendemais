import type { Period } from "./api";

export interface DashboardQuery {
  period: Period;
  page: number;
}

export function applyPeriod(query: DashboardQuery, period: Period): DashboardQuery {
  if (query.page === 1 && query.period.startDate === period.startDate && query.period.endDate === period.endDate) {
    return query;
  }
  return { period: { ...period }, page: 1 };
}

export function lastPage(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

export function changePage(query: DashboardQuery, page: number, total: number, pageSize: number): DashboardQuery {
  const boundedPage = Math.max(1, Math.min(page, lastPage(total, pageSize)));
  return boundedPage === query.page ? query : { ...query, page: boundedPage };
}

export function formatDateUtc(value: string | null): string {
  if (!value) return "—";
  const timestamp = value.includes("T") && !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
    ? `${value}Z`
    : value;
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime())
    ? "Data inválida"
    : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeZone: "UTC" }).format(date);
}
