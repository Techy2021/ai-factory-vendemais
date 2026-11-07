const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

function loadApi(fetch, viteEnv = { DEV: true }) {
  const source = fs.readFileSync(path.join(__dirname, "..", "src", "api.ts"), "utf8")
    .replaceAll("import.meta.env", "viteEnv");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const exports = {};
  const configSource = fs.readFileSync(path.join(__dirname, "..", "src", "apiConfig.ts"), "utf8");
  const config = {};
  vm.runInNewContext(ts.transpileModule(configSource, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText, { exports: config, URL, Error });
  vm.runInNewContext(compiled, {
    exports, fetch, URLSearchParams, Error, viteEnv,
    require: (name) => {
      if (name !== "./apiConfig") throw new Error("Unexpected import");
      return config;
    },
  });
  return exports;
}

test("the API client uses the configured production origin and fails closed if absent", async () => {
  const calls = [];
  const fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true };
  };
  const api = loadApi(fetch, { DEV: false, VITE_API_BASE_URL: "https://api.example.test" });
  await api.logout();
  assert.equal(calls[0].url, "https://api.example.test/auth/logout");
  assert.equal(calls[0].options.credentials, "include");
  assert.throws(() => loadApi(fetch, { DEV: false }));
});

test("401 invalidates the session without waiting for the other request", async () => {
  for (const unauthorizedPath of ["/api/leads", "/api/metrics"]) {
    const calls = [];
    const api = loadApi((url, options) => {
      calls.push({ url, options });
      if (url.includes(unauthorizedPath)) {
        return Promise.resolve({ ok: false, status: 401 });
      }
      return new Promise((_, reject) => {
        options.signal.addEventListener("abort", () => reject(new Error("aborted")));
      });
    });
    const controller = new AbortController();
    let invalidations = 0;
    await api.fetchDashboard({ startDate: "", endDate: "" }, 1, controller.signal, () => {
      invalidations += 1;
      controller.abort();
    });
    assert.equal(invalidations, 1);
    assert.equal(calls.length, 2);
    for (const call of calls) {
      assert.match(call.url, /^http:\/\/localhost:8001\/api\//);
      assert.equal(call.options.credentials, "include");
    }
  }
});

test("login and logout include credentials and propagate authentication failures", async () => {
  const calls = [];
  const api = loadApi(async (url, options) => {
    calls.push({ url, options });
    return { ok: !url.endsWith("/auth/login"), status: 401 };
  });
  await assert.rejects(api.login("synthetic"), (error) => error.status === 401);
  await api.logout();
  assert.equal(calls.length, 2);
  for (const call of calls) {
    assert.equal(call.options.credentials, "include");
    assert.match(call.url, /^http:\/\/localhost:8001\/auth\//);
  }
});
