# Lead Enrichment VendeMais — passagem de bastão da Joana

Oi! Sou a Joana 👋

Esse era meu projeto de estágio na VendeMais (durou um semestre). Foi pra produção no fim daquele semestre e tá rodando — bom, *tava* rodando, agora eu acho que a Cláudia desligou porque saiu do meu controle quando eu fui embora.

## O que é

Um cenário no **Make.com** (Stack C) que:

1. Observa novos deals no HubSpot que entram em `appointmentscheduled`
2. Pesquisa a empresa no Google Search
3. Manda resultados pro OpenAI (um modelo GPT pequeno) gerar um JSON com industry, tech stack, ICP score etc.
4. Grava o resultado numa tabela do Airtable
5. Atualiza o deal no HubSpot com o `icp_match_score`

São **5 módulos** em linha: HubSpot → Google → OpenAI → Airtable → HubSpot.

## O que tem nessa pasta agora

```
vendemais-lead-enrich/
├── workflows/
│   └── vendemais-make-blueprint.json   ← blueprint Make.com IMPORTÁVEL (reconstruí do pseudo + screenshots)
├── n8n-mirror/                         ← espelho do MESMO fluxo em n8n (roda local p/ testar de verdade)
│   ├── docker-compose.yml
│   ├── workflows/vendemais-enrich-v0.json     ← mirror REAL (precisa de credenciais)
│   ├── workflows/vendemais-enrich-local.json  ← versão OFFLINE (roda verde sem custo)
│   └── README.md
├── tests/
│   ├── validate_workflows.py           ← valida estrutura dos 2 JSON
│   └── test_enrichment_logic.py        ← lógica do prompt + parsing do fit-score (LLM mockado)
├── docs/                               ← schema Airtable, notas, screenshots (texto)
├── make-blueprint-pseudo.txt
├── BRIEFING.md  ·  CHANGELOG.md  ·  .env.example  ·  .gitignore
```

> **Por que dois artefatos?** O Make.com é SaaS, **não roda local** — então não dá pra
> testar de verdade só com ele. O `n8n-mirror/` reproduz os mesmos 5 passos em n8n
> (auto-hospedável via Docker) pra você conseguir importar, disparar e inspecionar o fluxo.

## Como importar / rodar — Make.com (produção)

1. Abra o Make.com na **conta corporativa** da VendeMais (não na minha pessoal!).
2. **Create a new scenario → ⋯ (mais opções) → Import Blueprint**.
3. Suba `workflows/vendemais-make-blueprint.json`.
4. **Reconfigure as conexões na mão** — elas **não vêm** no JSON (limitação do Make):
   HubSpot OAuth, Google CSE, OpenAI API key e Airtable PAT. No blueprint cada módulo
   está com `__IMTCONN__: 0` (desconectado) de propósito.
5. O scheduler está **OFF** no blueprint. Pra testar uma vez: **Run once**.

## Como importar / rodar — mirror n8n (teste local)

```bash
cd n8n-mirror
docker compose up -d          # sobe o n8n em http://localhost:5678
```

Depois: importe `n8n-mirror/workflows/vendemais-enrich-v0.json` pelo menu **Import from File**,
configure credenciais nos nodes, ative o workflow e dispare:

```bash
curl -X POST http://localhost:5678/webhook/lead-enrich \
  -H "Content-Type: application/json" \
  -d '{"deal_id": "9876543210", "company": "Acme Logística SA"}'
```

Passo a passo completo em [`n8n-mirror/README.md`](n8n-mirror/README.md).

## Como rodar os testes (não chamam API nenhuma)

```bash
python tests/validate_workflows.py      # estrutura dos 2 JSON
python tests/test_enrichment_logic.py   # prompt + parsing do fit-score (LLM mockado)
```

## Sobre o LLM

Hoje é **um modelo GPT pequeno da OpenAI** (`temperature 0.3`, `max_tokens 1500`, `response_format: json_object`).
Dá pra trocar por **Anthropic Claude** sem mudar a arquitetura: no Make use o módulo
`anthropic:createMessage`; no n8n troque o node OpenAI por um **HTTP Request** batendo em
`https://api.anthropic.com/v1/messages` (mesmo system/user prompt). O JSON de saída é o mesmo.

## Dívida técnica herdada

Coisas que ficaram **propositalmente sem resolver** (é o que vocês vão corrigir no curso).
Estão aqui, marcadas, pra ninguém ser pego de surpresa. **Não "arrumei" nada disso** —
detalhes e ordem de urgência em [`docs/notas-joana.md`](docs/notas-joana.md).

1. **Scheduler OFF / roda manual.** No Make o trigger era poll de 15min, hoje desligado;
   alguém clica "Run once" todo dia. No mirror n8n o workflow vem `active: false` e você
   dispara via curl. Mesma realidade: nada roda sozinho.
2. **API key pessoal da Joana.** OpenAI no meu cartão (~US$ 18/mês), Google CSE no meu
   billing, Airtable PAT meu. No mirror tem até uma chave de exemplo *hardcoded* no JSON
   (não é real, mas mostra o anti-padrão). Tudo precisa virar conta corporativa.
3. **Zero tratamento de erro.** Se a OpenAI devolve JSON quebrado, o cenário morre
   silencioso (já aconteceu ~3x). Sem branch de falha, sem retry custom, sem alerta no Slack.
4. **Sem versionamento Git originalmente.** Foi tudo clicado no Make. Não havia export do
   blueprint nem histórico — esse repo é o primeiro passo pra mudar isso.
5. **Sem instrumentação de custo.** Não tem campo `cost_usd` no Airtable nem cálculo de
   tokens por execução. Prompts estouram 8k tokens (snippets do Google não são truncados).
   Impossível auditar custo por lead hoje.
6. **Sem mapa LGPD de transferência internacional.** Dados de empresa-cliente passam por
   Google + OpenAI nos EUA. Levantei a bandeira pro jurídico, nunca responderam.
7. **Schema Airtable problemático.** `tech_stack` como *Multiple select* explode opções
   (400+, duplicadas), sem unique constraint em `deal_id` (gera linhas duplicadas),
   `raw_search_results` pesado (~80% da quota). Ver [`docs/airtable-schema.md`](docs/airtable-schema.md).

## Avisos importantes (por favor lê isso)

- O cenário Make tá no **meu espaço pessoal** (`joana@vendemais.com`). Vão precisar
  **migrar pra conta corporativa** — o Make não migra workspace, vocês recriam/importam blueprint.
- As **conexões não saem** no blueprint JSON do Make (tem que reconfigurar OAuth/PAT na mão).
- Anexei **screenshots descritos em texto** em `docs/cenario-make-screenshots/` e o
  **pseudo-blueprint** em `make-blueprint-pseudo.txt` (foi a base do JSON real).

## Se travarem

Me chama no LinkedIn (Joana M.), respondo quando puder. Tô em Lisboa fazendo mestrado, fuso +4h.

Boa sorte! O projeto é bem legal, os AEs amam o score. 💛

— Joana
