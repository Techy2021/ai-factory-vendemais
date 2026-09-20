# ADR-002 — Ambiente de produção

## Status

Aceito

## Contexto

O VendeMais já foi construído no Make e essa ferramenta continua sendo a principal opção para executar o fluxo em produção.

O n8n será mantido apenas como ambiente de apoio para testes locais, sem substituir o Make no ambiente produtivo.

## Decisão

O fluxo de produção será executado no Make, utilizando contas e credenciais corporativas.

O n8n será utilizado para testes e validações locais.

## Consequências

Usar o Make em produção permite aproveitar o fluxo que já existe e facilita a operação pelo time.

Como ponto de atenção, será necessário manter as credenciais corporativas organizadas e acompanhar os custos e possíveis falhas da plataforma.

## Alternativas consideradas

### n8n em produção

Oferece maior controle técnico, mas exige mais infraestrutura e manutenção.

### Aplicação própria

Daria mais liberdade, porém exigiria mais desenvolvimento e fugiria da proposta atual do projeto.
