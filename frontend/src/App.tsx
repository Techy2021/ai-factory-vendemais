import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { ApiError, fetchDashboard, login, logout } from "./api";
import type { LeadsResponse, MetricsResponse, Period } from "./api";
import { applyPeriod as applyQueryPeriod, changePage, formatDateUtc, lastPage } from "./query";
import type { DashboardQuery } from "./query";

type DashboardState =
  | { status: "loading" | "unauthenticated" | "error" }
  | { status: "ready"; leads: LeadsResponse; metrics: MetricsResponse };

const metrics = [
  { label: "Total de Leads", detail: "Leads enriquecidos", icon: "users" },
  { label: "Pontuação Média ICP", detail: "Média de aderência", icon: "chart" },
  { label: "Negócios Únicos", detail: "Negócios identificados", icon: "briefcase" },
  { label: "Sem Pontuação", detail: "Leads sem score ICP", icon: "alert" },
] as const;

type IconName =
  | "grid"
  | "users"
  | "chart"
  | "briefcase"
  | "alert"
  | "calendar"
  | "arrow"
  | "spark"
  | "database";

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" /><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
    chart: <><path d="M4 20h16M6 16v-4M12 16V4M18 16V8" /></>,
    briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" /></>,
    alert: <><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></>,
    arrow: <><path d="m9 18 6-6-6-6" /></>,
    spark: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3ZM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" /></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v7c0 1.66 3.58 3 8 3s8-1.34 8-3V5M4 12v7c0 1.66 3.58 3 8 3s8-1.34 8-3v-7" /></>,
  };

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}

function MetricCard({ label, detail, icon, value, status }: (typeof metrics)[number] & { value: string; status: string }) {
  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span className="metric-card__label">{label}</span>
        <span className="metric-card__icon"><Icon name={icon} /></span>
      </div>
      <p className="metric-card__value">{value}</p>
      <p className="metric-card__detail">{detail}</p>
      <span className="metric-card__status">{status}</span>
    </article>
  );
}

function TableState({ state }: { state: "loading" | "error" | "empty" | "unauthenticated" }) {
  const content = {
    unauthenticated: {
      title: "Sessão não autenticada",
      description: "Autentique-se pelo mecanismo administrativo existente para acessar os leads.",
    },
    loading: {
      title: "Carregando leads",
      description: "Aguarde enquanto os dados são carregados.",
    },
    error: {
      title: "Não foi possível carregar os leads",
      description: "Verifique a conexão e tente novamente mais tarde.",
    },
    empty: {
      title: "Nenhum lead encontrado",
      description: "Não há leads para exibir no período selecionado.",
    },
  }[state];

  return (
    <div className="table-state" role={state === "error" || state === "unauthenticated" ? "alert" : "status"}>
      <span className="table-state__icon"><Icon name={state === "error" || state === "unauthenticated" ? "alert" : "database"} /></span>
      <p className="table-state__title">{content.title}</p>
      <p className="table-state__description">{content.description}</p>
    </div>
  );
}

function displayText(value: string | null): string {
  return value?.trim() ? value : "—";
}

function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const password = new FormData(form).get("password");
    form.reset();
    if (typeof password !== "string" || !password) {
      setError("Informe a senha administrativa.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await login(password);
      onSuccess();
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 401
        ? "Senha inválida."
        : reason instanceof ApiError && reason.status === 429
          ? "Muitas tentativas. Aguarde antes de tentar novamente."
          : "Não foi possível entrar. Verifique a conexão e tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit}>
        <span className="brand__mark"><Icon name="spark" /></span>
        <p className="eyebrow">VENDEMAIS</p>
        <h1>Acesso administrativo</h1>
        <p className="login-card__description">Sessão ausente ou expirada. Entre para acessar o dashboard de leads.</p>
        <label htmlFor="password">Senha administrativa</label>
        <input id="password" name="password" type="password" autoComplete="current-password" maxLength={1024} required disabled={loading} />
        {error && <p className="login-card__error" role="alert">{error}</p>}
        <button type="submit" disabled={loading}>{loading ? "Entrando..." : "Entrar"}</button>
      </form>
    </main>
  );
}

function App() {
  const [dashboard, setDashboard] = useState<DashboardState>({ status: "loading" });
  const [session, setSession] = useState<"checking" | "authenticated" | "unauthenticated" | "logging-out">("checking");
  const [logoutError, setLogoutError] = useState("");
  const [query, setQuery] = useState<DashboardQuery>({ period: { startDate: "", endDate: "" }, page: 1 });
  const queryRef = useRef(query);
  const requestRef = useRef<AbortController | null>(null);
  const [draftPeriod, setDraftPeriod] = useState<Period>(query.period);
  const [retry, setRetry] = useState(0);
  const [filterError, setFilterError] = useState("");

  useEffect(() => {
    if (session === "unauthenticated" || session === "logging-out") return;
    const controller = new AbortController();
    requestRef.current = controller;
    setDashboard({ status: "loading" });
    void fetchDashboard(query.period, query.page, controller.signal, () => {
      controller.abort();
      setDashboard({ status: "unauthenticated" });
      setSession("unauthenticated");
    }).then(([metricsResult, leadsResult]) => {
      if (controller.signal.aborted) return;
      if (metricsResult.status === "fulfilled" && leadsResult.status === "fulfilled") {
        const finalPage = lastPage(leadsResult.value.total, leadsResult.value.page_size);
        if (query.page > finalPage) {
          updateQuery(changePage(query, finalPage, leadsResult.value.total, leadsResult.value.page_size));
          return;
        }
        setDashboard({ status: "ready", metrics: metricsResult.value, leads: leadsResult.value });
      } else {
        setDashboard({ status: "error" });
      }
    });
    return () => {
      controller.abort();
      if (requestRef.current === controller) requestRef.current = null;
    };
  }, [query, retry, session === "unauthenticated" || session === "logging-out"]);

  function updateQuery(next: DashboardQuery) {
    if (next === queryRef.current) return;
    requestRef.current?.abort();
    queryRef.current = next;
    setDashboard({ status: "loading" });
    setQuery(next);
  }

  async function handleLogout() {
    requestRef.current?.abort();
    setLogoutError("");
    setSession("logging-out");
    setDashboard({ status: "loading" });
    try {
      await logout();
      setSession("unauthenticated");
    } catch {
      setLogoutError("Não foi possível encerrar a sessão. Tente novamente.");
      setSession("authenticated");
    }
  }

  function applyPeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (draftPeriod.startDate && draftPeriod.endDate && draftPeriod.startDate > draftPeriod.endDate) {
      setFilterError("A data inicial deve ser anterior ou igual à data final.");
      return;
    }
    setFilterError("");
    updateQuery(applyQueryPeriod(queryRef.current, draftPeriod));
  }

  const loadedMetrics = dashboard.status === "ready" ? dashboard.metrics : null;
  const values = loadedMetrics
    ? [
        loadedMetrics.leads_total.toLocaleString("pt-BR"),
        loadedMetrics.average_score === null ? "—" : loadedMetrics.average_score.toLocaleString("pt-BR", { maximumFractionDigits: 1 }),
        loadedMetrics.unique_deals.toLocaleString("pt-BR"),
        loadedMetrics.missing_score_count.toLocaleString("pt-BR"),
      ]
    : ["—", "—", "—", "—"];
  const statusText = dashboard.status === "loading" ? "Carregando" : dashboard.status === "unauthenticated" ? "Sessão não autenticada" : dashboard.status === "error" ? "Dados indisponíveis" : "Dados carregados";
  const leads = dashboard.status === "ready" ? dashboard.leads : null;

  if (session === "unauthenticated") {
    return <LoginForm onSuccess={() => { setLogoutError(""); setSession("authenticated"); }} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#visao-geral" aria-label="VendeMais, visão geral">
          <span className="brand__mark"><Icon name="spark" /></span>
          <span><strong>VendeMais</strong><small>INTELIGÊNCIA COMERCIAL</small></span>
        </a>

        <div className="sidebar__navigation">
          <p className="sidebar__label">MENU PRINCIPAL</p>
          <nav aria-label="Navegação principal">
            <a className="nav-link" href="#visao-geral"><Icon name="grid" />Visão Geral</a>
            <a className="nav-link" href="#leads"><Icon name="users" />Leads</a>
          </nav>
        </div>

        <div className="sidebar__footer">
          <span className="sidebar__footer-icon"><Icon name="spark" /></span>
          <div><strong>Mais inteligência,</strong><span>melhores oportunidades.</span></div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar__breadcrumb"><span>Dashboard</span><Icon name="arrow" /><strong>Visão geral</strong></div>
          <div className="topbar__actions">
            <span className="topbar__badge"><span /> Painel de leads</span>
            <button type="button" className="logout-button" onClick={handleLogout} disabled={session === "logging-out"}>{session === "logging-out" ? "Saindo..." : "Sair"}</button>
          </div>
        </header>

        <main className="content" id="visao-geral">
          {logoutError && <p className="session-error" role="alert">{logoutError}</p>}
          <section className="page-intro" aria-labelledby="page-title">
            <div>
              <p className="eyebrow">PAINEL DE INTELIGÊNCIA COMERCIAL</p>
              <h1 id="page-title">Visão geral</h1>
              <p className="page-intro__description">Acompanhe seus leads e identifique novas oportunidades.</p>
            </div>
            <span className="connection-status" role="status"><span /> {statusText}</span>
          </section>

          <section className="overview" aria-labelledby="overview-title">
            <div className="section-heading">
              <div><h2 id="overview-title">Indicadores</h2><p>Uma visão dos seus leads enriquecidos.</p></div>
              <span className="section-heading__note">{statusText}</span>
            </div>
            <div className="metrics-grid">
              {metrics.map((metric, index) => <MetricCard key={metric.label} {...metric} value={values[index]} status={loadedMetrics && index === 1 && loadedMetrics.average_score === null ? "Sem pontuação" : statusText} />)}
            </div>
          </section>

          <section className="leads-panel" id="leads" aria-labelledby="leads-title">
            <div className="leads-panel__header">
              <div className="leads-panel__heading">
                <span className="leads-panel__heading-icon"><Icon name="users" /></span>
                <div><h2 id="leads-title">Leads enriquecidos</h2><p>Explore as informações disponíveis sobre seus leads.</p></div>
              </div>
              <span className="leads-panel__tag">VISÃO DE LEADS</span>
            </div>

            <form className="filters" onSubmit={applyPeriod}>
              <div className="filters__intro"><Icon name="calendar" /><div><strong>Filtrar por período</strong><span>Data de enriquecimento</span></div></div>
              <div className="filters__fields">
                <label>Data inicial<input type="date" value={draftPeriod.startDate} onChange={(event) => setDraftPeriod({ ...draftPeriod, startDate: event.target.value })} aria-describedby="filters-note" /></label>
                <label>Data final<input type="date" value={draftPeriod.endDate} onChange={(event) => setDraftPeriod({ ...draftPeriod, endDate: event.target.value })} aria-describedby="filters-note" /></label>
                <button type="submit">Aplicar filtro</button>
              </div>
              <p id="filters-note" className="filters__note" role={filterError ? "alert" : undefined}>{filterError || "O período considera a data de enriquecimento em UTC."}</p>
            </form>

            {(dashboard.status === "error" || dashboard.status === "unauthenticated") && (
              <div className="retry"><button type="button" onClick={() => setRetry((value) => value + 1)}>Tentar novamente</button></div>
            )}

            <div className="table-scroll">
              <table>
                <thead><tr><th scope="col">Empresa</th><th scope="col">Setor</th><th scope="col">Funcionários</th><th scope="col">Tecnologias</th><th scope="col">ICP</th><th scope="col">Enriquecimento</th></tr></thead>
                <tbody>
                  {leads && leads.items.length > 0 ? leads.items.map((lead, index) => (
                    <tr key={`${leads.page}-${index}`}>
                      <td>{displayText(lead.company_name)}</td>
                      <td>{displayText(lead.industry)}</td>
                      <td>{displayText(lead.size_employees)}</td>
                      <td>{lead.tech_stack && lead.tech_stack.length > 0 ? lead.tech_stack.join(", ") : "—"}</td>
                      <td>{lead.icp_match_score === null ? "—" : lead.icp_match_score.toLocaleString("pt-BR")}</td>
                      <td>{formatDateUtc(lead.enriched_at)}</td>
                    </tr>
                  )) : <tr><td colSpan={6}><TableState state={dashboard.status === "ready" ? "empty" : dashboard.status} /></td></tr>}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>{leads ? `${leads.total.toLocaleString("pt-BR")} lead(s)` : "Resultados indisponíveis"}</span>
              <div className="pagination__controls">
                <button type="button" disabled={!leads || leads.page <= 1} onClick={() => leads && updateQuery(changePage(queryRef.current, queryRef.current.page - 1, leads.total, leads.page_size))}>Anterior</button>
                <span>Página {leads ? leads.page : "—"}</span>
                <button type="button" disabled={!leads || leads.page * leads.page_size >= leads.total} onClick={() => leads && updateQuery(changePage(queryRef.current, queryRef.current.page + 1, leads.total, leads.page_size))}>Próxima</button>
              </div>
            </div>
          </section>
          <footer className="page-footer"><span>VendeMais</span> <span>Inteligência para vender melhor.</span></footer>
        </main>
      </div>
    </div>
  );
}

export default App;
