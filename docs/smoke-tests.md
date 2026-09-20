# Smoke Tests — Etapa 1

Foram executados os testes existentes do projeto por meio dos comandos:

```powershell
python tests/validate_workflows.py
python tests/test_enrichment_logic.py
```

## Resultado

As 15 verificações passaram: 10 no validador estrutural dos workflows e 5 no teste da lógica de enriquecimento. Não houve falhas nem erros de execução.

## Três cenários de smoke test

1. **Estrutura do blueprint Make:** o fluxo contém pelo menos cinco módulos, cobrindo a estrutura básica do cenário.
2. **Conexões do mirror n8n:** todas as conexões referenciam nós existentes, cobrindo a integridade básica do fluxo local.
3. **Leitura do resultado do LLM:** o JSON simulado produz um `icp_match_score` inteiro e dentro da faixa de 0 a 100.

Esses testes verificam artefatos e lógica local. Eles não executam o cenário no Make nem validam as integrações com serviços externos.
