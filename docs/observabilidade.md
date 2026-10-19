# Desenho da observabilidade — Etapa 2.3A

Estado em 13/10/2026, atualizado pela Etapa 2.3D. A Etapa 2.3A define o desenho; as etapas 2.3B, 2.3C e 2.3D implementam instrumentação, alerta e dashboard locais descritos ao final. Não há coletor ou entrega remota. Fontes: [blueprint atual](../workflows/vendemais-make-blueprint.json), [schema Airtable](airtable-schema.md) e [sanitização](pii-sanitizacao.md). A inspeção é estática; não comprova disponibilidade de telemetria no Make remoto.

## Estado da entrega

| Estado | Evidência/escopo |
| --- | --- |
| **Definido/documentado** | Trace por tentativa, seis spans, exatamente cinco métricas, thresholds iniciais e alerta descritos abaixo. Limiares são escolhas operacionais do projeto, ainda sem baseline medido. |
| **Já implementado no repositório** | Módulos HubSpot (6), Brave (8), sanitização (29), Gemini (18), parsing JSON (21), Airtable (19) e atualização HubSpot (28). Airtable recebe timestamp, conteúdo enriquecido e score; HubSpot recebe score. Isso é dado de negócio, não prova de coleta de métricas. |
| **Já implementado localmente — 2.3B** | IDs aleatórios, seis spans no caminho completo, tempos/status/erro normalizado, contrato estrutural do Gemini, JSONL e agregação das cinco métricas em janelas. Execução reproduzível com callbacks sintéticos; não instrumenta o Make. |
| **Já implementado localmente — 2.3C** | Avaliador das cinco regras; ciclo P2 com persistência, disparo, lembrete e recuperação; entrega em arquivo JSONL local. Sem Slack ou integração remota. |
| **A implementar** | Conectores reais e propagação remota; coleta comprovada de uso/custo e conciliação; confirmação automática de demanda, agendamento operacional e entrega Slack. Dashboard externo fica para etapa posterior. |

O schema informa ausência de `cost_usd`; o blueprint não evidencia consumo de tokens coletado, tempos por etapa ou exportação de traces. O tratamento de erros do CD refere-se ao deploy, não às execuções de enriquecimento, e não atende este desenho.

## Trace principal

Nome proposto: **`vendemais.enrichment`**. Um trace por tentativa de enriquecimento de um negócio. Início: negócio elegível disponibilizado pelo módulo 6. Fim: confirmação de atualização do score pelo módulo 28, ou término com falha em qualquer etapa. Em caso de lote, criar um trace por negócio, sem confundir lote/poll com execução individual. Nova tentativa gera novo trace e referencia a anterior, se disponível.

Gerar `trace_id` aleatório, `span_id`, vínculo pai-filho, início/fim em UTC, duração e resultado `success/error`. Atributos permitidos: ambiente, versão do blueprint, provedor, modelo e código de erro normalizado. Não usar nome de empresa, título do negócio, e-mail, prompt, resposta bruta ou chave como atributo. Evitar IDs CRM como dimensões de métricas; a correlação deve usar o identificador técnico aleatório. O formato, propagação e armazenamento desses campos ainda serão implementados, sem presumir suporte automático do Make.

### Spans propostos

Todos filhos do trace principal. O parsing JSON do módulo 21 fica abrangido pelo span Gemini, com identificação de falha de parsing; não se propõe um sétimo span nesta etapa.

| Span | Módulo/trecho | Início → fim | Resultado a registrar |
| --- | --- | --- | --- |
| `hubspot.read` | 6 — leitura/seleção de negócio | Início da leitura instrumentada → negócio elegível disponibilizado | Sucesso ou erro do conector. Duração real da leitura exige acesso ao tempo do módulo/conector; não pode ser inferida do `enriched_at`. |
| `brave.search` | 8 | Antes da requisição → resposta recebida ou falha | Resultado HTTP normalizado, sem conteúdo ou URL da consulta. |
| `pii.sanitize` | 29 | Antes da serialização/substituições → texto sanitizado disponível | Sucesso ou falha de transformação; nenhum texto pessoal no evento. |
| `gemini.generate` | 18 e parsing 21 | Antes do envio do prompt sanitizado → JSON interpretado ou erro | Erro de API, resposta ausente ou JSON inválido; modelo e uso faturável somente quando comprovadamente disponíveis. |
| `airtable.write` | 19 | Antes da criação → confirmação ou falha | Sucesso/erro normalizado da gravação. |
| `hubspot.update` | 28 | Antes da atualização → confirmação ou falha | Sucesso/erro normalizado; encerra tentativa bem-sucedida. |

Se não for possível instrumentar o início da leitura, o trace começa na entrega do negócio e a latência exclui o tempo anterior, explicitamente. Tentativas sem negócio identificável por falha de polling precisam de evento operacional separado; não inventar traces por leads que não foram lidos.

## Cinco métricas definidas

Janelas móveis, calculadas em UTC e avaliadas a cada cinco minutos, salvo a avaliação diária indicada. Dados ausentes devem ser classificados como **sem avaliação**, nunca convertidos em zero ou sucesso. Dimensões limitadas a ambiente e versão; detalhamento por provedor apenas quando necessário. Os limites abaixo são iniciais e deverão ser recalibrados com amostras reais.

| Categoria / nome | Unidade e definição | Origem | Como coletar (a implementar) | Threshold inicial | Janela de avaliação | Ação ao violar |
| --- | --- | --- | --- | --- | --- | --- |
| **Latência — `enrichment_latency_p95_seconds`** | Segundos; percentil 95 da duração das tentativas terminadas, inclusive falhas | Início/fim do trace principal | Registrar duração monotônica por tentativa; calcular p95 pelo método nearest-rank. Não deduzir duração do timestamp Airtable | **p95 > 60 s**, com pelo menos 20 tentativas terminadas | Últimos 60 minutos | RevOps investiga spans lentos e dependências; planeja ajuste de timeout/payload após diagnóstico. |
| **Erro — `enrichment_error_rate_percent`** | %; 100 × tentativas terminadas com falha / tentativas terminadas | Estado final dos traces e falhas de spans | Capturar erro em qualquer etapa; JSON inválido ou ausência de confirmação final é falha quando o término for conhecido. Contar cada tentativa uma vez | **> 5%**, com pelo menos 20 tentativas terminadas, em duas avaliações consecutivas | Últimos 60 minutos | Disparar alerta P2 descrito abaixo e investigar a etapa responsável. |
| **Custo — `enrichment_mean_cost_usd`** | USD/tentativa; soma do custo variável atribuível / tentativas terminadas | Uso faturável Brave/Gemini/Make e preços efetivamente contratados | Obter uso comprovado em respostas ou exportação de faturamento conciliável; incluir chamadas cobradas que falharam. Registrar tabela de preços/data. Ratear planos fixos só com método documentado; sem cobertura completa, marcar custo parcial e não avaliar este threshold | **> US$ 0,03/tentativa**, com pelo menos 20 tentativas e custos completos conciliados | Últimas 24 horas; avaliação diária às 09:00 de São Paulo | RevOps e responsável financeiro revisam consumo e preço; propõem otimização. Não bloqueia execução automaticamente. |
| **Volume — `enrichment_success_count`** | Tentativas bem-sucedidas por janela; requer confirmação Airtable e HubSpot | Término bem-sucedido do trace | Incrementar contagem uma vez por `trace_id`; nova tentativa conta separadamente. Não equivale a negócios únicos, pois não há deduplicação comprovada | **< 1 sucesso**, apenas se houver demanda elegível pendente confirmada e operação prevista ativa | Últimos 60 minutos | RevOps confere agendamento, entrada, conexões e bloqueios. Sem evidência de demanda/agendamento, sem avaliação; zero pode ser legítimo. |
| **Qualidade — `enrichment_valid_output_rate_percent`** | %; respostas que atendem ao contrato / tentativas que chegaram ao Gemini. Resposta ausente/erro conta como inválida após término | Saída Gemini e parsing módulo 21 | Validador futuro exige objeto JSON com os seis campos solicitados; score inteiro 0–100 ou `null` por insuficiência; `tech_stack` lista ou `null`. Contar aprovação uma vez por tentativa. Não medir qualidade pelo valor alto do score | **< 95%**, com pelo menos 20 tentativas terminadas que chegaram ao Gemini | Últimas 24 horas | Revisar amostra sanitizada em ambiente controlado, contrato do prompt e parsing; propor correções. Não comprova veracidade factual das inferências. |

Os seis campos do contrato são `industry`, `size_employees`, `tech_stack`, `buying_signals`, `icp_match_score` e `talking_points`. A regra de `null` segue a instrução atual de não inventar informações. Avaliação humana de veracidade não está implementada nem é uma sexta métrica deste desenho.

## Alerta P2 funcional localmente — entrega JSONL; Slack não configurado

- **Nome:** falhas recorrentes no enriquecimento.
- **Condição:** `enrichment_error_rate_percent > 5%` nos últimos 60 minutos, com pelo menos 20 tentativas terminadas, em duas avaliações consecutivas de cinco minutos. Sem dados suficientes, não disparar nem declarar recuperação.
- **Prioridade:** **P2**, degradação que exige investigação durante a operação comercial. Não se presume indisponibilidade total.
- **Público:** responsável operacional RevOps; mantenedor de integrações como apoio técnico.
- **Canal efetivo:** `local_jsonl`, em `logs/thresholds/alerts.jsonl`. Slack `#vendemais-operacao` é apenas o canal pretendido; existência, acesso e integração ainda precisam de configuração. Não há entrega remota.
- **Mensagem:** ambiente, período, taxa e denominador, versão, código/etapa predominante e link técnico para investigação quando existir. Sem PII, secrets, prompts ou respostas.
- **Controle:** um alerta aberto por ambiente; repetir somente após 60 minutos ainda em violação. Encerrar após duas avaliações válidas consecutivas com taxa ≤ 5%. Responsável registra diagnóstico e ação.

Nenhuma mensagem Slack foi enviada, webhook criado ou canal verificado. Na Etapa 2.3C, avaliador, ciclo do alerta e entrega local JSONL foram implementados e testados com dados sintéticos. O alerta é funcional **localmente**; coletor remoto, credencial e entrega Slack continuam **a implementar**.

## Próxima implementação necessária

Integrar a instrumentação local aos conectores reais; confirmar meios de coleta de uso/faturamento dos fornecedores; verificar cobertura de dados e demanda; configurar e testar o alerta com falha sintética. Definir armazenamento, acesso e retenção da telemetria operacional antes de persistir eventos reais. A implementação local abaixo não executa esses passos remotos.

## Instrumentação local — Etapa 2.3B

Implementada em [scripts/local_observability.py](../scripts/local_observability.py), usando somente a biblioteca padrão Python 3.11+. Demonstração reproduzível sem credenciais, rede ou serviços externos:

```powershell
python scripts/local_observability.py
python tests/test_local_observability.py
```

A demonstração acrescenta uma tentativa sintética a `logs/observability.jsonl` (diretório já ignorado pelo Git) e imprime as cinco métricas dessa tentativa, não de todo o arquivo. Para agregar o histórico local, carregue cada linha com `json.loads` e passe a lista para `aggregate(records, now)` com `now` em UTC. Não existe envio automático a coletor. O arquivo pode ser removido após a demonstração; não há poda automática de telemetria implementada nesta etapa.

### Formato e integração

Cada linha JSONL representa um trace terminado, com `schema_version`, `name`, `trace_id`, `span_id` raiz, `environment=local`, `start`, `end`, `duration_seconds`, `status`, `error`, `spans`, `quality_valid`, `cost_usd` e `cost_source`. Cada span tem nome, vínculo ao trace e ao span raiz, início/fim UTC, duração em segundos e status/erro. IDs são gerados por UUID v4 (`uuid.uuid4`): trace com 32 caracteres hexadecimais e spans com 16. A duração usa relógio monotônico de alta resolução (`perf_counter`), independente do relógio UTC.

`run_enrichment` recebe exatamente seis callbacks, um por span, cada um recebendo a saída anterior. Conectores que precisem do contexto original devem mantê-lo em memória na closure, sem acrescentá-lo à telemetria. Gemini inclui parsing/validação estrutural; as gravações devem retornar `True` apenas após confirmação. Falha interrompe a tentativa, termina o trace como `error` e não cria spans fictícios para etapas não executadas. `invalid_output` identifica parsing/contrato inválido; demais exceções viram `operation_failed`, sem mensagem ou stack. Não são registrados prompts, respostas, dados CRM ou tokens.

O helper `synthetic_operations` simula todos os serviços e a sanitização. Ele não chama Gemini/Airtable/HubSpot, não substitui o sanitizador do blueprint e não comprova resultado de integrações. O trace local inclui o tempo do callback `hubspot.read`; em integração futura, documentar o limite de medição efetivamente acessível.

### Agregação e custo

`aggregate` retorna exatamente as cinco métricas especificadas acima, com valor, amostra, janela e estado. Usa fim da tentativa nas janelas `(agora - janela, agora]`, p95 nearest-rank e deduplicação por `trace_id`; duplicatas divergentes são rejeitadas. Não misturar arquivos de ambientes/versões diferentes. Nenhuma agregação de versão remota é implementada.

Qualidade conta tentativas que chegaram ao Gemini, incluindo falhas de chamada, ausência de resposta e JSON inválido; erro posterior à resposta válida não reduz a qualidade estrutural. Volume só conta sucesso após as duas confirmações de escrita. Sem tentativas na janela, o valor é `null` com `state=no_evaluation`, não zero.

Custo é informado explicitamente para a tentativa inteira, incluindo cobranças em falhas, com origem `synthetic` ou `reconciled`. Não é estimado a partir de latência, score ou quantidade de spans. Cobertura ausente/parcial ou mistura de origens torna a média `null`; zero só é aceito se explicitamente informado. A demonstração usa US$ 0,02 **sintético**, sem relação com tarifa real. Na integração, o chamador deve conciliar Brave/Gemini/Make e documentar preços/data antes de usar `reconciled`; a camada não verifica faturas ou prova essa conciliação.

Valores agregados podem existir com uma amostra, mas **não significam threshold avaliado**. Limiares, amostras mínimas e condições da Etapa 2.3A permanecem iguais; a Etapa 2.3C adiciona o avaliador e alerta local abaixo.

## Avaliação automática e alerta local — Etapa 2.3C

Implementação: [scripts/threshold_alerts.py](../scripts/threshold_alerts.py). Não altera Make, thresholds, instrumentação ou conectores. Com a telemetria local existente:

```powershell
# Uma avaliação; não comunica com serviços externos.
python scripts/threshold_alerts.py --synthetic
# Avaliação contínua a cada cinco minutos; interromper com Ctrl+C.
python scripts/threshold_alerts.py --watch --synthetic
# Testes sintéticos isolados, incluindo entrega local e recuperação.
python tests/test_threshold_alerts.py
```

`--synthetic` permite avaliar custos explicitamente sintéticos apenas na demonstração. Sem essa opção, custo exige origem `reconciled`; cobertura parcial/desconhecida nunca vira zero. A avaliação de custo roda no intervalo diário 09:00–09:04:59 de São Paulo (12:00–12:04:59 UTC); fora dele retorna `insufficient_data` com motivo específico. As demais regras usam as janelas e amostras mínimas documentadas. O processo precisa estar em execução nesse horário; não há scheduler externo criado.

Volume exige `--pending --active`, declarações explícitas de demanda pendente e operação ativa para a avaliação corrente. Se não há tentativas, zero só pode ser inferido com `--telemetry-complete`, confirmação de que a janela vazia foi integralmente coletada. Sem essas evidências, volume retorna `insufficient_data`. Esses indicadores não são descobertos automaticamente; no modo contínuo é responsabilidade do operador atualizar/reiniciar o processo quando deixarem de ser verdadeiros.

### Formato da avaliação e arquivos

Cada métrica retorna `state` (`ok`, `alert`, `insufficient_data`), `value`, `samples`, `threshold`, `operator`, `window_hours` e `reason`. O estado `alert` indica violação numérica; para erro, a primeira violação ainda **não entrega P2**, pois o ciclo exige persistência. Os limites são estritos: 60 segundos, 5%, US$ 0,03 e 95% exatamente não violam; volume de 1 também não viola.

Arquivos locais, todos sob diretório já ignorado `logs/thresholds/`:

- `evaluations.jsonl`: avaliação datada com as cinco métricas.
- `state.json`: estado P2, contadores de sequência, identificador e última notificação; substituição via arquivo temporário.
- `alerts.jsonl`: canal funcional de entrega local, criado quando houver `opened`, `reminder` ou `resolved`. Ler esse arquivo reproduz a mensagem entregue; não representa envio ao Slack.

Use `--telemetry` e `--directory` para escolher arquivos/diretório separados em demonstrações independentes. Não misture ambientes/versões; a rotina aceita somente `environment=local`. Entradas ilegíveis/inválidas interrompem a execução sem fabricar recuperação. A agregação deduplica traces como na Etapa 2.3B.

### Ciclo P2

Aceita no máximo uma avaliação por intervalo UTC de cinco minutos, com pelo menos 300 segundos desde a última aceita. Intervalos pulados interrompem sequências. Duas avaliações consecutivas com mais de 5% de erros e pelo menos 20 tentativas abrem um único alerta. Mesma avaliação repetida não avança contadores. Dados insuficientes zeram sequências e mantêm aberto um alerta existente; não equivalem a recuperação.

Enquanto aberto, só há lembrete após 60 minutos desde a última notificação e com violação válida. Duas avaliações consecutivas válidas com taxa ≤ 5% encerram o alerta; nova violação persistente abre novo identificador. A regra preserva prioridade **P2**, público **RevOps e mantenedor de integrações**, canal pretendido **Slack #vendemais-operacao** e canal efetivo **local_jsonl**. A mensagem inclui condição, amostra, valor, ambiente, horário e até cinco UUIDs técnicos de traces com erro na janela, quando disponíveis; não inclui payload nem mensagem de exceção. Na recuperação, os traces de erro podem estar ausentes.

Exemplo sintético testado: 20 tentativas, 2 falhas (10%), avaliações às 12:00 e 12:05 UTC. Às 12:00 não há mensagem; às 12:05 um evento `opened` P2 é gravado em `alerts.jsonl`. Com duas avaliações válidas posteriores de 5% ou menos, grava `resolved` com o mesmo `alert_id`.

### Limitações

Sem Slack real, webhook, deploy, agendamento de produção ou garantia de disponibilidade do processo local. Custo conciliado depende da declaração/evidência do chamador. Não existe lock entre processos; executar uma instância por diretório. Estado e entrega não formam transação única: falha entre append e persistência pode duplicar uma notificação na retomada; consumidores podem deduplicar por `alert_id`, tipo e horário. Não há poda automática dos arquivos locais. Apenas o P2 de erro gera mensagem; as outras quatro regras retornam estado para ação do operador. Os testes não comprovam comportamento de fornecedores remotos.

### Limites conhecidos

Não há conexão ao Make, propagação entre processos, exportador OpenTelemetry, recuperação de execução interrompida por encerramento do processo ou lock de escrita concorrente no JSONL. Um processo encerrado antes do término pode não produzir registro. O arquivo local não deve receber dados reais sem definir acesso/retenção. Instrumentação e callbacks são síncronos; não há retry automático. O validador mede contrato estrutural, não veracidade factual. Testes e demonstração usam exclusivamente dados sintéticos, sem testes amplos ou implantação.

## Dashboard local ? Etapa 2.3D

Disponível no [guia de execução do dashboard](dashboard-observabilidade.md), com geração de `logs/dashboard.html` a partir dos JSONL existentes, cinco métricas, estados e histórico P2. Snapshot manual, sem alteração das regras ou do ciclo P2.
