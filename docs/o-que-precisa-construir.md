# O que você precisa construir — checklist do desafio

Você herdou um cenário Make.com funcional mas frágil, criado pela estagiária Joana, sem documentação e com credenciais pessoais. Em 12 semanas, transforme isso num sistema corporativo, auditável e versionado.

## 1. Migrar cenário Make do espaço pessoal da Joana para a conta corporativa VendeMais
Não é trivial: o Make.com **não tem "transfer workspace"**. A estratégia provavelmente envolve exportar o blueprint JSON do cenário da Joana, importar na conta corporativa e recriar conexões.

## 2. Reconfigurar todas as conexões
- HubSpot OAuth (admin do HubSpot precisa autorizar de novo)
- Airtable PAT (token novo na conta corporativa)
- OpenAI API key corporativa (não mais a pessoal da Joana — urgente, ela vai revogar daqui a alguns meses)
- Google Custom Search API (com billing no Google Cloud corporativo)

## 3. Versionar o blueprint exportado em Git
Limitação real do Make: **conexões não exportam** no JSON. Você vai versionar a estrutura do cenário, mas conexões continuam configuradas via UI.

## 4. Configurar GitHub Actions para sync do blueprint via API Make
Pipeline que, a cada push em `main`, sobe a versão atual do blueprint pro Make via API. Inverso também: cron que baixa o blueprint diariamente e abre PR se houver diff (detecta edição manual fora do Git).

## 5. Adicionar tratamento de erro (Joana não configurou nenhum!)
- Try/catch em cada módulo crítico
- Branch de falha: marca `enrichment_status = "failed"` no HubSpot
- Notificação no Slack do time RevOps quando uma execução quebra

## 6. Otimizar prompt (o modelo GPT pequeno com 8k tokens tá caro)
- Truncar snippets do Google a ~500 chars cada antes de mandar pro LLM
- Avaliar se cabe few-shot mais enxuto
- Medir custo médio por execução antes e depois

## 7. Instrumentar custo por execução
Adicionar campo `cost_usd` no Airtable. Calcular a partir dos tokens retornados pela API OpenAI. Construir uma view de custo acumulado por mês.

## 8. Mapear LGPD
Dados de empresas-cliente passando por Google Search + OpenAI nos EUA = **transferência internacional de dados**. Mapear: bases legais, contratos com sub-operadores, DPA com OpenAI e Google, anonimização possível antes do envio.

## 9. Plano para dashboard de uso
Looker Studio (ou Metabase) conectado ao Airtable + planilha de custo: leads/dia, taxa de erro, custo acumulado, distribuição do ICP score.

## 10. Pitch para Comitê Executivo de Receita
20 minutos na frente da Cláudia + CFO + CTO. Mostrar: estado herdado, o que foi corrigido, ROI medido, próximos passos e pedido de evolução de orçamento se for o caso.
