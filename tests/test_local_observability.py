"""Synthetic-only local observability tests. No API calls."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('obs', ROOT / 'scripts/local_observability.py')
obs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obs)
NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


class ObservabilityTests(unittest.TestCase):
    def run_trace(self, operations=None, **kwargs):
        ticks = iter(range(100))
        trace = obs.Trace(utc=lambda: NOW, monotonic=lambda: next(ticks))
        return obs.run_enrichment(operations or obs.synthetic_operations(), trace=trace, **kwargs)

    def test_trace_id_unique_random_uuid4(self):
        first, second = self.run_trace(), self.run_trace()
        self.assertNotEqual(first['trace_id'], second['trace_id'])
        self.assertEqual(uuid.UUID(hex=first['trace_id']).version, 4)

    def test_six_spans_and_parent_relationship(self):
        trace = self.run_trace()
        self.assertEqual([s['name'] for s in trace['spans']], list(obs.SPANS))
        self.assertEqual(len({s['span_id'] for s in trace['spans']}), 6)
        for span in trace['spans']:
            self.assertEqual(span['trace_id'], trace['trace_id'])
            self.assertEqual(span['parent_span_id'], trace['span_id'])

    def test_success_status_timestamps_and_duration(self):
        trace = self.run_trace()
        for item in [trace, *trace['spans']]:
            self.assertEqual(item['status'], 'success')
            self.assertIsNone(item['error'])
            self.assertEqual(datetime.fromisoformat(item['start']), NOW)
            self.assertEqual(datetime.fromisoformat(item['end']), NOW)
        self.assertEqual(trace['duration_seconds'], 13)
        self.assertTrue(all(s['duration_seconds'] == 1 for s in trace['spans']))

    def test_error_stops_unexecuted_spans_and_redacts_exception(self):
        operations = obs.synthetic_operations()
        def fail(_):
            raise RuntimeError('synthetic-secret-and-user@example.test')
        operations['brave.search'] = fail
        trace = self.run_trace(operations)
        self.assertEqual(trace['status'], 'error')
        self.assertEqual(len(trace['spans']), 2)
        self.assertEqual(trace['spans'][-1]['status'], 'error')
        self.assertEqual(trace['error'], 'operation_failed')
        self.assertGreater(trace['duration_seconds'], 0)
        self.assertNotIn('example.test', json.dumps(trace))
        self.assertIsNone(trace['quality_valid'])

    def test_invalid_json_and_missing_response_count_as_bad_quality(self):
        for output in ['{broken', None, {}, {'icp_match_score': 82}]:
            operations = obs.synthetic_operations()
            operations['gemini.generate'] = lambda _, value=output: value
            trace = self.run_trace(operations)
            self.assertFalse(trace['quality_valid'])
            self.assertEqual(trace['error'], 'invalid_output')
            self.assertEqual(len(trace['spans']), 4)

    def test_contract_nulls_valid_and_bool_score_invalid(self):
        data = {key: None for key in obs.FIELDS}
        self.assertEqual(obs.validate_output(data), data)
        data['icp_match_score'] = True
        with self.assertRaises(obs.InvalidOutput):
            obs.validate_output(data)

    def test_missing_write_confirmation_fails_but_keeps_quality(self):
        operations = obs.synthetic_operations()
        operations['airtable.write'] = lambda _: None
        trace = self.run_trace(operations)
        self.assertEqual(trace['status'], 'error')
        self.assertTrue(trace['quality_valid'])
        self.assertEqual(len(trace['spans']), 5)

    def test_five_aggregates(self):
        first = self.run_trace(cost_usd=.02, cost_source='synthetic')
        operations = obs.synthetic_operations()
        operations['gemini.generate'] = lambda _: '{broken'
        second = self.run_trace(operations, cost_usd=.04, cost_source='synthetic')
        metrics = obs.aggregate([first, second, deepcopy(first)], NOW)
        self.assertEqual(len(metrics), 5)
        self.assertEqual(metrics['enrichment_latency_p95_seconds']['value'], 13)
        self.assertEqual(metrics['enrichment_error_rate_percent']['value'], 50)
        self.assertAlmostEqual(metrics['enrichment_mean_cost_usd']['value'], .03)
        self.assertEqual(metrics['enrichment_success_count']['value'], 1)
        self.assertEqual(metrics['enrichment_valid_output_rate_percent']['value'], 50)

    def test_windows_and_missing_data(self):
        trace = self.run_trace()
        metrics = obs.aggregate([trace], NOW + timedelta(hours=2))
        self.assertIsNone(metrics['enrichment_latency_p95_seconds']['value'])
        self.assertEqual(metrics['enrichment_valid_output_rate_percent']['value'], 100)
        self.assertIsNone(metrics['enrichment_mean_cost_usd']['value'])
        self.assertTrue(all(m['value'] is None for m in obs.aggregate([], NOW).values()))
        self.assertTrue(all(m['value'] is None for m in obs.aggregate([trace], NOW + timedelta(days=2)).values()))

    def test_partial_cost_and_mixed_sources_not_zero(self):
        known = self.run_trace(cost_usd=0, cost_source='reconciled')
        unknown = self.run_trace()
        self.assertIsNone(obs.aggregate([known, unknown], NOW)['enrichment_mean_cost_usd']['value'])
        synthetic = self.run_trace(cost_usd=.02, cost_source='synthetic')
        self.assertIsNone(obs.aggregate([known, synthetic], NOW)['enrichment_mean_cost_usd']['value'])
        self.assertEqual(obs.aggregate([known], NOW)['enrichment_mean_cost_usd']['value'], 0)

    def test_jsonl_roundtrip_without_payload(self):
        operations = obs.synthetic_operations()
        operations['brave.search'] = lambda _: 'synthetic-user@example.test'
        trace = self.run_trace(operations)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'telemetry.jsonl'
            obs.append_jsonl(trace, path)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), trace)
            self.assertNotIn('example.test', path.read_text(encoding='utf-8'))

    def test_invalid_cost_and_trace_reuse(self):
        for cost in [-1, float('nan'), True]:
            with self.assertRaises(ValueError):
                self.run_trace(cost_usd=cost, cost_source='synthetic')
        trace = obs.Trace()
        obs.run_enrichment(obs.synthetic_operations(), trace=trace)
        with self.assertRaises(ValueError):
            obs.run_enrichment(obs.synthetic_operations(), trace=trace)


if __name__ == '__main__':
    unittest.main()
