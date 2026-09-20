# C4 — Nível 1: Contexto

Para esta atividade, o diagrama C4 foi utilizado para representar de forma simples a estrutura do VendeMais e mostrar como os sistemas envolvidos se conectam no processo de enriquecimento dos leads.

O VendeMais apoia o time comercial no enriquecimento dos leads. O processo recebe oportunidades do HubSpot, busca informações da empresa no Google, utiliza a OpenAI para analisar os dados, salva o enriquecimento no Airtable e atualiza o negócio no HubSpot. O fluxo é orquestrado pelo Make.

## Diagrama
```mermaid
C4Context

title VendeMais - Diagrama de Contexto

Person(revops, "Time de RevOps / Comercial", "Utiliza as informações dos leads enriquecidos.")

System(vendemais, "VendeMais", "Sistema responsável pelo enriquecimento de leads.")

System_Ext(hubspot, "HubSpot", "CRM utilizado para receber e atualizar oportunidades.")
System_Ext(make, "Make", "Plataforma que executa e orquestra o fluxo de automação.")
System_Ext(google, "Google Search", "Busca informações públicas sobre as empresas.")
System_Ext(openai, "OpenAI", "Analisa as informações e gera os dados de enriquecimento.")
System_Ext(airtable, "Airtable", "Armazena os dados enriquecidos.")

Rel(revops, vendemais, "Utiliza")
Rel(hubspot, vendemais, "Envia oportunidades")
Rel(vendemais, make, "Executa o fluxo por meio de")
Rel(vendemais, google, "Busca informações")
Rel(vendemais, openai, "Envia informações para análise")
Rel(vendemais, airtable, "Armazena os dados enriquecidos")
Rel(vendemais, hubspot, "Atualiza a oportunidade")
```
