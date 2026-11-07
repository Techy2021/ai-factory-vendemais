# API do dashboard

Com as dependências de `requirements.txt` instaladas, inicie a API a partir de
`backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1 --no-access-log
```

O comando presume um ambiente virtual em `backend\.venv`. Em desenvolvimento,
defina `VENDEMAIS_ENV=development` antes de iniciar o processo para acessar a
documentação em `http://localhost:8001/docs`.
O log de acesso é desativado nesse comando para evitar registrar URLs e
parâmetros de consulta. Logs de proxies ou servidores externos também devem
ser configurados para não registrar informações pessoais, senhas, cabeçalhos
`Cookie` ou `Set-Cookie`, nem corpos de requisições de autenticação.

Quando existir `frontend/dist`, a API serve seu `index.html` em `/` e os
demais arquivos reais desse diretório por seus caminhos. Não há fallback SPA:
caminhos e arquivos inexistentes retornam 404. Sem o diretório de build, `/`
retorna 503 e as rotas da API permanecem disponíveis. O build do frontend deve
ser gerado separadamente; não exponha arquivos internos dentro de `dist`.

## Configuração da autenticação

Consulte [`.env.example`](.env.example) para os nomes das variáveis. A aplicação
lê as variáveis do ambiente do processo; não carrega automaticamente um arquivo
`.env`. Defina:

- `VENDEMAIS_ENV`: `production` por padrão; `development` habilita a
  documentação e permite o cookie HTTP local. Valor inválido impede o início.
  A configuração é lida na inicialização; reinicie após alterá-la.
- `VENDEMAIS_ADMIN_PASSWORD`: senha administrativa forte e única, fornecida
  pelo ambiente ou gerenciador de segredos, nunca versionada.
- `VENDEMAIS_ALLOWED_ORIGIN`: origem exata do dashboard, incluindo esquema e
  porta quando aplicável, sem caminho ou barra final. Em produção deve usar
  HTTPS, por exemplo `https://dashboard.example.com`.
- `VENDEMAIS_COOKIE_SECURE`: `true` por padrão e obrigatório em produção.
  `false` é aceito apenas em desenvolvimento com origem HTTP de loopback
  (`localhost`, `127.0.0.1` ou `[::1]`).

Em produção, `/docs`, `/redoc` e `/openapi.json` retornam 404. Ocultá-los não
substitui autenticação, TLS ou outras proteções.

Em produção, sirva o dashboard e a API pela mesma origem HTTPS (por exemplo,
através de um proxy reverso). O CORS permite credenciais apenas para a origem
exata validada em `VENDEMAIS_ALLOWED_ORIGIN`, com métodos GET e POST e cabeçalho
`Content-Type`. O proxy deve proteger o tráfego com TLS, respeitar essa origem
e não registrar dados sensíveis.
Configuração ausente ou inválida impede a autenticação e o uso de sessões.
Para desenvolvimento local, defina `VENDEMAIS_ENV=development`, configure a
origem como `http://localhost:5173`, use `VENDEMAIS_COOKIE_SECURE=false` e acesse a API em
`http://localhost:8001`; não misture `localhost` e `127.0.0.1`. Configure
`VITE_API_BASE_URL` no frontend conforme o
[guia do dashboard](../frontend/README.md).

Para a leitura do Airtable, forneça também `AIRTABLE_API_TOKEN`,
`AIRTABLE_BASE_ID` e `AIRTABLE_TABLE_ID` no ambiente do processo. Use acesso
restrito à base e à tabela; não coloque valores sensíveis em arquivos
versionados ou logs.

## Autenticação

- `POST /auth/login` recebe JSON `{"password": "..."}` e, em caso de sucesso,
  retorna 204 com cookie `vendemais_session`, HttpOnly e SameSite=Strict.
  O cookie é Secure por padrão e expira após oito horas.
- `POST /auth/logout` retorna 204, revoga a sessão apresentada e apaga o cookie.
- Ambos exigem exatamente um cabeçalho `Origin` igual a
  `VENDEMAIS_ALLOWED_ORIGIN`, inclusive para clientes não navegadores. Uma
  origem ausente ou diferente retorna 403; isso protege as operações de sessão
  contra CSRF, incluindo login CSRF.
- Até cinco tentativas de login com corpo válido e origem autorizada são
  permitidas globalmente a cada cinco minutos, incluindo sucessos; exceder o
  limite retorna 429 com `Retry-After`. Senha incorreta retorna 401.

O frontend solicita o envio do cookie com `credentials: "include"`.
Sem sessão válida, os endpoints de negócio retornam 401.

## Contrato dos endpoints

- `GET /health`: retorna `{"status": "ok"}`.
- `GET /api/leads`: retorna uma resposta com `items`, `total`, `page` e
  `page_size`. Cada item contém `deal_id`, `company_name`, `industry`,
  `size_employees`, `tech_stack`, `icp_match_score` e `enriched_at`.
  Todos os campos podem ser nulos, inclusive `deal_id`. `tech_stack`
  é uma lista de strings ou `null`; texto de origem é preservado em um único
  item. `icp_match_score` é um número finito entre 0 e 100,
  inclusive valores decimais. Valores ausentes ou inválidos são retornados como
  `null` e contados como ausentes nas métricas.
- `GET /api/metrics`: retorna `leads_total`, `average_score`,
  `missing_score_count` e `unique_deals`. A média considera apenas scores
  válidos e é `null` quando não há scores válidos.

Os endpoints de negócio aceitam `start_date` e `end_date` opcionais no formato
`YYYY-MM-DD`. O período filtra `enriched_at` por datas inclusivas
em UTC; a data inicial não pode ser posterior à final. `/api/leads` também
aceita `page` (mínimo 1, padrão 1) e `page_size` (1 a 100, padrão 20).
Parâmetros inválidos retornam HTTP 422. Registros sem data são incluídos sem
filtro de período e excluídos quando há pelo menos um limite de data.

Com sessão e parâmetros válidos, os endpoints consultam o Airtable. Se a
configuração da fonte estiver ausente ou inválida, retornam HTTP 503:

```json
{"code": "DATA_SOURCE_NOT_CONFIGURED", "message": "Fonte de dados nao configurada."}
```

Falhas de acesso ou de validação da fonte também retornam 503, com código
`DATA_SOURCE_UNAVAILABLE`, sem expor detalhes sensíveis.

As sessões e o limitador existem somente na memória de um processo. Reiniciar
invalida as sessões e reinicia a contagem; múltiplos workers ou réplicas não
compartilham estado e enfraquecem o limite. Use um único worker e uma única
réplica até existir armazenamento compartilhado e limitação distribuída.
O limite global pode ser esgotado por outros usuários; aplique também controle
de taxa no proxy. Alterações na senha exigem reiniciar o processo para invalidar
sessões existentes. A autenticação usa uma única senha administrativa, sem
contas individuais, MFA ou recuperação de senha.

## Verificação local

Com a API em execução, por exemplo:

```powershell
Invoke-RestMethod http://localhost:8001/health
curl.exe -i "http://localhost:8001/api/leads"
```

Para testar login e logout no navegador, configure a origem local exata, use
`VENDEMAIS_COOKIE_SECURE=false` e acesse o dashboard em
`http://localhost:5173`. Depois do login, confira os endpoints protegidos e
execute logout. Não coloque senhas ou cookies em URLs ou comandos registrados
no histórico.

Para executar somente os testes de autenticação, a partir de `backend`:

```powershell
$env:VENDEMAIS_ENV = "development"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_auth.py"
```
