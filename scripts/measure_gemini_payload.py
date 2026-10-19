"""Deterministic synthetic A/B size measurement; no real Gemini or billing data."""
import argparse
import json
import math
from pathlib import Path

from gemini_payload import build_payload, compact


def fixtures():
    """Already-sanitized inputs; key facts occur early in each description."""
    facts = 'Empresa Sintética: software B2B; 250 funcionários; AWS e HubSpot; expansão comercial. '
    def result(index, long=False):
        return {'title': f'Empresa Sintética — fonte {index}',
                'url': f'https://source-{index}.example.test/company',
                'description': facts + ('Contexto adicional sintético sem novos fatos. ' * 50 if long else ''),
                'extra_snippets': [facts, 'Contato: [EMAIL]. Tecnologia: AWS.',
                                   'Trecho adicional descartado neste experimento.'],
                'thumbnail': {'src': 'https://images.example.test/' + 'x' * 600},
                'profile': {'name': 'Fonte sintética', 'img': 'x' * 300},
                'language': 'pt', 'family_friendly': True}
    return {
        'metadata_heavy': {'query': {'original': 'Empresa Sintética', 'spellcheck_off': False},
                           'web': {'results': [result(i) for i in range(5)]},
                           'mixed': {'main': ['metadata'] * 30}},
        'long_descriptions': {'web': {'results': [result(i, True) for i in range(5)]}},
        'minimal': {'web': {'results': [{'title': 'Empresa Sintética', 'description': facts}]}},
        'empty': {'web': {'results': []}},
    }


def mock_response(prompt):
    """Input-sensitive contract smoke check, NOT a Gemini quality evaluation."""
    complete = all(term in prompt for term in ('software B2B', '250 funcionários', 'AWS', 'expansão comercial'))
    return {'industry': 'Software B2B' if complete else None,
            'size_employees': '250' if complete else None,
            'tech_stack': ['AWS', 'HubSpot'] if complete else [],
            'buying_signals': ['expansão comercial'] if complete else [],
            'icp_match_score': 82 if complete else None,
            'talking_points': ['expansão comercial'] if complete else []}


def structurally_valid(response):
    # Same six business fields; deliberately no assertion about factual accuracy.
    return (set(response) == {'industry', 'size_employees', 'tech_stack', 'buying_signals',
                             'icp_match_score', 'talking_points'}
            and all(response[k] is None or isinstance(response[k], str) for k in ('industry', 'size_employees'))
            and all(isinstance(response[k], list) for k in ('tech_stack', 'buying_signals', 'talking_points'))
            and (response['icp_match_score'] is None or
                 (type(response['icp_match_score']) is int and 0 <= response['icp_match_score'] <= 100)))


def size(payload):
    text = payload['textPrompt']
    return {'prompt_characters_measured': len(text),
            'prompt_utf8_bytes_measured': len(text.encode('utf-8')),
            'mapper_json_utf8_bytes_measured': len(compact(payload).encode('utf-8')),
            'input_tokens_estimated_chars_div_4': math.ceil(len(text) / 4)}


def measure():
    cases = []
    for name, data in fixtures().items():
        sanitized = compact(data)
        before = build_payload(sanitized, optimized=False)
        after = build_payload(sanitized)
        left, right = size(before), size(after)
        response_before = mock_response(before['textPrompt'])
        response_after = mock_response(after['textPrompt'])
        cases.append({'case': name, 'before': left, 'after': right,
                      'prompt_character_reduction_percent': round(100 * (1 - right['prompt_characters_measured'] / left['prompt_characters_measured']), 2),
                      'mock_structural_valid_before': structurally_valid(response_before),
                      'mock_structural_valid_after': structurally_valid(response_after),
                      'mock_response_equal': response_before == response_after})
    before_chars = sum(c['before']['prompt_characters_measured'] for c in cases)
    after_chars = sum(c['after']['prompt_characters_measured'] for c in cases)
    return {'synthetic': True, 'method': 'Same sanitized fixture and current blueprint instructions in each A/B pair.',
            'token_method': 'ceil(prompt Unicode characters / 4); heuristic, not Gemini tokenizer.',
            'cost_usd': None, 'cost_note': 'No verified tariff or billed token count. For input tariff R USD/million: estimated tokens * R / 1e6. Excludes output, reasoning, cache and other services.',
            'latency_ms': None, 'latency_note': 'No API calls; local string processing does not estimate Gemini latency.',
            'quality_note': 'Input-sensitive mock only. No measured Gemini response quality or semantic non-regression claim.',
            'cases': cases, 'total_prompt_characters_before': before_chars,
            'total_prompt_characters_after': after_chars,
            'total_prompt_character_reduction_percent': round(100 * (1 - after_chars / before_chars), 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = json.dumps(measure(), ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()
