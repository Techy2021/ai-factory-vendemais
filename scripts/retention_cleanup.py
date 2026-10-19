"""Retention policy enforcement for Airtable. Dry-run unless --apply is supplied."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib import error, parse, request


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def action_for(record, now, raw_field, date_field):
    """Never infer age from missing/invalid timestamps."""
    fields = record.get('fields', {})
    enriched = timestamp(fields.get(date_field))
    if enriched is None or enriched > now:
        return None
    created = timestamp(record.get('createdTime'))
    if (created is not None and created <= now
            and max(created, enriched) <= now - timedelta(days=180)):
        return 'delete_record'
    if enriched <= now - timedelta(days=30) and fields.get(raw_field) not in (None, ''):
        return 'clear_raw'
    return None


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Airtable:
    def __init__(self, token, base, table):
        if not token or not re.fullmatch(r'app[A-Za-z0-9]+', base) or not re.fullmatch(r'tbl[A-Za-z0-9]+', table):
            raise ValueError('Missing token or invalid Airtable base/table ID.')
        self.url = f'https://api.airtable.com/v0/{base}/{table}'
        self.token = token
        self.client = request.build_opener(NoRedirect)

    def call(self, method, suffix='', query=None, payload=None):
        url = self.url + suffix
        if query:
            url += '?' + parse.urlencode(query, doseq=True)
        body = None if payload is None else json.dumps(payload).encode('utf-8')
        req = request.Request(url, data=body, method=method, headers={
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
        })
        time.sleep(0.25)  # Remain below five requests/second for this process.
        try:
            with self.client.open(req, timeout=30) as response:
                return json.load(response)
        except error.HTTPError as exc:
            # Never print provider bodies/URLs: they can contain data or credentials.
            raise RuntimeError(f'Airtable {method} failed (HTTP {exc.code}); no automatic retry.') from None
        except (error.URLError, TimeoutError, OSError, ValueError):
            raise RuntimeError(f'Airtable {method} failed; inspect state before rerunning.') from None

    def records(self, raw_field, date_field):
        # Snapshot all pages before writing, so deletion cannot shift pagination.
        records, seen = [], set()
        query = {'pageSize': 100, 'returnFieldsByFieldId': 'true',
                 'fields[]': [raw_field, date_field]}
        while True:
            page = self.call('GET', query=query)
            records.extend(page['records'])
            offset = page.get('offset')
            if not offset:
                return records
            if offset in seen:
                raise RuntimeError('Repeated pagination offset; nothing applied.')
            seen.add(offset)
            query['offset'] = offset

    def get(self, record_id):
        return self.call('GET', '/' + parse.quote(record_id, safe=''),
                         query={'returnFieldsByFieldId': 'true'})

    def clear(self, record_id, raw_field):
        return self.call('PATCH', '/' + parse.quote(record_id, safe=''),
                         payload={'fields': {raw_field: None}})

    def delete(self, record_id):
        return self.call('DELETE', '/' + parse.quote(record_id, safe=''))


def cleanup(client, now, raw_field, date_field, apply=False):
    results = {'clear_raw': 0, 'delete_record': 0, 'skipped': 0}
    for record in client.records(raw_field, date_field):
        action = action_for(record, now, raw_field, date_field)
        if action and apply:
            # Recheck current state: a refresh after listing must not be deleted.
            current = client.get(record['id'])
            action = action_for(current, now, raw_field, date_field)
            if action == 'clear_raw':
                client.clear(record['id'], raw_field)
            elif action == 'delete_record':
                client.delete(record['id'])
        results[action or 'skipped'] += 1
    return results


def current_fields():
    blueprint = Path(__file__).resolve().parents[1] / 'workflows/vendemais-make-blueprint.json'
    flow = json.loads(blueprint.read_text(encoding='utf-8'))['flow']
    record = next(m for m in flow if m['id'] == 19)['mapper']['record']
    raw = next(key for key, value in record.items() if value == '{{8.data.web}}')
    date = next(key for key, value in record.items() if value == '{{now}}')
    return raw, date


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-id', required=True)
    parser.add_argument('--table-id', required=True)
    parser.add_argument('--apply', action='store_true', help='Perform irreversible changes instead of dry-run.')
    args = parser.parse_args()
    try:
        raw, date = current_fields()
        client = Airtable(os.environ.get('AIRTABLE_RETENTION_PAT', ''), args.base_id, args.table_id)
        results = cleanup(client, datetime.now(timezone.utc), raw, date, args.apply)
        print(('APPLIED' if args.apply else 'DRY-RUN') + ': ' + json.dumps(results))
        return 0
    except (RuntimeError, ValueError, KeyError, StopIteration, OSError):
        print('Retention failed; execution may be partial. Check access/schema and remote state before rerunning.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
