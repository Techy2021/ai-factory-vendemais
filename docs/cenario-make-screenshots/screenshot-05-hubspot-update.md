# Screenshot 05 — HubSpot Update Deal

*(descrição textual)*

Quinto e último módulo do cenário, novamente o círculo laranja do HubSpot.

**Configuração visível:**

- **Módulo:** `HubSpot > Update a Deal`
- **Connection:** `Joana HubSpot Personal` (mesma do trigger, pessoal!)
- **Deal ID:** `{{1.id}}` (do trigger)

**Campos a atualizar:**

| Property HubSpot (interna)    | Valor mapeado                                       |
| ----------------------------- | --------------------------------------------------- |
| `icp_match_score`             | `{{3.choices[].message.content.icp_match_score}}`   |
| `enrichment_industry`         | `{{3.choices[].message.content.industry}}`          |
| `enrichment_last_run`         | `{{now}}`                                           |
| `enrichment_status`           | `"enriched"` (literal)                              |

**Custom properties criadas no HubSpot (Joana setup manual):**

- `icp_match_score` — Number, 0–100, visível no card do deal
- `enrichment_industry` — Single-line text
- `enrichment_last_run` — Date picker
- `enrichment_status` — Dropdown (`pending`, `enriched`, `failed`)

**Observação Joana:**
> "Adicionei esse módulo só na v0.3 (dezembro). Antes disso o score ficava só no Airtable e ninguém olhava. Quando começou a aparecer no card do deal os AEs adoraram. Mas note: se o cenário falha no módulo 3 (OpenAI), o `enrichment_status` fica eternamente em `pending` — não tem fallback pra marcar `failed`."
