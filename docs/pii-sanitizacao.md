# Sanitização antes do Gemini — Etapa 2.2D

No blueprint Make, o novo módulo 29 (`util:SetVariable2`) fica entre Brave Search (8) e Gemini (18). Serializa toda a resposta `8.data` com `toJSON` e aplica substituições globais; o prompt Gemini recebe somente `29.sanitized_search`, seguido das instruções existentes. Não há fallback para resposta bruta. A serialização inclui campos aninhados, títulos e URLs, evitando sanitizar apenas snippets e deixar outro campo passar ao modelo.

Usa a função nativa [replace do Make](https://help.make.com/text-and-binary-functions), com expressões regulares. Não requer serviço externo de sanitização nem outra chave. Exemplos exclusivamente sintéticos:

| Antes | Depois |
| --- | --- |
| `ana@example.test` | `[EMAIL]` |
| `+55 (11) 00000-0000` | `[TELEFONE]` |
| `000.000.000-00` | `[CPF_OU_NUMERO_PESSOAL]` |
| `Nome completo: Pessoa Sintética.` | `Nome completo: [NOME].` |
| `Acme Labs: 250 funcionários; AWS; Série B.` | Preservado |

Onze dígitos contíguos são mascarados conservadoramente sem validar CPF: também podem representar telefone nacional. Telefones brasileiros com DDD, prefixo +55 e números locais com hífen são tratados. Nomes exigem rótulo explícito (`Nome completo`, `Contato`, `Responsável`, `Full name`), duas a seis partes capitalizadas e término delimitado; partículas portuguesas são admitidas. Não se tenta classificar todo texto capitalizado como pessoa.

## Verificação direcionada

Execute `node tests/test_pii_sanitization.cjs` (Node.js 18+). O teste extrai as regras diretamente do blueprint e as executa em JavaScript, cobrindo casos sintéticos positivos, preservação empresarial, campos aninhados e ausência de caminho bruto para Gemini. Compara os módulos originais com `HEAD` para detectar alterações fora do sanitizador e da referência inicial do prompt; esse controle de escopo corresponde a esta alteração e deverá ser atualizado ao mudar a versão-base do blueprint.

## Limitações e estado

- Regras não garantem anonimização: nomes sem rótulo, formatos incomuns, dados codificados/escapados, endereços, documentos estrangeiros e inferências identificáveis podem permanecer. Nomes em minúsculas ou totalmente maiúsculos não são reconhecidos pela regra conservadora.
- Pode haver falsos positivos em sequências numéricas e texto rotulado como contato/responsável. Não há validação de dígitos verificadores.
- A consulta enviada à Brave continua contendo o título original. O Airtable continua recebendo a busca bruta; históricos do Make também podem conter dados anteriores à sanitização. Esta etapa protege somente a entrada do LLM.
- O teste local verifica regex, estrutura e isolamento das mudanças; não executa o interpretador IML remoto. Importação e execução controlada em homologação ainda precisam confirmar a avaliação das expressões no Make. Nenhuma implantação foi realizada nesta etapa.
- A sanitização não substitui base legal, teste de balanceamento ou controles de transferência/retensão. Não é filtro de prompt injection.
