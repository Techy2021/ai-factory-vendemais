"""Focused Stage 2.4 tests; synthetic inputs, no network or broad suite."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gemini_payload import (ROOT, PLACEHOLDER, LIMITS, optimize, build_payload, compact)
from measure_gemini_payload import fixtures, measure, mock_response, structurally_valid


class PayloadTests(unittest.TestCase):
    def test_selects_fields_preserves_order_and_does_not_mutate(self):
        data = fixtures()['metadata_heavy']
        original = deepcopy(data)
        selected = json.loads(optimize(compact(data)))
        self.assertEqual(data, original)
        self.assertEqual(list(selected), ['web'])
        self.assertEqual(len(selected['web']['results']), 5)
        for old, new in zip(data['web']['results'], selected['web']['results']):
            self.assertEqual(set(new), {'title', 'url', 'description', 'extra_snippets'})
            self.assertEqual(new['title'], old['title'])
            self.assertEqual(new['url'], old['url'])
            self.assertEqual(new['description'], old['description'])
            self.assertEqual(new['extra_snippets'], old['extra_snippets'][:2])

    def test_field_limits_unicode_and_valid_json(self):
        result = {field: '😀"\\\n' * 1000 for field in LIMITS}
        result['extra_snippets'] = ['á' * 1000] * 4
        selected = json.loads(optimize(compact({'web': {'results': [result]}})))['web']['results'][0]
        for field, limit in LIMITS.items():
            self.assertEqual(selected[field], result[field][:limit])
        self.assertEqual(selected['extra_snippets'], ['á' * 300] * 2)

    def test_empty_inputs_do_not_grow_or_invent_evidence(self):
        for data in (None, {}, {'web': None}, {'web': {}}, {'web': {'results': None}}, {'web': {'results': []}}):
            source = compact(data)
            self.assertEqual(optimize(source), source)

    def test_unexpected_input_fails_instead_of_silently_dropping(self):
        for source in ('not json', '[]', '{"web":[]}', '{"web":{"results":{}}}',
                       '{"web":{"results":[null]}}', '{"web":{"results":[{"title":42}]}}',
                       '{"web":{"results":[{"extra_snippets":[false]}]}}'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                optimize(source)

    def test_model_and_instructions_unchanged_only_content_replaced(self):
        blueprint = json.loads((ROOT / 'workflows/vendemais-make-blueprint.json').read_text(encoding='utf-8'))
        mapper = next(m['mapper'] for m in blueprint['flow'] if m['id'] == 18)
        sanitized = compact(fixtures()['long_descriptions'])
        for optimized in (False, True):
            payload = build_payload(sanitized, optimized=optimized)
            self.assertEqual(payload['model'], mapper['model'])
            content = optimize(sanitized) if optimized else sanitized
            self.assertEqual(payload['textPrompt'], mapper['textPrompt'].replace(PLACEHOLDER, content))
        self.assertIn('[EMAIL]', build_payload(sanitized)['textPrompt'])

    def test_reproducible_measurement_and_mock_contract(self):
        report = measure()
        self.assertEqual(report, measure())
        self.assertIsNone(report['cost_usd'])
        self.assertIsNone(report['latency_ms'])
        for case in report['cases']:
            self.assertTrue(case['mock_structural_valid_before'])
            self.assertTrue(case['mock_structural_valid_after'])
            self.assertTrue(case['mock_response_equal'])
            self.assertGreaterEqual(case['prompt_character_reduction_percent'], 0)
        self.assertGreater(report['total_prompt_character_reduction_percent'], 0)
        self.assertFalse(structurally_valid({'icp_match_score': 200}))

    def test_late_fact_can_be_lost_despite_valid_mock_contract(self):
        # Explicitly expose the semantic limitation of prefix truncation.
        data = {'web': {'results': [{'description': 'x' * 900 +
                ' software B2B; 250 funcionários; AWS; expansão comercial'}]}}
        source = compact(data)
        before = mock_response(build_payload(source, optimized=False)['textPrompt'])
        after = mock_response(build_payload(source)['textPrompt'])
        self.assertNotEqual(before, after)
        self.assertTrue(structurally_valid(after))


if __name__ == '__main__':
    unittest.main()
