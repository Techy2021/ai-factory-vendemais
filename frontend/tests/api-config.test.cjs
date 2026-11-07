const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "..", "src", "apiConfig.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
function createResolver(origin) {
  const exportsForTest = {};
  const context = { exports: exportsForTest, URL, Error };
  if (origin !== undefined) context.window = { location: { origin } };
  vm.runInNewContext(compiled, context);
  return exportsForTest.resolveApiBase;
}

const resolveApiBase = createResolver();

test("development defaults locally and accepts explicit loopback HTTP", () => {
  assert.equal(resolveApiBase(undefined, true), "http://localhost:8001");
  assert.equal(resolveApiBase("", true), "http://localhost:8001");
  assert.equal(resolveApiBase("http://127.0.0.1:8001/", true), "http://127.0.0.1:8001");
  assert.equal(resolveApiBase("http://[::1]:8001", true), "http://[::1]:8001");
  assert.equal(resolveApiBase("https://api.example.test/", true), "https://api.example.test");
});

test("production uses the browser HTTPS origin when configuration is absent", () => {
  const resolveInBrowser = createResolver("https://dashboard.example.test:8443");
  for (const value of [undefined, "", " "]) {
    assert.equal(resolveInBrowser(value, false), "https://dashboard.example.test:8443");
  }
  assert.equal(resolveInBrowser(undefined, true), "http://localhost:8001");
});

test("production accepts explicit HTTPS without a browser", () => {
  assert.equal(resolveApiBase("https://api.example.test:8443/", false), "https://api.example.test:8443");
  assert.equal(
    createResolver("http://dashboard.example.test")("https://api.example.test", false),
    "https://api.example.test",
  );
  for (const value of ["http://localhost:8001", "http://api.example.test", "/api", "not-a-url"]) {
    assert.throws(() => resolveApiBase(value, false));
  }
});

test("production rejects missing browser context and non-HTTPS browser origins", () => {
  for (const value of [undefined, "", " "]) {
    assert.throws(() => resolveApiBase(value, false), /contexto de navegador/);
    for (const origin of [
      "http://localhost:8001", "http://dashboard.example.test", "null", "file://",
      "https://dashboard.example.test/path", "not-a-url",
    ]) {
      assert.throws(() => createResolver(origin)(value, false), /origem do navegador/);
    }
  }
});

test("rejects unsafe URLs in both environments", () => {
  const resolveInBrowser = createResolver("https://dashboard.example.test");
  for (const value of [
    "http://api.example.test", "https://user:pass@api.example.test",
    "https://api.example.test/path", "https://api.example.test/?a=b",
    "https://api.example.test/#fragment", "javascript:alert(1)",
  ]) {
    for (const development of [true, false]) {
      assert.throws(() => resolveApiBase(value, development));
      assert.throws(() => resolveInBrowser(value, development));
    }
  }
});
