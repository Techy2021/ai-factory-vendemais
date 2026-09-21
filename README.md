# VendeMais ? Enriquecimento de leads

O VendeMais apoia o time comercial na qualifica??o de oportunidades B2B. O projeto consulta informa??es p?blicas sobre empresas, usa um LLM para gerar dados de enriquecimento, registra o resultado no Airtable e atualiza o score de ader?ncia ao perfil de cliente ideal (`icp_match_score`) no HubSpot.

## Fluxo final da Etapa 1

**HubSpot ? Brave Search ? Gemini ? JSON ? Airtable ? HubSpot**

O [blueprint versionado](workflows/vendemais-make-blueprint.json) cont?m seis m?dulos:

1. **HubSpot:** observa neg?cios atualizados no est?gio `appointmentscheduled`.
2. **Brave Search:** consulta informa??es sobre a empresa por HTTP.
3. **Gemini:** analisa os dados e gera a resposta de enriquecimento.
4. **JSON:** faz o parsing da resposta para disponibilizar os campos aos pr?ximos m?dulos.
5. **Airtable:** cria um registro com os dados enriquecidos.
6. **HubSpot:** atualiza o neg?cio com o `icp_match_score`.

## Arquitetura e documenta??o

A arquitetura escolhida ? a **Stack C**, baseada em servi?os SaaS e integra??es de baixo c?digo. O **Make ? o ambiente escolhido para produ??o**, com contas e credenciais corporativas. O n8n permanece como apoio para testes locais e aprendizado.

- [Auditoria do prot?tipo](docs/auditoria-prototipo.md)
- [Matriz de decis?o de stack](docs/matriz-decisao-stack.md)
- [ADR-001 ? Escolha da stack](docs/adr/ADR-001-escolha-da-stack.md)
- [ADR-002 ? Ambiente de produ??o](docs/adr/ADR-002-ambiente-de-producao.md)
- [C4 ? Contexto](docs/architecture/c4-contexto.md)
- [C4 ? Containers](docs/architecture/c4-containers.md)
- [Schema do Airtable](docs/airtable-schema.md)
- [Smoke tests da Etapa 1](docs/smoke-tests.md)

A auditoria, o contexto do ADR-001, os diagramas C4 e o mirror n8n ainda cont?m refer?ncias ao prot?tipo com Google Search/OpenAI. A decis?o de usar Make permanece v?lida, mas essas refer?ncias aos provedores precisam ser atualizadas para refletir Brave Search/Gemini. Para o fluxo implementado, consulte o blueprint versionado e a sequ?ncia descrita acima.

## Executar e testar

### Testes locais

Na raiz do reposit?rio, com Python 3.11 ou compat?vel, execute:

```bash
python tests/validate_workflows.py
python tests/test_enrichment_logic.py
```

Os scripts usam a biblioteca padr?o e n?o exigem credenciais nem chamadas externas. S?o 10 verifica??es estruturais dos artefatos Make/n8n e 5 verifica??es de l?gica com LLM simulado, incluindo montagem do prompt, parsing do score e rejei??o de JSON inv?lido. As 15 verifica??es passaram na revis?o desta entrega.

Os [smoke tests documentados](docs/smoke-tests.md) cobrem estrutura do blueprint, conex?es do mirror e leitura de um resultado simulado. Esses testes n?o comprovam a execu??o real do Gemini, a integra??o entre os servi?os ou o sucesso do deploy.

### Teste no Make

1. Use o ambiente corporativo do Make e importe [workflows/vendemais-make-blueprint.json](workflows/vendemais-make-blueprint.json) em um cen?rio de teste.
2. Configure ou remapeie as conex?es do HubSpot, Gemini e Airtable. Revise a base, a tabela e os campos de destino: refer?ncias exportadas n?o garantem acesso no novo ambiente.
3. Para importa??o manual, configure a chave Brave Search diretamente no m?dulo HTTP do Make, substituindo o placeholder `BRAVE_SEARCH_API_KEY` apenas no cen?rio. N?o grave a chave no arquivo versionado.
4. Com o agendamento desativado durante o teste, prepare um neg?cio de teste no est?gio esperado e execute **Run once**.
5. Confira a execu??o dos seis m?dulos, o JSON interpretado, o registro criado no Airtable e o score atualizado no HubSpot. Esse teste usa APIs reais e grava dados nos sistemas conectados.

A ativa??o e o agendamento devem ser conferidos no Make; o blueprint local n?o comprova o estado atual do cen?rio remoto.

### Apoio local com n8n

Com Docker e Docker Compose instalados:

```bash
cd n8n-mirror
docker compose up -d
```

Abra `http://localhost:5678` e importe `n8n-mirror/workflows/vendemais-enrich-local.json`, selecionando o arquivo a partir da raiz do reposit?rio. Essa vers?o usa servi?os simulados e permite exercitar o fluxo sem credenciais externas. Consulte o [guia do mirror](n8n-mirror/README.md) para disparar o webhook e inspecionar a execu??o.

O mirror conserva a estrutura do prot?tipo anterior; n?o valida a integra??o atual Brave Search/Gemini.

## CI com GitHub Actions

O workflow [ci.yml](.github/workflows/ci.yml) executa os dois scripts de teste em pushes e pull requests, usando Python 3.11. Falhas nos scripts fazem o job falhar. A CI verifica os artefatos e a l?gica local, sem acessar as APIs de produ??o.

## CD com GitHub Actions e Make API

O workflow [cd-make.yml](.github/workflows/cd-make.yml) atualiza um cen?rio existente no Make. Ele ? acionado por altera??es no blueprint enviadas ? branch `main` ou manualmente por **Actions ? CD Make ? Run workflow**.

Configure em **Settings ? Secrets and variables ? Actions**:

| Tipo | Nome | Uso |
| --- | --- | --- |
| Secret | `MAKE_API_KEY` | Autentica??o da API Make para leitura e atualiza??o do cen?rio. |
| Secret | `BRAVE_SEARCH_API_KEY` | Substitui??o do placeholder da busca durante o deploy. |
| Variable | `MAKE_SCENARIO_ID` | Identifica??o do cen?rio de destino, sem publicar seu valor na documenta??o. |
| Variable | `MAKE_REGION` | Regi?o do ambiente Make: `eu1`, `eu2`, `us1` ou `us2`. |

As demais credenciais de integra??o s?o configuradas nas conex?es do Make. N?o inclua chaves ou tokens no README, no blueprint ou nos logs.

O CD l? o blueprint local e substitui o placeholder Brave Search **somente em mem?ria**. Antes do envio, consulta `GET /scenarios/{id}/blueprint` e valida a estrutura remota, aceitando objeto ou string JSON. Em seguida, faz um ?nico `PATCH /scenarios/{id}`, com o campo `blueprint` serializado como string JSON dentro do corpo JSON da requisi??o.

O workflow n?o imprime o payload nem o corpo das respostas de erro. Em falhas, informa o status HTTP e, quando dispon?veis, o diagn?stico 1010 e o identificador `CF-Ray`. N?o h? retry autom?tico. Em caso de timeout ap?s o PATCH, confira o cen?rio no Make antes de repetir.

CI e CD s?o workflows independentes: o CD atual n?o aguarda automaticamente a conclus?o da CI. Confira os testes antes de disparar o deploy. O CD atualiza o blueprint; n?o executa o cen?rio nem configura seu agendamento.

## Status da Etapa 1

- Objetivo, decis?o de stack, ambiente de produ??o, ADRs, diagramas C4 e smoke tests est?o documentados, com a defasagem dos provedores indicada acima.
- O blueprint dos seis m?dulos est? versionado com o fluxo Brave Search/Gemini.
- Os 15 testes locais passaram e a CI foi executada com sucesso no GitHub Actions.
- O CD Make foi executado com sucesso pela branch `main`, com credenciais via GitHub Secrets, serialização do blueprint e validação de erros.
- O blueprint foi sincronizado pela Make API e o cenário foi verificado no Make após o deploy, com os seis módulos e os principais mapeamentos preservados.
- **Pendente de evid?ncia:** execu??o integrada do fluxo final e confirma??o do agendamento em produ??o. Os testes locais n?o substituem essa valida??o.

O reposit?rio re?ne os artefatos da Etapa 1 e registra as limita??es conhecidas. A opera??o em produ??o n?o deve ser considerada homologada apenas com base nos testes locais.

## D?vida t?cnica herdada

A [auditoria](docs/auditoria-prototipo.md) e as [notas do prot?tipo](docs/notas-joana.md) registram pontos de evolu??o, como tratamento de falhas, acompanhamento de custos, duplicidade de registros e governan?a de dados. Esses documentos s?o hist?ricos; a exist?ncia de testes e pipelines n?o comprova a resolu??o de todas essas pend?ncias.
