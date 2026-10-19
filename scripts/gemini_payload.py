"""Prepare a Gemini prompt from already-sanitized Brave JSON. No API calls."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = '{{29.sanitized_search}}'
# Keep every result, in the original order. Limits are Unicode code points.
LIMITS = {'title': 200, 'url': 500, 'description': 800}
EXTRA_SNIPPET_LIMIT = 300
EXTRA_SNIPPET_COUNT = 2


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def optimize(sanitized):
    """Select useful fields after sanitization; never reconstruct raw search data.

    Missing/null results mean no evidence; unexpected schema fails explicitly.
    Do not cut the serialized JSON: truncate strings before serialization.
    """
    data = json.loads(sanitized)
    if data is None:
        return 'null'
    if not isinstance(data, dict):
        raise ValueError('Expected sanitized Brave object')
    web = data.get('web')
    if web is None:
        web = {}
    if not isinstance(web, dict):
        raise ValueError('Expected web object')
    results = web.get('results')
    if results is None:
        return compact(data)
    if not isinstance(results, list):
        raise ValueError('Expected results array')
    selected = []
    for result in results:
        if not isinstance(result, dict):
            raise ValueError('Expected result object')
        item = {}
        for field, limit in LIMITS.items():
            value = result.get(field)
            if value is not None:
                if not isinstance(value, str):
                    raise ValueError('Expected text field')
                item[field] = value[:limit]
        extras = result.get('extra_snippets')
        if extras is not None:
            if not isinstance(extras, list) or any(not isinstance(v, str) for v in extras):
                raise ValueError('Expected snippet array')
            item['extra_snippets'] = [v[:EXTRA_SNIPPET_LIMIT] for v in extras[:EXTRA_SNIPPET_COUNT]]
        selected.append(item)
    candidate = compact({'web': {'results': selected}})
    # Sparse/empty input should never grow merely due to a new wrapper.
    original = compact(data)
    return candidate if len(candidate.encode('utf-8')) < len(original.encode('utf-8')) else original


def build_payload(sanitized, *, optimized=True, blueprint=None):
    """Return the actual model/textPrompt mapper shape, with its placeholder resolved."""
    if blueprint is None:
        blueprint = json.loads((ROOT / 'workflows/vendemais-make-blueprint.json').read_text(encoding='utf-8'))
    module = next(m for m in blueprint['flow'] if m['id'] == 18)
    mapper = module['mapper']
    template = mapper['textPrompt']
    if template.count(PLACEHOLDER) != 1:
        raise ValueError('Unexpected Gemini prompt mapping')
    # Validate input in both paths, but preserve baseline bytes/spacing in its text.
    content = optimize(sanitized)
    return {'model': mapper['model'],
            'textPrompt': template.replace(PLACEHOLDER, content if optimized else sanitized)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='JSON already sanitized upstream')
    parser.add_argument('--output', type=Path, required=True, help='Candidate mapper JSON, not sent')
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError('Input and output must differ')
        payload = build_payload(args.input.read_text(encoding='utf-8'))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(compact(payload) + '\n', encoding='utf-8')
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        print('Payload not generated: check sanitized input, output and blueprint. No request sent.')
        return 1
    print(f'Local candidate written: {args.output}. No request sent.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
