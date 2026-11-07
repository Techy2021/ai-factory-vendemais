# VendeMais — README v1.0

Enriquecimento de oportunidades B2B com Brave Search e Gemini, registro no Airtable e atualização do `icp_match_score` no HubSpot. Make é a plataforma escolhida para produção; n8n apoia testes locais e aprendizado.

**Estado:** o dashboard React, a API FastAPI, o acesso ao Airtable e login/logout foram validados localmente. Filtros e paginação estão implementados; as mudanças posteriores à validação local de dados devem ser conferidas na próxima homologação. Não há publicação ou homologação do dashboard em produção comprovada. A Etapa 1 registra sincronização do blueprint pela Make API, sem comprovar o estado remoto atual ou a homologação integrada. Sanitização está no blueprint local, sem deploy comprovado; observabilidade e otimização são locais. Ativação da retenção e execução integrada/agendamento em produção permanecem pendentes.

## Fluxo e arquitetura

**HubSpot → Brave Search → sanitização → Gemini → parsing JSON → Airtable → HubSpot**

O [blueprint atual](workflows/vendemais-make-blueprint.json) contém sete módulos, incluindo o sanitizador da Etapa 2.2D. O Gemini solicita `industry`, `size_employees`, `tech_stack`, `buying_signals`, `icp_match_score` e `talking_points`; score inteiro de 0 a 100 ou `null` por insuficiência de informação.

O dashboard é um fluxo separado e somente de leitura: **React/Vite → FastAPI → Airtable**. A automação Make é responsável pelo fluxo de enriquecimento e gravação no Airtable/HubSpot; o dashboard não executa nem altera a automação. A API consulta apenas campos autorizados do Airtable e protege leads e métricas com sessão administrativa.

- [Decisão de stack](docs/matriz-decisao-stack.md), [ADR-001](docs/adr/ADR-001-escolha-da-stack.md) e [ADR-002](docs/adr/ADR-002-ambiente-de-producao.md).
- C4: [contexto](docs/architecture/c4-contexto.md) e [containers](docs/architecture/c4-containers.md).
- [Schema Airtable](docs/airtable-schema.md), [auditoria](docs/auditoria-prototipo.md), [notas históricas](docs/notas-joana.md) e [smoke tests](docs/smoke-tests.md).

Parte desses documentos e o [mirror n8n](n8n-mirror/README.md) ainda descrevem Google Search/OpenAI do protótipo; não validam a integração Brave/Gemini. O blueprint e os guias específicos das etapas registram a implementação atual.

## Dashboard: execução e configuração

Requisitos: Python 3.11, Node.js com npm compatível com as dependências em
[`frontend/package.json`](frontend/package.json), acesso à base/tabela Airtable
e uma senha administrativa fornecida com segurança. O backend usa FastAPI,
Pydantic e Uvicorn, conforme [`backend/requirements.txt`](backend/requirements.txt).

Variáveis do **processo do backend** (o FastAPI não carrega `.env` automaticamente):

| Variável | Finalidade |
| --- | --- |
| `VENDEMAIS_ENV` | `production` por padrão; `development` para documentação e HTTP local. |
| `AIRTABLE_API_TOKEN` | Token de leitura autorizado à base/tabela. |
| `AIRTABLE_BASE_ID` | Identificador da base. |
| `AIRTABLE_TABLE_ID` | Identificador da tabela. |
| `VENDEMAIS_ADMIN_PASSWORD` | Senha administrativa forte, fornecida por ambiente ou cofre. |
| `VENDEMAIS_ALLOWED_ORIGIN` | Origem exata permitida para o dashboard; localmente, `http://localhost:5173`. |
| `VENDEMAIS_COOKIE_SECURE` | `true` por padrão e obrigatório em produção; `false` somente em desenvolvimento com HTTP de loopback local. |

O exemplo [`backend/.env.example`](backend/.env.example) lista as variáveis;
não coloque credenciais no repositório, em comandos registrados no histórico
ou em logs. Defina-as no ambiente do processo com um mecanismo apropriado.

No **frontend**, `VITE_API_BASE_URL` é uma origem pública, não um segredo.
Em desenvolvimento, ausente ou vazia, usa `http://localhost:8001`; HTTP
explícito só é aceito para loopback. Em produção, ausente ou vazia, usa a
origem HTTPS atual do navegador; se definida, deve ser uma origem HTTPS
absoluta, sem credenciais, caminho, consulta ou fragmento. O Vite incorpora o
valor configurado na aplicação: defina-o antes de gerá-la e reinicie o servidor
de desenvolvimento após alterações. Veja
[`frontend/.env.example`](frontend/.env.example) e
[`frontend/README.md`](frontend/README.md).

Após configurar as variáveis do backend, inicie-o em um terminal PowerShell:

```powershell
Set-Location 'D:\VendeMais\backend'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1 --no-access-log
```

Em outro terminal:

```powershell
Set-Location 'D:\VendeMais\frontend'
npm ci
npm run dev -- --host localhost --port 5173 --strictPort
```

Abra `http://localhost:5173`. Para cookies locais, use `localhost`
consistentemente, inclusive na URL da API; o processo backend deve receber
`VENDEMAIS_ENV=development`,
`VENDEMAIS_ALLOWED_ORIGIN=http://localhost:5173` e
`VENDEMAIS_COOKIE_SECURE=false` **somente em desenvolvimento local**.

### Endpoints e dados

| Endpoint | Comportamento |
| --- | --- |
| `GET /health` | Público; retorna o estado da aplicação. |
| `POST /auth/login` | Recebe a senha administrativa e retorna 204 com cookie de sessão. |
| `POST /auth/logout` | Revoga a sessão apresentada e remove o cookie; retorna 204. |
| `GET /api/leads` | Protegido; retorna `items`, `total`, `page` e `page_size`. |
| `GET /api/metrics` | Protegido; retorna `leads_total`, `average_score`, `missing_score_count` e `unique_deals`. |

Os endpoints de dados aceitam `start_date` e `end_date` opcionais em
`YYYY-MM-DD`, com limites inclusivos em UTC sobre `enriched_at`. Sem filtro de
período, registros sem data também são incluídos; com filtro, são excluídos.
Em leads, `page` começa em 1 e `page_size` vai de 1 a 100. `deal_id` e os
demais campos de apresentação podem ser `null`; nenhuma identificação é
inventada. `tech_stack` é lista de textos ou `null`; texto de origem é mantido
como um único item.

O dashboard aceita pontuações numéricas finitas de 0 a 100, inclusive
decimais. Valor ausente, booleano, texto, não finito ou fora da faixa é
tratado como `null` e contado como ausente nas métricas. A média usa apenas
pontuações válidas. A regra de saída solicitada ao Gemini no fluxo Make é
separada desse contrato de leitura.

### Sessões e requisitos para produção

O cookie é HttpOnly e SameSite=Strict; em produção deve ser Secure. Login e
logout exigem exatamente a origem configurada, e o CORS permite credenciais
apenas para essa origem. Sem sessão válida, leads e métricas retornam 401; uma
fonte de dados ausente ou indisponível retorna 503. Não registre senhas,
cookies, corpos de login nem dados pessoais em logs da aplicação ou proxy.
Em produção, `/docs`, `/redoc` e `/openapi.json` estão desativados; use
`VENDEMAIS_ENV=development` apenas no ambiente local.

As sessões expiram após oito horas e, junto com o limitador, existem apenas na
memória do processo. O limite é de cinco tentativas globais por cinco minutos,
inclusive sucessos; reinício invalida as sessões e zera a contagem. Uma
demonstração acadêmica controlada pode usar **um worker e uma réplica**, com
ressalvas: não há contas individuais nem MFA, e o limite global pode impedir
usuários legítimos. Para produção, exija HTTPS, cookie Secure, origem e CORS
restritos, origem HTTPS da API (mesma origem ou `VITE_API_BASE_URL` pública
configurada), proteção adicional de taxa no proxy e gestão segura de
credenciais. A compatibilidade de `SameSite` deve ser validada na topologia de
domínios; CORS não a substitui. Mais de um
worker/réplica exige estratégia compartilhada de sessões e limitação de taxa.

**Pendente de homologação em produção:** implantação HTTPS, configuração de
origens e cookies, proteção de taxa, gestão de segredos e validação integrada
do dashboard no ambiente de destino. A aprovação com ressalvas da estratégia
de sessão aplica-se somente à demonstração acadêmica controlada.

## Segurança e credenciais

O [.env.example](.env.example) lista nomes sem valores. `.env` local é opcional, deve conter apenas credenciais de desenvolvimento e está coberto pelo [.gitignore](.gitignore), que não protege arquivos já rastreados. `.env` não é carregado automaticamente pelo CD, Compose ou script de retenção. Nunca versione chaves, exportações com secrets ou logs com credenciais.

| Armazenamento | Configuração atual |
| --- | --- |
| GitHub Actions Secrets do CD | `MAKE_API_KEY`, `BRAVE_SEARCH_API_KEY` |
| GitHub Actions Variables do CD | `MAKE_SCENARIO_ID`, `MAKE_REGION` (`eu1`, `eu2`, `us1` ou `us2`) |
| Conexões corporativas Make | Gemini, HubSpot OAuth e Airtable PAT; não há `GEMINI_API_KEY` local consumida pelo projeto |
| Retenção, separada do CD | Secret/ambiente do processo `AIRTABLE_RETENTION_PAT`; Variables do workflow `AIRTABLE_RETENTION_BASE_ID` e `AIRTABLE_RETENTION_TABLE_ID` |

Mantenha inventário/responsáveis no cofre corporativo, acesso mínimo e credenciais distintas por ambiente. O CD usa configuração do repositório, sem isolamento automatizado por GitHub Environment; homologação exige cenário/conexões separados.

**Rotação:** a cada 90 dias ou antes por exigência do provedor, mudança de acesso ou suspeita de exposição. Gere a substituta, atualize cofre/Secrets/conexões, valide e revogue a anterior; em comprometimento confirmado, revogue imediatamente. Atualizar o Secret Brave não troca a chave já publicada: isso requer CD autorizado. Apagar um valor não elimina o histórico Git. Procedimento: [segurança de credenciais](docs/seguranca-credenciais.md).

## LGPD

O [mapa de dados](docs/lgpd-mapa-dados.md) inventaria origem, finalidade, destinatários, categorias e papéis por inspeção estática. Dados exclusivamente empresariais não exigem base legal de dados pessoais; texto livre e associação a pessoas podem mudar esse enquadramento.

**Bases legais:** legítimo interesse é hipótese candidata para dados pessoais comuns na qualificação B2B, condicionada à finalidade, necessidade, expectativas e teste de balanceamento ainda pendente. Consentimento não foi adotado; contrato e obrigação legal não foram presumidos. Não há fundamento documentado para dados sensíveis nem aprovação jurídica comprovada do tratamento.

**Transferência internacional:** potencial/não confirmada em HubSpot, Make, Brave, Gemini e Airtable. Países, suboperadores, contratos/DPA e mecanismo aplicável não estão comprovados; `country=BR` não garante residência. A base legal do tratamento não resolve, por si só, o mecanismo de transferência.

**Retenção e exclusão:** política interna de até 30 dias para busca bruta e históricos/prompts; até 180 dias para enriquecimento e vínculo no Airtable; CRM ativo com revisão a cada 180 dias e até 180 dias após encerramento; backups até 90 dias após exclusão ativa. Não são prazos legais presumidos. O [procedimento de retenção](docs/retencao-exclusao.md) implementa limpeza bruta Airtable em 30 dias e exclusão quando criação e enriquecimento têm ao menos 180 dias, além de configuração de poda do mirror n8n. Workflow existe, mas ativação/exclusão remota e poda real não foram comprovadas. HubSpot, históricos Make/Brave/Gemini e backups não são limpos por essa rotina.

**PII antes do Gemini:** o módulo 29 serializa toda a resposta Brave e mascara e-mail, padrões de telefone/CPF e nomes com rótulos, sem fallback bruto no prompt. As [regras de sanitização](docs/pii-sanitizacao.md) foram testadas localmente com dados sintéticos; o interpretador Make requer validação em homologação. Não garantem anonimização nem filtram prompt injection. Consulta Brave, cópia bruta Airtable e históricos Make continuam fora dessa proteção.

## Observabilidade local

O [guia de observabilidade](docs/observabilidade.md) descreve o trace **`vendemais.enrichment`**, por tentativa, com IDs técnicos aleatórios e seis spans: `hubspot.read`, `brave.search`, `pii.sanitize`, `gemini.generate` (inclui parsing), `airtable.write` e `hubspot.update`. A implementação local usa callbacks; não instrumenta automaticamente o Make remoto.

| Métrica | Janela | Threshold existente |
| --- | --- | --- |
| Latência p95 | 1h | > 60 s, mínimo 20 tentativas |
| Taxa de erro | 1h | > 5%, mínimo 20 tentativas |
| Custo médio | 24h | > US$ 0,03/tentativa, mínimo 20 e custos completos conciliados |
| Volume de sucessos | 1h | < 1, com demanda pendente e operação ativa confirmadas |
| Qualidade estrutural | 24h | < 95%, mínimo 20 tentativas que chegaram ao Gemini |

Estados: `ok`, `alert` e `insufficient_data`. Qualidade mede contrato estrutural, não veracidade. Custo é avaliado entre 09:00 e 09:04:59 de São Paulo (12:00 UTC); custos sintéticos só são aceitos com `--synthetic`. Volume requer `--pending --active`; janela vazia só vira zero com confirmação adicional `--telemetry-complete`.

**P2:** apenas a taxa de erro gera eventos, após duas avaliações consecutivas válidas de cinco minutos. Há lembrete após 60 minutos ainda em violação e recuperação após duas avaliações válidas com taxa ≤ 5%. A entrega funcional é `logs/thresholds/alerts.jsonl` (`opened`, `reminder`, `resolved`); Slack é canal pretendido, sem configuração ou envio.

Na raiz, com Python 3.11 ou compatível, sem instalar pacotes:

```powershell
# Demonstração sintética: acrescenta uma tentativa ao JSONL local.
python scripts/local_observability.py
# Avaliação local: persiste avaliação e estado P2, sem Slack.
python scripts/threshold_alerts.py --synthetic
# Snapshot: não altera as fontes nem avança o ciclo P2.
python scripts/observability_dashboard.py
Start-Process logs/dashboard.html
```

O [dashboard](docs/dashboard-observabilidade.md) lê `logs/observability.jsonl` e `logs/thresholds/alerts.jsonl`, mostra cinco métricas e os últimos 20 eventos P2 até a referência. `logs/dashboard.html` é artefato local ignorado pelo Git; execute novamente e recarregue para atualizar. Em outros sistemas, abra o arquivo no navegador. O painel sinaliza custos marcados como sintéticos; o schema não comprova a origem completa dos traces ou eventos P2.

## Otimização medida do payload Gemini

O [preparador local](scripts/gemini_payload.py) recebe JSON já sanitizado, seleciona título, URL, descrição e snippets de `web.results`, com limites por campo. Mantém ordem, modelo e instruções. **Não está conectado ao Make**, cujo blueprint não foi alterado pela Etapa 2.4.

| Soma dos quatro cenários sintéticos | Antes | Depois |
| --- | ---: | ---: |
| Caracteres do prompt completo | 29.001 | 9.808 |
| Tokens estimados (`ceil(caracteres / 4)`, por prompt) | 7.251 | 2.453 |

**Redução medida em caracteres: 66,18%.** Dados exclusivamente sintéticos; tokens são heurística, não contagem Gemini. **Custo e latência reais não foram medidos.** O contrato estrutural permaneceu válido nas respostas simuladas, mas truncamento pode eliminar fatos tardios; não há comprovação de não regressão semântica no Gemini. Método e trade-off: [otimização](docs/otimizacao-payload-gemini.md) e [relatório A/B](docs/gemini-payload-medicao.json).

```powershell
python scripts/measure_gemini_payload.py
```

## Troubleshooting

| Sintoma | Verificação e ação |
| --- | --- |
| Dashboard sem dados | Confira caminhos JSONL, referência e janelas de 1h/24h. Logs antigos ficam fora das métricas. Execute o gerador novamente; a demo acima cria apenas dados sintéticos. Para histórico, use `--at` com ISO 8601 e fuso, conforme o guia. JSONL inválido interrompe a geração; um HTML anterior continua sendo snapshot antigo. |
| `insufficient_data` | Leia o motivo no cartão. Verifique amostra mínima, conciliação/horário do custo, demanda/operação e cobertura da coleta. Uma tentativa da demo não atende ao mínimo 20. Não declare `--telemetry-complete` sem evidência nem transforme ausência em zero. |
| P2 não dispara | O dashboard não dispara alertas. Execute o avaliador, por exemplo `python scripts/threshold_alerts.py --watch --synthetic` para demonstração, e confira `evaluations.jsonl`/`state.json`. Exige taxa > 5%, amostra ≥ 20 e duas avaliações válidas consecutivas em intervalos de cinco minutos; lacunas ou dados insuficientes interrompem a sequência. Uma execução isolada não basta. O canal é JSONL, não Slack. |
| Retenção falha | Confira `AIRTABLE_RETENTION_PAT` no ambiente do processo, escopos `data.records:read/write`, acesso à base/tabela e IDs de campos. Datas ausentes/inválidas/futuras impedem ações. Use primeiro o modo padrão sem `--apply`, que ainda consulta a API. Em falha, pode haver alterações parciais: confira o estado remoto antes de repetir; não há rollback automático. Veja o procedimento de retenção. |
| Sanitização falha ou deixa PII | Execute o teste abaixo e confira módulo 29 e referência a `29.sanitized_search` no prompt. O teste também compara com `HEAD`; mudança de versão-base pode exigir revisão dessa expectativa, não remoção automática do controle. Valide a expressão em homologação; formatos fora das regex podem permanecer. Não contorne a falha enviando `8.data` bruto ao Gemini. |
| Variáveis/secrets não funcionam | Confirme nomes e armazenamento da tabela de credenciais; preencher `.env` não injeta variáveis nos processos atuais. Gemini usa conexão Make. Atualizar o Secret Brave não muda o cenário publicado. Verifique ambiente, permissões e conexão sem imprimir valores ou exportar secrets. |

### Testes direcionados

Execute apenas o comando correspondente à área investigada, na raiz. Python usa biblioteca padrão; sanitização requer Node.js 18+ e Git. Dados/clientes são simulados, sem comprovar comportamento remoto.

```powershell
python tests/test_local_observability.py
python tests/test_threshold_alerts.py
python tests/test_observability_dashboard.py
python tests/test_retention_cleanup.py
node tests/test_pii_sanitization.cjs
python tests/test_gemini_payload.py
```

## CI, CD e validação remota pendente

A [CI](.github/workflows/ci.yml) executa `tests/validate_workflows.py` e `tests/test_enrichment_logic.py` com Python 3.11 em push/PR; não inclui automaticamente os testes direcionados acima. A [CD Make](.github/workflows/cd-make.yml) atualiza cenário existente por mudanças no blueprint na `main` ou disparo manual. Injeta Brave em memória, consulta/valida o blueprint remoto e envia um `PATCH` com blueprint serializado. Não executa cenário nem configura agendamento; CI e CD são independentes.

Em falhas de CD, confira status HTTP, diagnóstico 1010 e `CF-Ray` quando disponíveis; não há retry automático. Em timeout após `PATCH`, confira o cenário antes de repetir. Retenção usa [workflow separado](.github/workflows/retention.yml), sem ativação comprovada.

Para homologar, use cenário corporativo separado e agendamento desativado; importe o blueprint, remapeie conexões e valide base/tabela/campos. Na importação manual, substitua `BRAVE_SEARCH_API_KEY` somente no módulo HTTP remoto. Uma execução **Run once** deve comprovar os sete módulos, parsing, gravação Airtable e atualização HubSpot. Usa APIs reais, grava dados e pode gerar custo; não foi realizada nesta revisão documental.

Permanecem declarados: execução integrada/agendamento em produção; validação e deploy remoto da sanitização; teste de balanceamento e contratos/transferências; cobertura/ativação da retenção; conectores, telemetria e custo conciliado reais; entrega Slack; ativação e avaliação real da otimização. Nenhuma função local ou teste sintético, isoladamente, homologa produção.
