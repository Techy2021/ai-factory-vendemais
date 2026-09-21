# Changelog

## [v1.0.0] - Etapa 1
- Consolidado o blueprint Make com seis módulos: HubSpot → Brave Search → Gemini → JSON → Airtable → HubSpot.
- Documentadas a arquitetura escolhida, a utilização do Make em produção, os ADRs e os diagramas C4; referências antigas aos provedores sinalizadas no README.
- Registrados os smoke tests locais e as 15 verificações aprovadas; CI executada com sucesso no GitHub Actions.
- Implementado e validado o CD pela branch `main`, com sincronização do blueprint pela Make API e uso de GitHub Secrets para `MAKE_API_KEY` e `BRAVE_SEARCH_API_KEY`, substituindo o placeholder Brave Search somente em memória.
- Verificado o cenário no Make após o deploy, preservando os seis módulos e os principais mapeamentos.
- Executado Gitleaks no estado atual e no histórico Git: nenhum achado no working tree após a correção; permanece apenas o falso positivo do exemplo antigo no histórico.
- Substituído o valor de exemplo do campo `apiKey` do módulo OpenAI em `n8n-mirror/workflows/vendemais-enrich-v0.json` por `OPENAI_API_KEY_EXAMPLE`, sem alterar a lógica do workflow.

## [etapa-1]
- Incluída a auditoria do protótipo.
- Incluída a matriz de decisão de stack.
- Incluídos o ADR-001 (escolha da stack) e o ADR-002 (ambiente de produção).
- Incluídos os diagramas C4 de nível 1 (contexto) e nível 2 (containers).
- Adicionadas no README as referências aos documentos da Etapa 1.

## [v0.4-handoff] (RevOps, herdando da Joana)
- Reconstruído o **blueprint Make.com importável** (`workflows/vendemais-make-blueprint.json`) a partir do pseudo-blueprint + screenshots. 5 módulos.
- Adicionado **mirror n8n** auto-hospedável (`n8n-mirror/`: docker-compose + workflow + README) para testar o mesmo fluxo localmente.
- Adicionados **testes** (`tests/`): validador estrutural dos 2 JSON + teste de lógica com LLM mockado (prompt + parsing do fit-score).
- Primeiro **versionamento Git** do projeto (antes era tudo clicado no Make).
- `.env.example` e `.gitignore` corrigidos.
- Dívida técnica herdada **documentada** no README (não corrigida — material do curso).

## [v0.3-joana]
- Adicionado módulo HubSpot Update (atualiza score no deal)
- icp_match_score agora visível pros vendedores

## [v0.2-joana]
- Trocado o modelo do LLM por um GPT menor e mais barato

## [v0.1-joana]
- Primeira versão funcional: HubSpot → Search → OpenAI → Airtable
- Sem update do HubSpot ainda
