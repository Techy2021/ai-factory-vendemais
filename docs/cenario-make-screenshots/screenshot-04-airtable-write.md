# Screenshot 04 — Airtable Create Record

*(descrição textual)*

Quarto módulo, círculo amarelo com ícone do Airtable.

**Configuração visível:**

- **Módulo:** `Airtable > Create a Record`
- **Connection:** `Joana Airtable PAT` (Personal Access Token criado com a conta corporativa, MAS o token tá no espaço Make pessoal da Joana)
- **Base:** `VendeMais CRM` (base ID: `appXXXXXXXXXX` — está na conta corporativa Airtable, ok)
- **Table:** `Lead Enrichment`

**Mapeamento de campos (do JSON parseado do OpenAI):**

| Campo Airtable      | Origem (Make mapping)                              |
| ------------------- | -------------------------------------------------- |
| `deal_id`           | `{{1.id}}` (HubSpot)                               |
| `company_name`      | `{{1.properties.company}}`                         |
| `industry`          | `{{3.choices[].message.content.industry}}`         |
| `size_employees`    | `{{3.choices[].message.content.size_employees}}`   |
| `tech_stack`        | `{{3.choices[].message.content.tech_stack}}` (join `,`) |
| `buying_signals`    | `{{3.choices[].message.content.buying_signals}}`   |
| `icp_match_score`   | `{{3.choices[].message.content.icp_match_score}}`  |
| `talking_points`    | `{{3.choices[].message.content.talking_points}}`   |
| `enriched_at`       | `{{now}}`                                          |
| `raw_search_results`| `{{2.items}}` (serializado pra debug)              |

**Observação Joana:**
> "Tem um parser de JSON antes desse módulo (não tá no print) que pega o `choices[0].message.content` e converte de string pra objeto. Às vezes a OpenAI devolve JSON quebrado e dá erro — sem error handling, o cenário só morre."
