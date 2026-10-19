"""Focused dashboard checks; no external services or persistent fixtures."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from observability_dashboard import render, timestamp
from local_observability import run_enrichment, synthetic_operations

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


class DashboardTests(unittest.TestCase):
    def test_empty_data_has_five_insufficient_states(self):
        html = render([], [], NOW)
        self.assertEqual(html.count('<strong class="insufficient_data">'), 5)
        self.assertIn('Nenhum evento P2', html)

    def test_synthetic_values_reuse_thresholds_and_volume_evidence(self):
        records = []
        for _ in range(20):
            record = run_enrichment(synthetic_operations(), cost_usd=.02, cost_source='synthetic')
            record['end'] = NOW.isoformat()
            records.append(record)
        html = render(records, [], NOW, pending=True, active=True, allow_synthetic=True)
        self.assertEqual(html.count('<strong class="ok">'), 5)
        self.assertIn('DADOS SINTÉTICOS', html)
        html = render(records, [], NOW)
        self.assertEqual(html.count('<strong class="insufficient_data">'), 2)

    def test_p2_filtered_ordered_limited_and_escaped(self):
        def event(day, priority='P2'):
            return dict(at=f'2026-10-{day:02}T12:00:00+00:00', priority=priority,
                        event='opened', alert_id=f'id-{day}', condition='<script>alert(1)</script>')
        html = render([], [event(10), event(12), event(14), event(11), event(13, 'P1')], NOW, limit=2)
        self.assertIn('id-12', html)
        self.assertIn('id-11', html)
        self.assertNotIn('id-10', html)
        self.assertNotIn('id-14', html)
        self.assertNotIn('id-13', html)
        self.assertLess(html.index('id-12'), html.index('id-11'))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_reference_requires_timezone(self):
        with self.assertRaises(ValueError):
            timestamp('2026-10-13T12:00:00')


if __name__ == '__main__':
    unittest.main()
