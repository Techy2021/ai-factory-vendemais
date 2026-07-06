# Screenshot 02 — Google Search

*(descrição textual)*

Segundo módulo do cenário, círculo azul com ícone do Google.

**Configuração visível:**

- **Módulo:** `Google Search > Search`
- **Connection:** `Joana Google Custom Search API` (cx pessoal da Joana, key pessoal)
- **Search engine ID (cx):** `017576662512468239146:omuauf_lfve` (genérico web-wide)
- **Query (construída dinamicamente com mapeamento Make):**

```
{{1.properties.company}} headquarters employees revenue technology stack
```

Onde `{{1.properties.company}}` vem do módulo anterior (HubSpot Watch Deals).

- **Number of results:** `5`
- **Safe search:** `off`
- **Language:** `pt-BR` (mas Joana anotou: "deveria ser auto, muita empresa tem site só em inglês")

**Output esperado (array):**

```
[
  { "title": "...", "link": "...", "snippet": "..." },
  ... (5 itens)
]
```

**Observação Joana:**
> "Custom Search API tem free tier de 100 queries/dia. A gente passa disso fácil com 5k leads/mês. Configurei billing no meu Google Cloud pessoal pra não dar erro — sai uns US$ 5 por mil queries extras."
