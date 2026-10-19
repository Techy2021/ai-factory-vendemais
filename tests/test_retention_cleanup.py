"""Targeted synthetic retention tests: no network, no real records."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('retention', ROOT / 'scripts/retention_cleanup.py')
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)
NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
RAW, DATE = retention.current_fields()


def record(days, created_days=None):
    date = (NOW - timedelta(days=days)).isoformat()
    return {'id': 'recSynthetic', 'createdTime': (NOW - timedelta(days=created_days if created_days is not None else days)).isoformat(),
            'fields': {RAW: 'Synthetic search: Acme Test', DATE: date, 'score': 82}}


class FakeAirtable:
    def __init__(self, records):
        self.state = deepcopy(records)
        self.writes = []
        self.refreshed = None

    def records(self, *args):
        return deepcopy(self.state)

    def get(self, record_id):
        return deepcopy(self.refreshed or next(r for r in self.state if r['id'] == record_id))

    def clear(self, record_id, raw):
        next(r for r in self.state if r['id'] == record_id)['fields'][raw] = None
        self.writes.append(('clear', record_id))

    def delete(self, record_id):
        self.state = [r for r in self.state if r['id'] != record_id]
        self.writes.append(('delete', record_id))


class RetentionTests(unittest.TestCase):
    def action(self, value):
        return retention.action_for(value, NOW, RAW, DATE)

    def test_raw_boundary(self):
        self.assertIsNone(self.action(record(29.999)))
        self.assertEqual(self.action(record(30)), 'clear_raw')

    def test_record_boundary(self):
        self.assertEqual(self.action(record(179.999)), 'clear_raw')
        self.assertEqual(self.action(record(180)), 'delete_record')

    def test_recent_created_or_enriched_protected(self):
        self.assertEqual(self.action(record(200, 5)), 'clear_raw')
        self.assertIsNone(self.action(record(5, 200)))

    def test_unknown_invalid_naive_future_dates(self):
        for value in [None, '', 'bad', '2020-01-01T00:00:00', (NOW + timedelta(days=1)).isoformat()]:
            item = record(200)
            item['fields'][DATE] = value
            self.assertIsNone(self.action(item))
        item = record(200)
        item.pop('createdTime')
        self.assertEqual(self.action(item), 'clear_raw')

    def test_empty_raw_preserved(self):
        item = record(40)
        item['fields'].pop(RAW)
        self.assertIsNone(self.action(item))

    def test_timezone(self):
        item = record(30)
        item['fields'][DATE] = (NOW - timedelta(days=30)).astimezone(timezone(timedelta(hours=-3))).isoformat()
        self.assertEqual(self.action(item), 'clear_raw')

    def test_dry_run_never_writes(self):
        fake = FakeAirtable([record(40)])
        before = deepcopy(fake.state)
        retention.cleanup(fake, NOW, RAW, DATE)
        self.assertEqual(fake.state, before)
        self.assertEqual(fake.writes, [])

    def test_clear_only_raw_and_idempotency(self):
        item = record(40)
        fake = FakeAirtable([item])
        retention.cleanup(fake, NOW, RAW, DATE, True)
        expected = deepcopy(item)
        expected['fields'][RAW] = None
        self.assertEqual(fake.state, [expected])
        retention.cleanup(fake, NOW, RAW, DATE, True)
        self.assertEqual(len(fake.writes), 1)

    def test_delete_only_expired_records(self):
        old, fresh = record(181), record(10)
        fresh['id'] = 'recFreshSynthetic'
        fake = FakeAirtable([old, fresh])
        retention.cleanup(fake, NOW, RAW, DATE, True)
        self.assertEqual(fake.state, [fresh])

    def test_refresh_between_list_and_write(self):
        fake = FakeAirtable([record(200)])
        fake.refreshed = record(1, 200)
        retention.cleanup(fake, NOW, RAW, DATE, True)
        self.assertEqual(fake.writes, [])

    def test_pagination_and_wire_actions(self):
        client = retention.Airtable('synthetic-token', 'appSynthetic', 'tblSynthetic')
        calls = []
        pages = iter([{'records': [record(40)], 'offset': 'synthetic-next'}, {'records': []}])
        def call(method, suffix='', query=None, payload=None):
            calls.append((method, suffix, deepcopy(query), payload))
            return next(pages) if method == 'GET' else {}
        client.call = call
        self.assertEqual(len(client.records(RAW, DATE)), 1)
        self.assertEqual(calls[1][2]['offset'], 'synthetic-next')
        client.clear('recSynthetic', RAW)
        self.assertEqual(calls[-1], ('PATCH', '/recSynthetic', None, {'fields': {RAW: None}}))
        client.delete('recSynthetic')
        self.assertEqual(calls[-1][0], 'DELETE')

    def test_n8n_pruning_configuration(self):
        compose = (ROOT / 'n8n-mirror/docker-compose.yml').read_text(encoding='utf-8')
        for setting in ['EXECUTIONS_DATA_PRUNE=true', 'EXECUTIONS_DATA_MAX_AGE=720', 'EXECUTIONS_DATA_PRUNE_MAX_COUNT=0']:
            self.assertIn(setting, compose)


if __name__ == '__main__':
    unittest.main()
