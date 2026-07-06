# Mirror n8n — VendeMais Lead Enrichment

O cenário "de verdade" da VendeMais vive no **Make.com**, que é SaaS e **não roda local**.
Este mirror reproduz os **mesmos 5 passos** em **n8n** (auto-hospedável via Docker) para
você conseguir **testar o fluxo de fato** antes de mexer no Make corporativo.

> Não é o sistema de produção. É um espelho de aprendizado. As credenciais aqui são
> placeholders — **nunca** coloque chave real neste JSON (a Joana colocou a dela e por
> isso ela virou dívida técnica; ver `## Dívida técnica herdada` no README principal).

## Dois workflows nesta pasta

| Arquivo | O que é | Precisa de credencial / ferramenta paga? |
|---------|---------|-------------------------------------------|
| `workflows/vendemais-enrich-v0.json` | Mirror **real**: os 5 passos com os nodes de verdade (Google CSE, OpenAI, Airtable, HubSpot). Mostra a arquitetura herdada + a dívida técnica. | **Sim** — os passos 2–5 exigem chaves/contas. Sem elas só os passos 1–2 rodam. |
| `workflows/vendemais-enrich-local.json` | Versão **100% offline**: os 4 nodes de serviço externo viraram **Code nodes mockados**. Roda **de ponta a ponta sem nenhuma credencial nem custo**. | **Não** — zero chave, zero download, zero ferramenta paga. |

Os dois têm os **mesmos nomes de node** e o **mesmo encadeamento** — dá pra abrir lado a
lado e ver exatamente o que foi mockado. No offline, cada Code node traz um comentário
dizendo onde plugar o serviço real (inclusive um modelo GPT pequeno da OpenAI no passo 3).

### Rodar a versão offline (recomendado no 1º contato)

1. Importe `workflows/vendemais-enrich-local.json` (menu **(...) → Import from File**).
2. Ative no botão **Publish / Active**.
3. Dispare — a resposta já traz o JSON enriquecido (o webhook responde com o último node):

```bash
curl -X POST http://localhost:5678/webhook/lead-enrich-local \
  -H "Content-Type: application/json" \
  -d '{"deal_id": "9876543210", "company": "Acme Logística SA"}'
```

Resposta esperada (o `icp_match_score` é derivado do `deal_id`, então é determinístico
e igual em qualquer SO/terminal):

```json
{
  "status": "enriched",
  "hubspot_update": "ok (MOCK)",
  "deal_id": "9876543210",
  "icp_match_score": 60,
  "industry": "Logistica",
  "message": "Deal 9876543210 enriquecido offline (sem custo). Score ICP = 60."
}
```

> O `path` do webhook offline é `lead-enrich-local` (o do mirror real é `lead-enrich`),
> então os dois podem ficar ativos ao mesmo tempo sem conflito.

## Os 5 passos (mesmos do Make)

| # | Make (produção)            | n8n (mirror)                         | Node n8n                       |
|---|----------------------------|--------------------------------------|--------------------------------|
| 1 | HubSpot · Watch Deals      | Webhook `POST /webhook/lead-enrich`  | `n8n-nodes-base.webhook`       |
| 2 | Google Search              | HTTP Request (Google CSE)            | `n8n-nodes-base.httpRequest`   |
| 3 | OpenAI · Chat Completion   | OpenAI · Chat                        | `n8n-nodes-base.openAi`        |
| 4 | Airtable · Create Record   | Airtable · Append                    | `n8n-nodes-base.airtable`      |
| 5 | HubSpot · Update Deal      | HubSpot · Update Deal                | `n8n-nodes-base.hubspot`       |

O passo 1 vira **Webhook** de propósito: assim dá pra disparar o fluxo com um `curl`,
sem precisar configurar o trigger nativo do HubSpot. É a mesma realidade do herdado:
o scheduler está **OFF**, então roda na mão.

## Subir o mirror

```bash
cd n8n-mirror
docker compose up -d
```

Abre em <http://localhost:5678>. **No primeiro acesso** o n8n mostra a tela
**"Set up owner account"** — crie uma conta local (email + senha quaisquer, ex.:
`owner@vendemais.local` / `VendeMais2026`). Isso fica só na sua máquina.

> ℹ️ O antigo login `admin`/`admin` (basic auth) **foi removido** no n8n v1/v2.
> Por isso o `docker-compose.yml` fixa a versão `2.28.7` — a tag `:latest` muda
> sozinha e volta a quebrar este passo.

## Importar o workflow

1. No n8n: menu **(...) → Import from File**.
2. Selecione `workflows/vendemais-enrich-v0.json`.
3. Configure as credenciais (OpenAI, Airtable, HubSpot) nos nodes — elas **não vêm**
   no JSON (igual ao Make, onde conexões não exportam). Sem credencial real, os passos
   3–5 vão falhar; o passo 1–2 já dá pra inspecionar.
4. Ative o workflow no botão **Publish / Active** (canto superior direito) — senão o
   webhook dá `404`. (No n8n 2.x o botão se chama **Publish**; em versões antigas era **Active**.)

## Teste manual (sem chamar API real)

Dispara o webhook com um lead falso:

```bash
curl -X POST http://localhost:5678/webhook/lead-enrich \
  -H "Content-Type: application/json" \
  -d '{"deal_id": "9876543210", "company": "Acme Logística SA"}'
```

- `200` + execução visível em **Executions** = webhook + montagem do fluxo OK.
- `404` = workflow não está **Active**.
- Falha no node OpenAI/Airtable/HubSpot = credencial faltando (esperado neste mirror).

Para validar a **lógica** (montagem do prompt + parsing do fit-score) **sem subir nada
e sem API**, use o teste mockado em `../tests/test_enrichment_logic.py` (ver README principal).

## Parar

```bash
docker compose down        # mantém o volume n8n_data
docker compose down -v     # apaga tudo (workflows e credenciais locais)
```

## Não faça

- Não commite credencial real neste JSON nem no `.env`.
- Não trate este mirror como produção — produção é o Make corporativo.
