# ADR-001 — Escolha da Stack

## Status

Aceito

## Contexto

O VendeMais já possui um fluxo funcionando no Make, integrado ao HubSpot, Google, OpenAI e Airtable.

A auditoria mostrou que o fluxo funciona, mas ainda precisa melhorar pontos como automação, credenciais, tratamento de erros, custo e controle de dados.

Foi construída uma matriz de decisão de stack, onde foram comparadas três opções com base em critérios como integração, custo, manutenção, segurança e evolução do sistema.

A Stack C obteve a maior pontuação na matriz.

## Decisão

A Stack C será mantida como principal solução do projeto, utilizando ferramentas SaaS e integrações de baixo código.

A escolha permite aproveitar o que já existe no projeto e evitar refazer o fluxo do zero.

## Consequências

A Stack C facilita a manutenção do VendeMais e aproveita as ferramentas que já fazem parte do projeto.

Como ponto negativo, o sistema continua dependente de serviços externos e exige atenção aos custos, ao uso de credenciais e à disponibilidade das plataformas.

## Alternativas consideradas

### Stack A

Oferece maior controle técnico, mas exige mais manutenção.

### Stack B

Permitiria criar uma aplicação própria, mas não combina tanto com o foco do VendeMais, que é integrar sistemas.
