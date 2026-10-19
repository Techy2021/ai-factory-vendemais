# Retenção e exclusão — Etapa 2.2E

Implementação da [política adotada](lgpd-mapa-dados.md), sem deploy no Make nem limpeza real executada nesta entrega.

## Airtable: critério e ação

`scripts/retention_cleanup.py` usa a API real do Airtable, biblioteca padrão Python e os IDs de campos extraídos do módulo 19 do blueprint. Base e tabela são argumentos explícitos, para separar homologação e produção. O PAT fica em `AIRTABLE_RETENTION_PAT`, com acesso apenas à base autorizada e escopos `data.records:read` e `data.records:write`. Não é carregado de `.env` automaticamente e nunca é impresso.

- **30 dias:** havendo conteúdo bruto e `enriched_at <= agora UTC - 30 dias`, executa `PATCH` com apenas o campo `raw_search_results: null`. Preserva registro, score e todos os demais campos.
- **180 dias:** exclui o registro Airtable via `DELETE` somente se tanto `createdTime` quanto `enriched_at` forem válidos e tiverem pelo menos 180 dias. Usa o mais recente dos dois marcos para evitar exclusão prematura.
- Data de enriquecimento ausente, inválida, sem fuso ou futura impede qualquer ação. Criação desconhecida impede exclusão do registro inteiro, mas não a limpeza de conteúdo bruto comprovadamente vencido.
- `enriched_at` é o marco disponível para a coleta no projeto; ocorre após a busca. Não há timestamp próprio de coleta. Essa aproximação pode atrasar a limpeza pelo intervalo entre busca e gravação.
- Lista todas as páginas antes de mutar e relê cada registro elegível antes de escrever. É idempotente; campo já vazio não é limpo novamente. Falha interrompe a rotina com código diferente de zero, sem expor payload/token e sem retry automático. Alterações anteriores à falha não são revertidas.

Referências: [paginação Airtable](https://support.airtable.com/docs/getting-started-with-airtables-web-api), [atualização de registro](https://airtable.com/developers/web/api/update-record).

## Como disparar

Com Python 3.11+, injete `AIRTABLE_RETENTION_PAT` pelo cofre/ambiente do processo. Use primeiro uma base sintética de homologação, com os mesmos IDs de campos do blueprint; IDs diferentes exigem adaptar o mapeamento antes de executar. Não inclua tokens na linha de comando.

```powershell
# Somente leitura e planejamento (ainda consulta a API).
python scripts/retention_cleanup.py --base-id appBASE_AUTORIZADA --table-id tblTABELA_AUTORIZADA
# Aplicação irreversível na base especificada.
python scripts/retention_cleanup.py --base-id appBASE_AUTORIZADA --table-id tblTABELA_AUTORIZADA --apply
```

O workflow independente `.github/workflows/retention.yml` permite disparo manual, com `apply=false` por padrão, e aplicação diária às **03:00 de São Paulo (06:00 UTC)**. Cadastre o Secret `AIRTABLE_RETENTION_PAT` e as Variables `AIRTABLE_RETENTION_BASE_ID` e `AIRTABLE_RETENTION_TABLE_ID` para a base autorizada. O agendamento depende de publicação na branch padrão e configuração no GitHub; **não foi ativado nem executado nesta entrega**. Não utiliza o CD Make. Execuções agendadas podem atrasar; com frequência diária, a exclusão pode ocorrer até aproximadamente um dia após vencer o prazo. Para limite estrito, aumentar frequência ou adotar prazo operacional menor antes da ativação.

## Históricos/prompts

O Compose do mirror n8n configura poda nativa automática em 720 horas, sem limite por quantidade, buffer de exclusão zero e ciclos de um minuto. Para aplicar localmente, quando autorizado:

```powershell
docker compose -f n8n-mirror/docker-compose.yml up -d
```

A poda trata execuções concluídas e seus dados, incluindo entradas/saídas dos nodes; não altera registros Airtable nem workflows. O marco nativo é a conclusão da execução, não o início; execuções longas e os ciclos de poda podem ultrapassar 30 dias desde o início. Execuções em andamento/espera e exceções do n8n, como execuções anotadas, requerem revisão separada. Não se afirma remoção de backups. Não foi iniciado/recriado container para validar a poda real. Referências: [poda n8n](https://docs.n8n.io/hosting/scaling/execution-data/), [variáveis de execução](https://docs.n8n.io/hosting/configuration/environment-variables/executions/).

**Produção Make e provedores:** esta implementação não apaga históricos/prompts do Make, Brave ou Gemini. Não foi verificado endpoint de exclusão nem configuração contratada; confirmar retenção e eliminação com cada fornecedor/DPA. O mirror local não comprova cumprimento em produção. O score armazenado no HubSpot, o CRM de origem e backups também não são excluídos por esta rotina.

## Exemplo e teste sintéticos

Em `2026-10-13T12:00:00Z`, um registro criado/enriquecido em `2026-09-03T12:00:00Z` (40 dias) com busca `Synthetic search: Acme Test` e score 82 passa a ter busca vazia, mantendo o mesmo registro e score. Um registro de 10 dias permanece intacto. Um registro com criação e enriquecimento há 181 dias é excluído do Airtable.

```powershell
python tests/test_retention_cleanup.py
```

Testes isolados com cliente simulado, sem rede: limites 30/180 dias, proteção de registros recentes, datas/fusos, dry-run, limpeza parcial, idempotência, releitura, paginação, payload PATCH e configuração de poda. Não comprovam comportamento remoto.

## Limitações operacionais

Não execute em base de cliente sem instrução válida do controlador. Exceções de conservação devem ser decididas antes da execução: o script não possui campo de bloqueio jurídico e não detecta essas exceções. Não há transação entre releitura e escrita; execute sem atualizações concorrentes nos registros elegíveis. A listagem mantém em memória os campos solicitados, sem gravá-los em disco. Grandes bases podem exigir processamento em lotes. Histórico de revisões/lixeira/backups do Airtable não equivale ao campo ativo: confirmar expiração do fornecedor, sem presumir apagamento físico imediato. A correspondência dos IDs de campos com o schema remoto deve ser validada antes da ativação.
