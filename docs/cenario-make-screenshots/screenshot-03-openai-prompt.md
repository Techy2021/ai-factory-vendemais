# Screenshot 03 — OpenAI Chat Completion

*(descrição textual — o print mais importante pra auditar)*

Terceiro módulo, círculo preto com ícone da OpenAI.

**Configuração visível:**

- **Módulo:** `OpenAI > Create a Chat Completion`
- **Connection:** `Joana OpenAI Personal` ⚠️ (sk-... pessoal da Joana, billing no cartão pessoal dela)
- **Model:** um modelo GPT pequeno da OpenAI (migrou de um modelo maior recentemente pra economizar)
- **Max tokens:** `1500`
- **Temperature:** `0.3`
- **Response format:** `json_object`

**Messages:**

- **role:** `system`
  **content:**
  ```
  Você é um analista de inteligência de vendas B2B. Sempre responde em JSON válido, sem texto antes ou depois.
  ```

- **role:** `user`
  **content (prompt completo — texto integral do print):**
  ```
  "Você é um analista de inteligência de vendas. Recebeu o nome da empresa: {{company_name}}
  e os resultados de busca: {{search_results}}. Retorne em JSON:
  {
    "industry": "...",
    "size_employees": "...",
    "tech_stack": [...],
    "buying_signals": [...],
    "icp_match_score": 0-100,
    "talking_points": [...]
  }
  "
  ```

Onde:
- `{{company_name}}` ← do módulo 1 (HubSpot)
- `{{search_results}}` ← array completo do módulo 2 (Google), serializado como JSON string

**Observação Joana:**
> "Tem prompt que estoura 8k tokens fácil porque os snippets do Google vêm gigantes. Já vi execução custando US$ 0,02 — vezes 5k leads/mês dá US$ 100. Não tá dentro do budget. Precisa truncar os snippets antes."
