const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "..", "src", "scorePresentation.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const exportsForTest = {};
vm.runInNewContext(compiled, { exports: exportsForTest });
const { scorePresentation } = exportsForTest;

test("scores have distinct labels at each threshold including decimals", () => {
  for (const [score, kind, label] of [
    [null, "missing", "Sem pontuação"],
    [0, "low", "Baixa"], [49, "low", "Baixa"], [49.9, "low", "Baixa"],
    [50, "medium", "Média"], [79, "medium", "Média"], [79.9, "medium", "Média"], [79.9999, "medium", "Média"],
    [80, "high", "Alta"], [100, "high", "Alta"],
  ]) {
    const result = scorePresentation(score);
    assert.equal(result.kind, kind, `score ${score}`);
    assert.equal(result.label, label, `score ${score}`);
  }
});
