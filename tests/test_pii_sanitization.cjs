// Synthetic fixtures only. Executes the exact regexp rules stored in the Make blueprint.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const file = 'workflows/vendemais-make-blueprint.json';
const blueprint = JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const step = blueprint.flow.find(m => m.id === 29);
const expression = step.mapper.value;
const rules = [...expression.matchAll(/; "((?:\\"|[^"])*)"; "([^"]*)"\)/g)].map(m => {
  const literal = m[1].replace(/\\"/g, '"');
  const end = literal.lastIndexOf('/');
  return [new RegExp(literal.slice(1, end), literal.slice(end + 1)), m[2]];
});
assert.equal(rules.length, 5);
let reconstructed = 'toJSON(8.data)';
for (const [pattern, replacement] of rules) {
  reconstructed = `replace(${reconstructed}; "${pattern.toString().replace(/"/g, '\\"')}"; "${replacement}")`;
}
assert.equal(expression, `{{${reconstructed}}}`);
function sanitize(data) {
  return rules.reduce((text, [pattern, replacement]) => text.replace(pattern, replacement), JSON.stringify(data));
}
const cases = [
  ['email global/case', 'ana@example.test e BIA@EXAMPLE.TEST', '[EMAIL] e [EMAIL]'],
  ['formatted CPF', 'CPF: 000.000.000-00.', 'CPF: [CPF_OU_NUMERO_PESSOAL].'],
  ['bare CPF', 'CPF: 00000000000', 'CPF: [CPF_OU_NUMERO_PESSOAL]'],
  ['phone international', 'Tel: +55 (11) 00000-0000', 'Tel: [TELEFONE]'],
  ['phone landline', 'Tel: (11) 0000-0000', 'Tel: [TELEFONE]'],
  ['local formatted phone', 'Tel: 00000-0000', 'Tel: [TELEFONE]'],
  ['labeled full name', 'Nome completo: Pessoa Sintética. Empresa: Acme Labs.', 'Nome completo: [NOME]. Empresa: Acme Labs.'],
  ['name with particle', 'Responsável: Pessoa de Teste; AWS', 'Responsável: [NOME]; AWS'],
  ['business context', 'Acme Labs: 250 funcionários, receita R$ 12.500.000; AWS, HubSpot, Série B.', 'Acme Labs: 250 funcionários, receita R$ 12.500.000; AWS, HubSpot, Série B.'],
  ['no arbitrary name guessing', 'Acme Labs e Pessoa Sintética', 'Acme Labs e Pessoa Sintética'],
  ['long numeric identifier', 'ID: 1234567890123456', 'ID: 1234567890123456'],
  ['empty', '', ''],
];
for (const [name, input, expected] of cases) {
  assert.equal(JSON.parse(sanitize(input)), expected, name);
}
const nested = {web: {results: [{title: 'Acme Labs', description: 'Nome completo: Pessoa Sintética. ana@example.test', url: 'https://example.test/ana@example.test'}]}, other: 'CPF 000.000.000-00'};
const cleaned = sanitize(nested);
assert(!cleaned.includes('ana@example.test'));
assert(!cleaned.includes('Pessoa Sintética'));
assert(!cleaned.includes('000.000.000-00'));
assert(cleaned.includes('Acme Labs'));
assert.equal(sanitize(null), 'null');
const ids = blueprint.flow.map(m => m.id);
assert.equal(ids[ids.indexOf(18) - 1], 29);
assert.equal(ids[ids.indexOf(29) - 1], 8);
assert.equal(step.module, 'util:SetVariable2');
assert.equal(step.mapper.name, 'sanitized_search');
const gemini = blueprint.flow.find(m => m.id === 18);
assert(gemini.mapper.textPrompt.startsWith('{{29.sanitized_search}}'));
assert(!gemini.mapper.textPrompt.includes('{{8.'));
// Ensure all prior mappings, parameters and prompt instructions remain identical.
const before = JSON.parse(execFileSync('git', ['show', `HEAD:${file}`], {cwd: root, encoding: 'utf8'}));
const restored = structuredClone(blueprint);
restored.flow = restored.flow.filter(m => m.id !== 29);
restored.flow.find(m => m.id === 18).mapper.textPrompt = gemini.mapper.textPrompt.replace('{{29.sanitized_search}}', '{{8.data}}{{8.data.web}}{{8.data.web.results}}');
assert.deepEqual(restored, before);
console.log(`PASS: ${cases.length} synthetic cases; nested payload/null; pre-LLM routing; unchanged original modules.`);
