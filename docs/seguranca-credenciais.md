# Segurança de credenciais — Etapa 2.2A

## Ambientes e armazenamento

Use contas corporativas e credenciais distintas para desenvolvimento/homologação e produção. Nunca copie secrets de produção para testes, exemplos, blueprints, commits ou logs.

| Credencial/configuração | Desenvolvimento/homologação | Produção |
| --- | --- | --- |
| `MAKE_API_KEY` | Chave de teste no cofre corporativo; `.env` local ignorado somente se necessário. | GitHub Actions Secret `MAKE_API_KEY`, com menor acesso disponível. |
| `BRAVE_SEARCH_API_KEY` | Chave de teste no cofre corporativo e no cenário de homologação; `.env` local opcional. | GitHub Actions Secret `BRAVE_SEARCH_API_KEY`; CD injeta a chave em memória no blueprint enviado ao Make. Restringir acesso e exportação do módulo HTTP remoto. |
| Gemini | Chave de teste na conexão Gemini do Make de homologação. | Chave corporativa de produção na conexão Gemini do Make. Não há variável local consumida pelo projeto. |
| HubSpot OAuth / Airtable PAT | Conexões próprias para dados e bases de teste. | Conexões corporativas do Make, com acesso mínimo necessário. |
| `MAKE_SCENARIO_ID` / `MAKE_REGION` | Configuração própria do cenário de homologação. | GitHub Actions Variables com esses nomes; não são secrets. |

Mantenha no cofre corporativo o inventário, os responsáveis e as datas de rotação. O `.env` local é opcional e não é carregado automaticamente pelo CD ou Docker Compose atual. O mirror n8n offline dispensa credenciais externas.

**Limite atual:** o CD usa Secrets/Variables do repositório, sem declarar GitHub Environment nem selecionar homologação/produção. Mantenha esse CD direcionado à produção; para homologação, use cenário e conexões separados, com importação manual e agendamento desativado. Essa separação é uma regra operacional, não isolamento automatizado comprovado. Não troque temporariamente secrets de produção para testar. O `.gitignore` não protege arquivos já rastreados.

## Rotação simples

1. **Responsável:** administrador corporativo de integrações/RevOps executa a rotação; mantenedor do repositório atualiza GitHub Secrets. Registre no cofre quem ocupa esses papéis e o ambiente afetado.
2. **Quando:** a cada 90 dias, ou antes se o provedor exigir; também em desligamento/mudança de acesso, suspeita de exposição ou identificação de credencial pessoal. Em comprometimento confirmado, revogue imediatamente.
3. **Substituição:** gere nova chave/token com acesso mínimo no mesmo ambiente. Atualize o cofre e o armazenamento da tabela. Para OAuth, reautorize a conexão corporativa. Para Brave em produção, atualizar o GitHub Secret não troca a chave já presente no cenário: execute o CD autorizado para publicar a substituição. Não versione exportações com secrets.
4. **Validação:** valide primeiro em homologação com dados de teste. Em produção, em janela acordada, confirme autenticação Make e uma execução controlada incluindo Brave, Gemini, gravação Airtable e atualização HubSpot. Essa execução grava dados e pode gerar custo. Registre data, responsável e resultado, sem payloads ou tokens. Em falha, corrija antes de revogar a chave anterior, salvo comprometimento.
5. **Revogação:** após validar, revogue a credencial anterior no provedor, remova cópias locais e acessos antigos e confirme que ela deixou de autenticar. Registre conclusão e próxima rotação no cofre. Se houve exposição no Git, revogue e substitua primeiro: apagar o valor atual não elimina o histórico.
