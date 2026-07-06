# Briefing — Projeto Lead Enrichment VendeMais

**De:** Cláudia Mendes, Diretora de Receita — VendeMais
**Para:** RevOps Specialist (você)
**Data:** início deste ano

---

Bem-vindo(a) ao time de Receita. Sou a Cláudia, Diretora de Receita da VendeMais há quatro anos. Deixa eu te situar.

## A VendeMais

Somos uma das maiores empresas de B2B SaaS de vendas do Brasil. Hoje somos 1.500 funcionários, ARR na casa das centenas de milhões, e atendemos desde médias empresas até grandes contas no Brasil e LatAm. Nossa missão é simples: fazer times de vendas B2B baterem meta com previsibilidade, usando dados e automação.

Vendas é nosso produto, e vendas é também nosso processo interno. Por isso a área de RevOps (Revenue Operations), que reporta direto pra mim, é estratégica. É onde você entra.

## Sua função

Você é RevOps Specialist com viés técnico. Não é engenheiro(a) de software, mas mexe com no-code/low-code, escreve um pouco de script, entende APIs, lê documentação técnica. Vai sentar no time de Receita, ao lado de SDRs, AEs e Marketing Ops.

## O contexto que você herda

No segundo semestre do ano passado, contratei uma estagiária excelente, a Joana. Em três meses ela construiu, sozinha no Make.com, um cenário que enriquece nossos leads automaticamente: o deal entra no estágio "appointmentscheduled" no HubSpot, o Make dispara busca no Google sobre a empresa, manda os resultados pro OpenAI, que devolve um JSON com industry, tech stack, sinais de compra e um ICP match score de 0 a 100. Esse score volta pro HubSpot e ajuda o AE a priorizar.

Funcionou. Os vendedores adoraram. Recebemos cerca de 5.000 leads novos por mês e o enrichment economiza horas de pesquisa manual.

**O problema:** a Joana saiu em dezembro pra fazer mestrado fora. O cenário está no espaço pessoal Make dela, com a API key OpenAI dela (saindo do CPF dela!), sem documentação, sem export do blueprint, sem versionamento. Hoje alguém do meu time clica "run" manualmente todo dia porque desliguei o scheduler pra não estourar a quota pessoal dela. Isso não é sustentável.

## O que espero em 12 semanas

1. Cenário migrado pra conta corporativa VendeMais, rodando 100% automatizado.
2. Blueprint do Make versionado em GitHub, com CI/CD via GitHub Actions sincronizando via API Make.
3. Dashboard de uso: custo por execução, taxa de erro, leads enriquecidos/dia.
4. Mapeamento LGPD do fluxo (dados de empresa-cliente passando por Google + OpenAI nos EUA).
5. Pitch de 20 minutos pro Comitê Executivo de Receita pedindo evolução do projeto.

## Restrições

- **Orçamento:** US$ 50/mês (Make Starter + LLM). Negociável só com bom business case.
- **LGPD:** dados de CRM são propriedade dos nossos clientes B2B. Múltiplas bases legais cruzadas. Não improvise.
- **Segurança:** nada de credencial pessoal. Tudo conta corporativa, tudo auditável.

Conta comigo no que precisar. Bem-vindo(a) à VendeMais.

— Cláudia
