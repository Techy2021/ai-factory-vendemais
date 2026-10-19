# Etapa 2.4 — otimização medida do payload Gemini

## Payload identificado e escopo

No blueprint `workflows/vendemais-make-blueprint.json`, o módulo HTTP Brave **8**
produz `8.data`. O módulo **29** sanitiza `toJSON(8.data)` e expõe
`29.sanitized_search`. O módulo Gemini **18**, modelo `gemini-2.5-flash`, usa
`{{29.sanitized_search}}` como prefixo de `mapper.textPrompt`, seguido das
instruções de enriquecimento. Portanto, o contexto atual é o JSON **completo**
da resposta Brave já sanitizada, incluindo metadados que não são necessários à
análise. A posição atual do contexto, anterior às instruções, foi preservada.

Identificação feita por inspeção estática do blueprint local; não é captura de
uma execução Make/Gemini. O truncamento de `snippet` em
`tests/test_enrichment_logic.py` pertence ao teste legado do protótipo e não é
chamado pelo módulo Gemini atual.

Esta entrega implementa um **preparador local de payload candidato**, em Python
padrão. Não altera o blueprint, não conecta o preparador ao Make e não chama
Gemini. Não modifica sanitização, observabilidade, LGPD ou retenção. A ativação no
fluxo remoto fica para uma etapa posterior; a produção continua com o payload
anterior. O artefato local usa a forma `model`/`textPrompt` do mapper Make, não é
uma requisição HTTP completa da API Gemini.

## Otimização

`scripts/gemini_payload.py` recebe exclusivamente JSON **já sanitizado**. Não é
um sanitizador e não deve ser alimentado diretamente com a resposta bruta Brave.
Seleciona `web.results`, preservando quantidade e ordem dos resultados:

| Campo de cada resultado | Limite em caracteres Unicode |
| --- | ---: |
| `title` | 200 |
| `url` | 500 |
| `description` | 800 |
| `extra_snippets` | primeiros 2, até 300 cada |

O corte é feito nos valores antes da serialização: o JSON permanece válido,
inclusive com aspas, escapes e caracteres multibyte. Não há resumo por LLM,
reordenação, deduplicação ou mudança do score, campos de saída, modelo ou
instruções. URLs longas podem ser cortadas; seu papel aqui é apenas contexto,
não um link garantidamente navegável.

Metadados como thumbnails, perfis, query e outros grupos da resposta não entram
na seleção. Se a seleção serializada não for menor em bytes UTF-8 que o objeto
original compacto, preserva-se o original compacto. Assim entradas mínimas não
crescem por causa do novo wrapper. `null`, resultados ausentes/nulos e entradas
vazias não ganham evidência inventada. Formatos inesperados de campos usados
provocam erro explícito. Não há limite global nem corte da quantidade de
resultados: muitas ocorrências ainda podem produzir um prompt grande.

## Execução reproduzível

Na raiz do repositório, com Python 3.11 ou compatível, sem instalar pacotes:

```powershell
python scripts/measure_gemini_payload.py
python tests/test_gemini_payload.py
```

Para regenerar o relatório versionado:

```powershell
python scripts/measure_gemini_payload.py --output docs/gemini-payload-medicao.json
```

Para preparar um candidato a partir de um arquivo já sanitizado:

```powershell
python scripts/gemini_payload.py --input logs/busca-sanitizada.json --output logs/gemini-payload-candidato.json
```

A saída contém `model` e `textPrompt` com o conteúdo otimizado. O preparador lê
as instruções diretamente do blueprint atual e resolve apenas o placeholder
`{{29.sanitized_search}}`. Se o mapeamento esperado mudar, falha em vez de gerar
silenciosamente outro prompt. Nenhum comando envia uma requisição ou faz deploy.

## Medição sintética A/B

Fonte reproduzível: `fixtures()` em `scripts/measure_gemini_payload.py`. Cada par
usa exatamente o mesmo JSON sanitizado sintético, instruções e modelo; muda
apenas a seleção/truncamento do contexto. Os cenários contêm metadados extensos,
descrições longas, entrada mínima e entrada vazia. São exemplos controlados,
não uma amostra representativa de buscas reais. Nos dois cenários maiores há
cinco resultados; os fatos usados pelo mock estão no início das descrições.

Números do [relatório gerado](gemini-payload-medicao.json), incluindo todas as
instruções no tamanho do prompt:

| Cenário | Caracteres antes | Depois | Redução | Tokens estimados antes → depois |
| --- | ---: | ---: | ---: | ---: |
| Metadados extensos | 8.199 | 2.361 | 71,20% | 2.050 → 591 |
| Descrições longas | 19.286 | 5.931 | 69,25% | 4.822 → 1.483 |
| Mínimo | 824 | 824 | 0% | 206 → 206 |
| Vazio | 692 | 692 | 0% | 173 → 173 |
| **Soma dos cenários** | **29.001** | **9.808** | **66,18%** | **7.251 → 2.453** |

Redução = `100 × (antes − depois) / antes`. A redução agregada usa a soma dos
caracteres, não a média das porcentagens. O relatório também mede bytes UTF-8
do prompt e do mapper JSON compacto. O mapper exclui metadados/conexão Make e
overhead HTTP; seus bytes não equivalem a tokens cobrados pelo provedor.

Tokens são **estimativa heurística** `ceil(caracteres / 4)`, por prompt, sem
tokenizador Gemini. Caracteres e bytes são **medidos localmente**; tokens não.
O relatório depende do prompt versionado: mudanças futuras nas instruções
alterarão os totais e exigirão regeneração.

Não foi atribuído valor monetário: não há tarifa verificada nem contagem
faturada. Com uma tarifa de entrada comprovada `R` USD por milhão de tokens,
a projeção seria `tokens_estimados × R / 1.000.000`. Para esses cenários, a
parcela estimada de entrada seria `0,007251 × R` antes e `0,002453 × R` depois.
Isso não estima a fatura total: exclui saída, reasoning, cache, Make, Brave e
eventuais diferenças de modalidade. Nenhum custo real foi medido.

Latência não foi reportada: medir serialização de poucos objetos locais não
representa a latência de rede/inferência do Gemini e não responde à hipótese de
ganho percebido pelo usuário.

## Qualidade, trade-off e testes

O mock é sensível à presença dos fatos sintéticos no prompt e produz os seis
campos do contrato. As quatro respostas antes/depois são iguais e
estruturalmente válidas: campos presentes, listas, tipos básicos e score inteiro
0–100 ou `null`. A entrada vazia produz desconhecidos/listas vazias, não fatos.
Trata-se de teste de contrato e preservação dos fatos escolhidos no experimento,
**não de respostas reais do Gemini** nem de demonstração de não regressão factual.

Reduzir metadados e texto diminui o volume de entrada, mas pode remover contexto
útil: fatos depois de 800 caracteres, snippets após o segundo e evidências fora
de `web.results`. Um teste coloca os fatos após o limite e verifica que o mock
muda a resposta mesmo mantendo o contrato estrutural válido. Essa perda é um
limite conhecido do truncamento, não uma falha escondida pela métrica de formato.
O ganho financeiro dependeria dos tokens faturados e a qualidade real requer
avaliação controlada com Gemini e evidências representativas antes de ativação.

Executados apenas os **7 testes direcionados** em `tests/test_gemini_payload.py`:
seleção e ordem sem mutação; limites/Unicode/JSON válido; entradas vazias;
rejeição de schema inesperado; preservação exata do modelo e instruções;
reprodutibilidade/contrato simulado; exposição da perda de fatos tardios.
Sem testes amplos, chamadas reais, novos serviços ou deploy no Make.
