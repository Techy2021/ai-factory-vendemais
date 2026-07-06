#!/usr/bin/env python3
"""
Teste de logica do enriquecimento de leads com LLM MOCKADO.

Exercita as duas pecas que o cenario Make/n8n faz "por dentro":
  1. Montagem do prompt (company_name + search_results -> texto do usuario)
  2. Parsing do JSON devolvido pelo LLM -> extracao/validacao do fit-score (0-100)

NAO chama OpenAI/Anthropic nem rede. O "LLM" e um mock deterministico.
Roda: python tests/test_enrichment_logic.py
"""
import json
import sys

# ---------------------------------------------------------------------------
# Logica sob teste (espelha o que o modulo OpenAI faz no Make/n8n)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Você é um analista de inteligência de vendas B2B. "
    "Sempre responde em JSON válido, sem texto antes ou depois."
)


def build_user_prompt(company_name, search_results, max_snippet=500):
    """Monta o prompt do usuario. Trunca snippets (a Joana NAO fazia isso -> custo)."""
    trimmed = [
        {**r, "snippet": (r.get("snippet", "")[:max_snippet])}
        for r in search_results
    ]
    return (
        f"Você é um analista de inteligência de vendas. "
        f"Recebeu o nome da empresa: {company_name} "
        f"e os resultados de busca: {json.dumps(trimmed, ensure_ascii=False)}. "
        'Retorne em JSON: {"industry": "...", "size_employees": "...", '
        '"tech_stack": [...], "buying_signals": [...], '
        '"icp_match_score": 0-100, "talking_points": [...]}'
    )


def parse_fit_score(llm_raw):
    """Parseia o content do LLM e extrai um icp_match_score inteiro 0-100.

    Lanca ValueError se o JSON for invalido ou o score sair da faixa
    (replica a fragilidade: sem isso o cenario morre silencioso).
    """
    data = json.loads(llm_raw)  # pode estourar JSONDecodeError -> erro real
    score = int(data["icp_match_score"])
    if not 0 <= score <= 100:
        raise ValueError(f"icp_match_score fora da faixa 0-100: {score}")
    return score


# ---------------------------------------------------------------------------
# LLM mockado
# ---------------------------------------------------------------------------

def mock_llm(messages):
    """Devolve um content fixo (formato OpenAI: choices[0].message.content string)."""
    return json.dumps({
        "industry": "Logística",
        "size_employees": "100-500",
        "tech_stack": ["AWS", "Salesforce"],
        "buying_signals": ["captou Série B"],
        "icp_match_score": 82,
        "talking_points": ["Mencionar caso de last-mile"],
    }, ensure_ascii=False)


def mock_llm_broken(messages):
    """Simula a OpenAI devolvendo JSON quebrado (acontecia ~3x/mes)."""
    return '{"industry": "Logística", "icp_match_score": 8'  # cortado


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def expect(cond, msg):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {msg}")
    else:
        failed += 1
        print(f"  [FALHOU] {msg}")


SEARCH = [
    {"title": "Acme - About", "link": "http://a", "snippet": "X" * 1200},
    {"title": "Acme - News", "link": "http://b", "snippet": "Série B captada"},
]

# 1) prompt contem o nome da empresa
prompt = build_user_prompt("Acme Logística SA", SEARCH)
expect("Acme Logística SA" in prompt, "prompt inclui o nome da empresa")

# 2) snippets sao truncados a 500 chars (correcao da divida de custo)
parsed_back = json.loads(prompt.split("resultados de busca: ", 1)[1].rsplit(". Retorne", 1)[0])
expect(all(len(r["snippet"]) <= 500 for r in parsed_back), "snippets truncados a <= 500 chars")

# 3) system prompt exige JSON
expect("JSON" in SYSTEM_PROMPT, "system prompt exige resposta em JSON")

# 4) parsing extrai fit-score inteiro 0-100 do LLM mockado
score = parse_fit_score(mock_llm([SYSTEM_PROMPT, prompt]))
expect(score == 82 and isinstance(score, int), "fit-score parseado = 82 (int, faixa 0-100)")

# 5) JSON quebrado levanta erro (divida: hoje isso mata o cenario silencioso)
try:
    parse_fit_score(mock_llm_broken([]))
    expect(False, "JSON quebrado deveria levantar erro")
except (json.JSONDecodeError, ValueError):
    expect(True, "JSON quebrado levanta erro (precisa de tratamento)")

print()
print(f"RESULTADO: {passed} passou(aram), {failed} falhou(aram).")
sys.exit(1 if failed else 0)
