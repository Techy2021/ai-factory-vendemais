# C4 — Nível 2: Containers

O diagrama C4 de nível 2 mostra os principais componentes que participam do fluxo de enriquecimento do VendeMais e como eles se relacionam.

O HubSpot fornece as oportunidades que entram no estágio de agendamento. O Make coordena todo o processo, consultando o Google Search, enviando as informações para análise pela OpenAI, armazenando os resultados no Airtable e atualizando o negócio no HubSpot.

## Diagrama
```mermaid
C4Container

title VendeMais - Diagrama de Containers

Person(revops, "Time de RevOps / Comercial", "Acompanha as oportunidades enriquecidas.")

System_Ext(hubspot, "HubSpot", "CRM utilizado como origem e destino das oportunidades.")
System_Ext(google, "Google Search", "Busca informações públicas sobre as empresas.")
System_Ext(openai, "OpenAI", "Analisa os dados e gera o enriquecimento.")
System_Ext(airtable, "Airtable", "Armazena os resultados do enriquecimento.")

System_Boundary(vendemais, "VendeMais") {

    Container(make, "Make", "Low-code / SaaS", "Orquestra o processo de enriquecimento dos leads.")

}

Rel(hubspot, make, "Envia oportunidades em appointmentscheduled", "API")
Rel(make, google, "Busca informações da empresa", "API")
Rel(google, make, "Retorna resultados da pesquisa", "API")
Rel(make, openai, "Envia resultados para análise", "API")
Rel(openai, make, "Retorna dados enriquecidos", "API")
Rel(make, airtable, "Salva dados enriquecidos", "API")
Rel(make, hubspot, "Atualiza icp_match_score e outros campos", "API")

Rel(revops, hubspot, "Consulta e acompanha as oportunidades")
```
