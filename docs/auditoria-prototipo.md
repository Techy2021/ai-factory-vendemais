# Auditoria do protótipo VendeMais

## 1. Descrição do protótipo

O protótipo é um cenário no Make.com que enriquece dados de negócios do HubSpot para apoiar a equipe de vendas. O fluxo observa negócios atualizados no estágio `appointmentscheduled`, pesquisa a empresa no Google, envia o nome e os resultados de busca a um modelo da OpenAI, grava os dados produzidos na tabela `Lead Enrichment` do Airtable e atualiza o negócio no HubSpot com a pontuação de aderência ao perfil de cliente ideal (ICP), o setor e o estado do enriquecimento.

O cenário foi criado no espaço pessoal da Joana. Embora tenha agendamento previsto a cada 15 minutos, ele está desligado e é executado manualmente uma vez por dia. A base do Airtable pertence à conta corporativa, mas as conexões usadas pelo cenário dependem de credenciais ou configurações pessoais. A auditoria se baseia nas notas e nas descrições das telas disponíveis em `docs`; não há, nessas fontes, evidência de uma inspeção direta do cenário em execução.

## 2. Lacunas identificadas

- **Operação e responsabilidade:** o cenário e as conexões estão associados ao espaço pessoal da criadora. O agendamento desligado exige intervenção diária. A migração para a conta corporativa requer importar o blueprint e recriar as conexões, pois elas não acompanham o arquivo exportado.
- **Continuidade e segurança das credenciais:** as integrações com HubSpot, OpenAI e Google usam contas ou chaves pessoais; o token do Airtable está configurado no espaço pessoal do Make. A chave da OpenAI está vinculada ao cartão pessoal da Joana e poderá ser revogada.
- **Confiabilidade:** não há tratamento de erros nos módulos críticos. Uma resposta inválida da OpenAI pode interromper o fluxo sem aviso, deixando `enrichment_status` como `pending`. A deduplicação mencionada nas notas não está comprovada pelas telas e há registros repetidos no Airtable.
- **Dados e rastreabilidade:** `deal_id` não tem garantia de unicidade na tabela. O campo `tech_stack` acumula opções equivalentes com grafias diferentes. `raw_search_results` ocupa espaço e não possui política de retenção documentada. O blueprint não está documentado e versionado como fonte controlada nas informações disponíveis.
- **Custo e desempenho:** os resultados de busca são enviados integralmente ao modelo, elevando o consumo de tokens. A tabela não registra `cost_usd` por execução; por isso, os valores mencionados nas notas são estimativas, não uma medição sistemática do custo por lead.
- **Governança de dados:** não há mapeamento documentado da LGPD para o envio de dados de empresas clientes ao Google e à OpenAI, nem avaliação registrada de contratos, transferência internacional e minimização dos dados enviados.
- **Medição de resultados:** faltam painel de uso e relatório que relacionem volume, falhas, custos e resultados comerciais. Assim, o impacto do protótipo ainda não pode ser demonstrado de forma consistente.

## 3. Avaliação inicial de riscos e prioridades

| Prioridade | Risco principal | Justificativa e ação inicial |
| --- | --- | --- |
| Crítica | Interrupção do serviço e dependência pessoal | O cenário está desligado e a chave da OpenAI pode ser revogada. Transferir a operação para a conta corporativa e substituir as credenciais pessoais. |
| Alta | Falhas silenciosas e dados incompletos | Não há tratamento de erros; negócios podem permanecer em `pending`. Registrar falhas, marcar `failed` no HubSpot e notificar a equipe responsável. |
| Alta | Registros duplicados e perda de qualidade | Atualizações do mesmo negócio podem repetir o enriquecimento; a tabela não impõe unicidade. Validar a deduplicação e adotar uma gravação controlada por `deal_id`. |
| Alta | Tratamento de dados sem avaliação formal | O fluxo envia dados a serviços externos. Documentar os dados enviados, a base legal, os contratos aplicáveis e as medidas de minimização com a área jurídica. |
| Média | Custo variável sem controle | Snippets longos aumentam tokens e não há custo por execução registrado. Limitar o texto enviado e medir tokens e `cost_usd`. |
| Média | Falta de rastreabilidade e indicadores | Sem versão controlada do blueprint ou painel, mudanças e resultados são difíceis de auditar. Versionar o cenário e definir métricas operacionais e comerciais. |

Esta classificação é preliminar. A ordem de execução deve ser confirmada com dados reais de volume, custo e falhas, além da avaliação jurídica.

## 4. Estado atual vs estado desejado

| Aspecto | Estado atual | Estado desejado |
| --- | --- | --- |
| Operação | Cenário no espaço pessoal e execução manual diária. | Cenário na conta corporativa, com agendamento controlado e responsáveis definidos. |
| Conexões | Credenciais pessoais ou mantidas no espaço pessoal do Make. | Conexões corporativas autorizadas, documentadas e sob gestão da empresa. |
| Mudanças | Estrutura sem versionamento controlado demonstrado. | Blueprint versionado em Git, com processo de publicação e detecção de alterações feitas diretamente no Make. |
| Erros | Falhas podem interromper o fluxo sem alerta e deixar o status em `pending`. | Erros registrados, status `failed` atualizado e equipe RevOps notificada. |
| Registros | Possibilidade de enriquecimentos e linhas repetidos para o mesmo `deal_id`. | Verificação de duplicidade e atualização consistente do registro do negócio. |
| Custos | Busca enviada integralmente ao modelo e custo por execução desconhecido. | Snippets limitados, consumo medido e custo registrado por execução e por mês. |
| Dados e conformidade | Dados brutos armazenados sem retenção definida e análise de LGPD pendente. | Dados minimizados, prazo de retenção definido e tratamento jurídico documentado. |
| Resultados | Sem painel e sem medida consolidada de impacto. | Indicadores de volume, erros, custos, pontuação ICP e resultados comerciais acompanhados. |

## 5. Conclusão da auditoria

O protótipo demonstra uma aplicação útil do enriquecimento de negócios: produz informações para a abordagem comercial e devolve a pontuação ICP ao HubSpot. Contudo, sua operação depende de pessoas e credenciais individuais, e as falhas e os custos não são observados de modo suficiente. Há também problemas conhecidos de duplicação e pendências de governança de dados.

A evolução recomendada começa pela continuidade operacional: migrar o cenário e as conexões para contas corporativas e restabelecer a execução controlada. Em seguida, é necessário tratar erros e duplicações, registrar custos e avaliar o fluxo de dados com a área jurídica. O versionamento do blueprint e os indicadores de uso permitirão verificar se essas mudanças aumentam a confiabilidade e produzem resultado para a equipe de vendas.
