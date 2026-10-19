"""Synthetic threshold/lifecycle tests, no external services."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import local_observability as obs
import threshold_alerts as alerts

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def metrics():
    values = [60, 5, .03, 1, 95]
    return {name: {'value': value, 'samples': 20, 'window_hours': 1 if index in (0, 1, 3) else 24,
                   'source': 'reconciled'} for index, (name, value) in enumerate(zip(alerts.RULES, values))}


def error_evaluation(value=10, samples=20):
    data = metrics()
    data[alerts.ERROR].update(value=value, samples=samples)
    return alerts.evaluate(data, pending=True, active=True)


class ThresholdTests(unittest.TestCase):
    def test_exact_thresholds_ok(self):
        result = alerts.evaluate(metrics(), pending=True, active=True)
        self.assertEqual(len(result), 5)
        self.assertTrue(all(item['state'] == 'ok' for item in result.values()))

    def test_all_thresholds_violated(self):
        data = metrics()
        for name, value in zip(alerts.RULES, [61, 6, .031, 0, 94]):
            data[name]['value'] = value
        result = alerts.evaluate(data, pending=True, active=True)
        self.assertTrue(all(item['state'] == 'alert' for item in result.values()))

    def test_minimum_sample_and_missing(self):
        data = metrics()
        for item in data.values():
            item['samples'] = 19
        result = alerts.evaluate(data)
        self.assertTrue(all(item['state'] == 'insufficient_data' for item in result.values()))
        self.assertTrue(all(item['state'] == 'insufficient_data' for item in alerts.evaluate({}).values()))

    def test_volume_requires_demand_and_complete_empty_window(self):
        data = metrics()
        data['enrichment_success_count'].update(value=None, samples=0)
        self.assertEqual(alerts.evaluate(data, pending=True, active=True)['enrichment_success_count']['state'], 'insufficient_data')
        self.assertEqual(alerts.evaluate(data, pending=True, active=True, telemetry_complete=True)['enrichment_success_count']['state'], 'alert')
        self.assertEqual(alerts.evaluate(data, pending=False, active=True, telemetry_complete=True)['enrichment_success_count']['state'], 'insufficient_data')

    def test_cost_due_and_source(self):
        data = metrics()
        name = 'enrichment_mean_cost_usd'
        self.assertEqual(alerts.evaluate(data, daily_cost_due=False)[name]['state'], 'insufficient_data')
        data[name]['source'] = 'synthetic'
        self.assertEqual(alerts.evaluate(data)[name]['state'], 'insufficient_data')
        self.assertEqual(alerts.evaluate(data, allow_synthetic=True)[name]['state'], 'ok')

    def test_p2_two_consecutive_no_premature_or_duplicate(self):
        state, events = alerts.advance_p2(error_evaluation(), {}, NOW)
        self.assertEqual(events, [])
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(seconds=10))
        self.assertEqual(events, [])
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=5), ['a'*32, 'synthetic-user@example.test'])
        self.assertEqual(events[0]['event'], 'opened')
        self.assertEqual(events[0]['priority'], 'P2')
        self.assertEqual(events[0]['related_trace_ids'], ['a'*32])
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=10))
        self.assertEqual(events, [])

    def test_gap_and_insufficient_break_streak(self):
        state, _ = alerts.advance_p2(error_evaluation(), {}, NOW)
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=10))
        self.assertEqual(events, [])
        state, _ = alerts.advance_p2(error_evaluation(samples=19), state, NOW + timedelta(minutes=15))
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=20))
        self.assertEqual(events, [])

    def test_recovery_needs_two_valid_evaluations(self):
        state, _ = alerts.advance_p2(error_evaluation(), {}, NOW)
        state, _ = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=5))
        state, events = alerts.advance_p2(error_evaluation(5), state, NOW + timedelta(minutes=10))
        self.assertEqual(events, [])
        state, events = alerts.advance_p2(error_evaluation(samples=19), state, NOW + timedelta(minutes=15))
        self.assertTrue(state['open'])
        state, _ = alerts.advance_p2(error_evaluation(5), state, NOW + timedelta(minutes=20))
        state, events = alerts.advance_p2(error_evaluation(5), state, NOW + timedelta(minutes=25))
        self.assertEqual(events[0]['event'], 'resolved')
        self.assertFalse(state['open'])

    def test_reminder_after_sixty_minutes_and_reopen(self):
        state, _ = alerts.advance_p2(error_evaluation(), {}, NOW)
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=5))
        first_id = events[0]['alert_id']
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=65))
        self.assertEqual(events[0]['event'], 'reminder')
        self.assertEqual(events[0]['alert_id'], first_id)
        state, _ = alerts.advance_p2(error_evaluation(0), state, NOW + timedelta(minutes=70))
        state, _ = alerts.advance_p2(error_evaluation(0), state, NOW + timedelta(minutes=75))
        state, _ = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=80))
        state, events = alerts.advance_p2(error_evaluation(), state, NOW + timedelta(minutes=85))
        self.assertNotEqual(events[0]['alert_id'], first_id)

    def test_persistent_local_delivery_end_to_end(self):
        records = []
        for index in range(20):
            operations = obs.synthetic_operations()
            if index < 2:
                operations['gemini.generate'] = lambda _: '{synthetic-invalid'
            record = obs.run_enrichment(operations, cost_usd=.02, cost_source='synthetic')
            record['end'] = NOW.isoformat()
            records.append(record)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            telemetry = root / 'telemetry.jsonl'
            for record in records:
                obs.append_jsonl(record, telemetry)
            def run(at):
                return alerts.run_once(telemetry, root/'state.json', root/'evaluations.jsonl', root/'alerts.jsonl', at, allow_synthetic=True)
            _, events = run(NOW)
            self.assertEqual(events, [])
            result, events = run(NOW + timedelta(minutes=5))
            self.assertEqual(result[alerts.ERROR]['value'], 10)
            self.assertEqual(events[0]['event'], 'opened')
            delivered = json.loads((root/'alerts.jsonl').read_text(encoding='utf-8'))
            self.assertEqual(delivered['delivery_channel'], 'local_jsonl')
            self.assertEqual(delivered['intended_channel'], 'Slack #vendemais-operacao')
            self.assertEqual(len(delivered['related_trace_ids']), 2)


if __name__ == '__main__':
    unittest.main()
