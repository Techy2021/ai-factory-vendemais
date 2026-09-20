# Matriz de decisão de stack

## Critérios e pesos

Inicialmente foram definidos os critérios e pesos que serão utilizados na avaliação das stacks.

| Critério | Peso |
|---|---:|
| Aderência ao projeto | 25% |
| Integração com HubSpot, Airtable e APIs | 20% |
| Custo operacional | 15% |
| Manutenção pelo time de RevOps | 15% |
| Segurança e governança | 10% |
| Versionamento e CI/CD | 10% |
| Evolução futura | 5% |
| **Total** | **100%** |

Esses critérios estão relacionados ao briefing, que enfatiza automação, conta corporativa, controle de custo, versionamento, integração com sistemas e governança como requisitos mínimos para funcionamento.

## Escala de notas

Foi utilizada uma escala simples de 1 a 5:

- 1 = muito ruim
- 2 = ruim
- 3 = adequado
- 4 = bom
- 5 = muito bom

Como referência, foram utilizadas as três opções da disciplina:

- **Stack A** – n8n + Railway + Supabase
- **Stack B** – aplicação de interface com Streamlit/Gradio + hospedagem
- **Stack C** – Make + Airtable + integrações com SaaS

## Avaliação das stacks

### Aderência ao projeto

| Stack | Nota | Justificativa |
|---|---:|---|
| Stack A | 4 | Atende bem automações e integrações. |
| Stack B | 2 | É mais adequada quando a interface é parte central da solução. |
| Stack C | 5 | Possui maior aderência ao cenário atual de integração SaaS do VendeMais. |

### Integração com HubSpot, Airtable e APIs

| Stack | Nota | Justificativa |
|---|---:|---|
| Stack A | 4 | O n8n integra bem com APIs e possui grande variedade de conectores. |
| Stack B | 3 | Consegue integrar via código e APIs, mas exige mais desenvolvimento e manutenção. |
| Stack C | 5 | É voltada para integração entre ferramentas SaaS, utilizando conectores e menos código. |

A Stack C faz sentido para o projeto porque o fluxo depende diretamente de ferramentas como HubSpot, Airtable e serviços externos.

### Custo operacional

| Stack | Nota | Justificativa |
|---|---:|---|
| Stack A | 4 | Possui custo baixo para projetos pequenos, mas envolve hospedagem e manutenção. |
| Stack B | 3 | Exige hospedagem da aplicação e mais recursos, dependendo da interface e do uso. |
| Stack C | 4 | Apesar de ter custo mensal, reduz esforços de desenvolvimento e manutenção. |

### Manutenção pelo time de RevOps

| Stack | Nota | Justificativa |
|---|---:|---|
| Stack A | 4 | O n8n é visual e facilita a manutenção, mas ainda exige conhecimento técnico de infraestrutura e integrações. |
| Stack B | 2 | Exige desenvolvimento em código e aumenta a dependência de conhecimento técnico. |
| Stack C | 5 | As ferramentas estão mais próximas da rotina do time e permitem ajustes com menos código. |

### Segurança e governança

| Stack | Nota | Justificativa |
|---|---:|---|
| Stack A | 5 | Permite maior controle sobre o ambiente, principalmente quando hospedado em infraestrutura própria. |
| Stack B | 4 | Oferece bom controle, mas depende de como a aplicação é desenvolvida e de como as informações sensíveis são gerenciadas. |
| Stack C | 3 | Facilita a operação, mas parte da governança e da infraestrutura fica sob responsabilidade de serviços externos. |

### Versionamento e CI/CD

| Stack | Nota | Justificativa |
|---|---:|---|
| Stack A | 5 | O n8n permite exportar workflows e integrá-los ao Git, além de permitir automações de deploy e CI/CD. |
| Stack B | 5 | Se encaixa naturalmente no GitHub, branches, versionamento, testes e pipelines de CI/CD. |
| Stack C | 3 | É possível versionar, mas o processo é menos direto que em soluções baseadas em código ou arquivos locais. |

### Evolução futura

| Stack | Nota | Justificativa |
|---|---:|---|
| Stack A | 5 | O n8n oferece liberdade para integrar novas APIs e aumentar a complexidade do fluxo. |
| Stack B | 5 | Como a solução é baseada em código, praticamente qualquer funcionalidade pode ser desenvolvida. |
| Stack C | 4 | Permite evoluir com novos módulos, mas fica dependente dos recursos da plataforma. |

## Matriz final

| Critério | Peso | Stack A | Stack B | Stack C |
|---|---:|---:|---:|---:|
| Aderência ao projeto | 25% | 4 | 2 | 5 |
| Integração com HubSpot, Airtable e APIs | 20% | 4 | 3 | 5 |
| Custo operacional | 15% | 4 | 3 | 4 |
| Manutenção pelo time de RevOps | 15% | 4 | 2 | 5 |
| Segurança e governança | 10% | 5 | 4 | 3 |
| Versionamento e CI/CD | 10% | 5 | 5 | 3 |
| Evolução futura | 5% | 5 | 5 | 4 |

## Pontuação ponderada

| Critério | Peso | Stack A | Stack B | Stack C |
|---|---:|---:|---:|---:|
| Aderência ao projeto | 25% | 1,00 | 0,50 | 1,25 |
| Integração com HubSpot, Airtable e APIs | 20% | 0,80 | 0,60 | 1,00 |
| Custo operacional | 15% | 0,60 | 0,45 | 0,60 |
| Manutenção pelo time de RevOps | 15% | 0,60 | 0,30 | 0,75 |
| Segurança e governança | 10% | 0,50 | 0,40 | 0,30 |
| Versionamento e CI/CD | 10% | 0,50 | 0,50 | 0,30 |
| Evolução futura | 5% | 0,25 | 0,25 | 0,20 |
| **Pontuação final** | **100%** | **4,25** | **3,00** | **4,40** |

## Resultado da matriz

A partir dos critérios definidos, a Stack C apresentou a maior pontuação, com 4,40, seguida da Stack A, com 4,25, e da Stack B, com 3,00.

A diferença entre a Stack A e a Stack C foi pequena. A Stack A apresentou vantagens relacionadas à segurança, versionamento e flexibilidade técnica. A Stack C se destacou pela facilidade de integração com as ferramentas que já fazem parte do projeto VendeMais.

Como o protótipo já utiliza Make, HubSpot e Airtable, a Stack C permite aproveitar boa parte do trabalho existente, evitando uma reconstrução desnecessária.

A matriz não indica que o Make seja a solução ideal em qualquer situação, mas mostra que, para este projeto e para os critérios definidos, a Stack C apresentou a maior aderência.