# Dashboard VendeMais

## Endereço da API

O frontend usa `VITE_API_BASE_URL`, incorporada pelo Vite ao iniciar o servidor
de desenvolvimento ou gerar a aplicação. O valor é público: nunca coloque
senhas, tokens ou outras credenciais nessa variável.

Em desenvolvimento, a variável pode ficar ausente ou vazia para usar
`http://localhost:8001`. Para outro endereço, defina uma origem HTTPS ou uma
origem HTTP de loopback, por exemplo `http://localhost:8001`. Configure a
variável no ambiente ou em um arquivo local baseado em `.env.example` e reinicie
o Vite após alterá-la.

Em produção, deixe `VITE_API_BASE_URL` ausente ou vazia para usar a origem
HTTPS atual do navegador, quando dashboard e API compartilham o mesmo serviço.
Para uma API separada, configure antes da geração uma origem HTTPS absoluta,
por exemplo `https://api.example.com`, sem credenciais, caminho, consulta ou
fragmento. Sem configuração explícita, a ausência de contexto de navegador ou
uma origem não HTTPS causa erro controlado; não existe fallback para localhost
em produção. Testes locais com HTTP devem usar o servidor de desenvolvimento,
não uma aplicação de produção.

A origem usada no navegador deve ser compatível com a origem autorizada no
backend e com as políticas CORS e `SameSite` dos cookies. Em produção, use
HTTPS e configure essas políticas conforme a implantação; CORS não contorna
restrições de cookies entre sites.
