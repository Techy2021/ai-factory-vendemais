# Screenshot 01 — Trigger HubSpot (Watch Deals)

*(descrição textual do print que a Joana tinha no Notion)*

Tela do editor visual do Make.com. O primeiro módulo do cenário, círculo laranja com o logo do HubSpot.

**Configuração visível no painel lateral direito:**

- **Módulo:** `HubSpot > Watch Deals`
- **Connection:** `Joana HubSpot Personal` ⚠️ (conta `joana@vendemais.com` — pessoal!)
- **Watch Deals by:** `Updated date`
- **Filter:**
  - Property: `dealstage`
  - Operator: `equals`
  - Value: `appointmentscheduled`
- **Limit:** `100` registros por execução
- **Include fields:**
  - `dealname`
  - `company` (associação)
  - `amount`
  - `hubspot_owner_id`
  - `createdate`

**Schedule (canto inferior esquerdo do cenário):**

- `Run scenario`: **a cada 15 minutos**
- Status atual no print: 🔴 **OFF** (Cláudia desligou no fim do ano passado)

**Observação manuscrita da Joana no Notion:**
> "Esse trigger às vezes pega o mesmo deal 2x se alguém edita o stage. Coloquei um filter logo depois pra deduplicar pelo deal_id mas não tá no print."
