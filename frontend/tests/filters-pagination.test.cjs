const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

function loadModule(name, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, "..", "src", name), "utf8")
    .replaceAll("import.meta.env", "viteEnv");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const exports = {};
  vm.runInNewContext(compiled, {
    exports, URLSearchParams, URL, Error, viteEnv: { DEV: true },
    require: (moduleName) => {
      if (moduleName !== "./apiConfig") throw new Error("Unexpected import");
      return loadModule("apiConfig.ts");
    },
    ...globals,
  });
  return exports;
}

test("applying a filter resets the page and identical filters do not create a new query", () => {
  const { applyPeriod } = loadModule("query.ts");
  const query = { period: { startDate: "2026-03-01", endDate: "2026-03-31" }, page: 3 };
  const reset = applyPeriod(query, query.period);
  assert.equal(reset.page, 1);
  assert.equal(applyPeriod(reset, { ...query.period }), reset);
  const changed = applyPeriod(reset, { startDate: "", endDate: "2026-04-01" });
  assert.equal(changed.page, 1);
  assert.equal(changed.period.startDate, "");
  assert.equal(changed.period.endDate, "2026-04-01");
});

test("navigation is bounded for empty, partial and shrinking result sets", () => {
  const { changePage, lastPage } = loadModule("query.ts");
  const query = { period: { startDate: "", endDate: "" }, page: 1 };
  assert.equal(lastPage(0, 10), 1);
  assert.equal(lastPage(21, 10), 3);
  assert.equal(changePage(query, 0, 0, 10), query);
  assert.equal(changePage(query, 2, 0, 10), query);
  const finalPage = changePage(query, 99, 21, 10);
  assert.equal(finalPage.page, 3);
  assert.equal(changePage(finalPage, 3, 10, 10).page, 1);
  assert.equal(changePage(finalPage, 2, 21, 10).page, 2);
});

test("dates without timezone follow the API's UTC convention", () => {
  const originalTimezone = process.env.TZ;
  process.env.TZ = "America/Sao_Paulo";
  try {
    const { formatDateUtc } = loadModule("query.ts");
    assert.equal(formatDateUtc("2026-03-01T23:30:00"), "01/03/2026");
    assert.equal(formatDateUtc("2026-03-01T23:30:00-03:00"), "02/03/2026");
    assert.equal(formatDateUtc(null), "—");
    assert.equal(formatDateUtc("invalid"), "Data inválida");
  } finally {
    if (originalTimezone === undefined) delete process.env.TZ;
    else process.env.TZ = originalTimezone;
  }
});

test("both endpoints use the same period and leads use the selected page", async () => {
  const calls = [];
  const api = loadModule("api.ts", {
    fetch: async (url, options) => {
      calls.push({ url: new URL(url), options });
      return {
        ok: true,
        json: async () => url.includes("/api/metrics")
          ? { leads_total: 0, average_score: null, missing_score_count: 0, unique_deals: 0 }
          : { items: [], total: 0, page: 2, page_size: 10 },
      };
    },
  });
  const signal = new AbortController().signal;
  const [metrics, leads] = await api.fetchDashboard(
    { startDate: "2026-03-01", endDate: "2026-03-31" }, 2, signal, () => assert.fail("unexpected 401"),
  );
  assert.equal(metrics.status, "fulfilled");
  assert.equal(metrics.value.leads_total, 0);
  assert.equal(metrics.value.average_score, null);
  assert.equal(leads.status, "fulfilled");
  assert.equal(leads.value.items.length, 0);
  assert.equal(calls.length, 2);
  for (const call of calls) {
    assert.equal(call.url.searchParams.get("start_date"), "2026-03-01");
    assert.equal(call.url.searchParams.get("end_date"), "2026-03-31");
    assert.equal(call.options.credentials, "include");
    assert.equal(call.options.signal, signal);
  }
  const leadsCall = calls.find((call) => call.url.pathname === "/api/leads");
  assert.equal(leadsCall.url.searchParams.get("page"), "2");
  assert.equal(leadsCall.url.searchParams.get("page_size"), "10");
  const metricsCall = calls.find((call) => call.url.pathname === "/api/metrics");
  assert.equal(metricsCall.url.searchParams.has("page"), false);
});

test("a stale 401 after cancellation does not invalidate the current session", async () => {
  const pending = [];
  const api = loadModule("api.ts", {
    fetch: () => new Promise((resolve) => pending.push(resolve)),
  });
  const controller = new AbortController();
  let invalidations = 0;
  const result = api.fetchDashboard({ startDate: "", endDate: "" }, 1, controller.signal, () => invalidations++);
  controller.abort();
  for (const resolve of pending) resolve({ ok: false, status: 401 });
  await result;
  assert.equal(invalidations, 0);
});
