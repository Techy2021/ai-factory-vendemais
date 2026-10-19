# Dashboard local — Etapa 2.3D

Na raiz do repositório, com Python 3.11 ou compatível, sem instalar pacotes:

```powershell
python scripts/observability_dashboard.py
Start-Process logs/dashboard.html
```

Em outros sistemas, abra `logs/dashboard.html` pelo navegador. O HTML é autocontido,
sem servidor, JavaScript, CDN ou chamadas externas. O artefato fica em `logs/`, já
ignorado pelo Git. Execute novamente e recarregue a página para atualizar.

## Fontes e métricas

O gerador lê `logs/observability.jsonl` e `logs/thresholds/alerts.jsonl`, sem alterá-los.
Reutiliza `aggregate` de `scripts/local_observability.py` e `evaluate` de
`scripts/threshold_alerts.py`. Não avança o ciclo P2, não grava avaliações e não muda
thresholds. `evaluations.jsonl` não é necessário: os estados são recalculados no
horário de referência mostrado no topo, sem reaproveitar uma avaliação antiga.

| Métrica | Unidade | Janela |
| --- | --- | --- |
| Latência p95 | segundos | 1h |
| Taxa de erro | % de tentativas | 1h |
| Custo médio | USD por tentativa | 24h |
| Volume de sucessos | contagem | 1h |
| Qualidade estrutural | % válido entre tentativas que chegaram ao Gemini | 24h |

Cada cartão apresenta `ok`, `alert` ou `insufficient_data`, valor, amostra, janela,
limiar e motivo técnico retornado pelo avaliador. Ausência de valor aparece como
`—`, nunca como zero automático. As regras e amostras mínimas continuam sendo as
da [observabilidade existente](observabilidade.md).

O custo só é avaliado entre 12:00 e 12:04:59 UTC (09:00 em São Paulo). Fora desse
horário, seu valor descritivo pode aparecer junto com `insufficient_data`.
Volume requer confirmação explícita de demanda e operação; informe apenas quando
verdadeiro para a referência escolhida:

```powershell
python scripts/observability_dashboard.py --pending --active
```

`--telemetry-complete` confirma que uma janela vazia foi integralmente coletada;
com demanda e operação confirmadas permite inferir zero sucessos. Não use essa
opção para encobrir coleta ausente.

## Reprodução histórica e dados sintéticos

Para reproduzir uma leitura com referência fixa, incluindo o intervalo de custo:

```powershell
python scripts/observability_dashboard.py --at 2026-10-14T12:00:00+00:00 --synthetic --output logs/dashboard-historico.html
```

A referência precisa incluir fuso horário. Não modifica datas nos logs. Dados
anteriores às janelas ficam fora das métricas; eventos posteriores à referência
ficam fora do histórico. `--synthetic` apenas permite avaliar custo explicitamente
marcado como sintético; não gera dados nem declara demanda ou operação.

O painel destaca **DADOS SINTÉTICOS** se encontrar `cost_source=synthetic` nas fontes
de telemetria, mesmo quando os registros já estão fora da janela. O schema atual
marca a origem do custo, mas não comprova a origem de todos os demais campos.
Sem esse marcador, o painel informa origem não comprovada. Eventos P2 não possuem
marcador de origem: não se deve tratá-los como evidência de produção.

## Alertas e limitações

São mostrados os últimos 20 eventos P2 até a referência, ordenados por horário
decrescente: `opened`, `reminder` e `resolved`, com ID, horário, taxa de erro,
amostra, condição e canal efetivo de entrega. Histórico não confirma o estado
atual do incidente. Apenas a regra de taxa de erro gera eventos P2 no avaliador
existente; os demais cartões exibem estados.

Arquivos ausentes geram aviso e estado vazio, sem fabricar recuperação. JSONL
inválido interrompe a geração com código 1; se já existir HTML, ele continua sendo
o snapshot anterior, com seu horário original. Evite gerar enquanto os JSONL
estiverem sendo escritos: não há lock ou tolerância a uma linha parcial.

É um snapshot manual que carrega os arquivos em memória, sem séries históricas,
atualização automática, coletor remoto ou garantia de disponibilidade. Qualidade
é estrutural, não factual. Não há deploy externo ou configuração/envio de Slack.

Validação pontual, sem suíte ampla:

```powershell
python tests/test_observability_dashboard.py
```
