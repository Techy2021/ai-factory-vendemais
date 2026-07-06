# Schema Airtable — Base `VendeMais CRM`, tabela `Lead Enrichment`

Base ID: `appXXXXXXXXXX` (conta Airtable corporativa — ok, esse ativo já está com a VendeMais)
Tabela: `Lead Enrichment`

## Campos

| Campo                 | Tipo Airtable          | Notas                                                                |
| --------------------- | ---------------------- | -------------------------------------------------------------------- |
| `deal_id`             | Single line text       | **Primary field**. ID do deal no HubSpot. Idealmente único.          |
| `company_name`        | Single line text       | Vem direto de `properties.company` do HubSpot.                       |
| `industry`            | Single line text       | Saída do LLM.                                                        |
| `size_employees`      | Single line text       | LLM devolve faixa tipo `"100-500"` ou número aproximado.             |
| `tech_stack`          | Multiple select        | Opções criadas dinamicamente (cuidado: Airtable cria option nova a cada novo valor — vira zona). |
| `buying_signals`      | Long text              | Texto corrido com sinais detectados (ex.: "abriu vaga de CTO", "captou Série B"). |
| `icp_match_score`     | Number (integer, 0–100)| Score de fit com ICP da VendeMais.                                   |
| `talking_points`      | Long text              | Bullet points pro AE usar na call.                                   |
| `enriched_at`         | Date (with time)       | Timestamp da execução. Setado via `{{now}}` do Make.                 |
| `raw_search_results`  | Long text              | JSON serializado dos 5 resultados do Google. **Debug only** — pesado, considerar TTL. |

## Problemas conhecidos do schema

- **`tech_stack` como Multiple select**: cada novo valor único cria opção nova no Airtable. Já tem 400+ opções, muitas duplicadas (`"AWS"`, `"Amazon Web Services"`, `"aws"`).
- **Sem unique constraint** em `deal_id`: deal re-enriquecido gera linha duplicada.
- **`raw_search_results` ocupa espaço**: base tá em ~80% da quota do plano Airtable Team.
- **Sem campo `cost_usd`** por execução — impossível auditar custo por lead hoje.
