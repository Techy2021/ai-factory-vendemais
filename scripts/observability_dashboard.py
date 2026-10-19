"""Read-only local HTML snapshot. Standard library only; no network calls."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

from local_observability import aggregate
from threshold_alerts import evaluate

LABELS = {
    'enrichment_latency_p95_seconds': ('Latência p95', 's'),
    'enrichment_error_rate_percent': ('Taxa de erro', '%'),
    'enrichment_mean_cost_usd': ('Custo médio', 'USD'),
    'enrichment_success_count': ('Volume de sucessos', ''),
    'enrichment_valid_output_rate_percent': ('Qualidade estrutural', '%'),
}


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timestamp precisa incluir fuso horário')
    return result.astimezone(timezone.utc)


def read_jsonl(path, warnings):
    if not path.exists():
        warnings.append(f'Arquivo ausente: {path}. Dados indisponíveis.')
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict) or row.get('environment') != 'local':
                raise ValueError(f'{path}, linha {number}: esperado registro local')
            rows.append(row)
    return rows


def render(telemetry, alerts, now, *, warnings=(), limit=20, **options):
    metrics = aggregate(telemetry, now)
    evaluation = evaluate(metrics, daily_cost_due=now.hour == 12 and now.minute < 5,
                          **options)
    def safe(value):
        return escape(str(value))
    cards = []
    for name, (label, unit) in LABELS.items():
        item = evaluation[name]
        value = '—' if item['value'] is None else f"{item['value']:.4g} {unit}"
        cards.append(f'<article><h2>{label}</h2><p class="value">{value}</p>'
                     f'<strong class="{item["state"]}">{item["state"]}</strong>'
                     f'<p>Amostras: {item["samples"]} · Janela: {item["window_hours"]}h</p>'
                     f'<p>Alerta se {safe(item["operator"])} {item["threshold"]} {unit}</p>'
                     f'<p>Motivo: {safe(item["reason"] or "avaliação válida")}</p></article>')
    recent = sorted((event for event in alerts if event.get('priority') == 'P2'
                     and timestamp(event['at']) <= now),
                    key=lambda event: timestamp(event['at']), reverse=True)[:limit]
    rows = []
    for event in recent:
        cells = [event.get(key, '—') for key in
                 ('at', 'event', 'alert_id', 'value', 'samples', 'condition', 'delivery_channel')]
        rows.append('<tr>' + ''.join(f'<td>{safe(cell)}</td>' for cell in cells) + '</tr>')
    synthetic = any(record.get('cost_source') == 'synthetic' for record in telemetry)
    provenance = ('DADOS SINTÉTICOS presentes: há traces com cost_source=synthetic. '
                  'Não comprovam operação ou custo de produção.' if synthetic else
                  'Origem real/sintética não comprovada: o schema não identifica a origem completa dos traces.')
    notice = ''.join(f'<p class="notice">{safe(warning)}</p>' for warning in warnings)
    return f'''<!doctype html>
<html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VendeMais · Observabilidade local</title>
<style>
body{{font:16px system-ui,sans-serif;margin:2rem auto;padding:0 1rem;max-width:1200px;background:#f5f7fa;color:#17243b}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}}
article,.notice{{background:white;padding:1rem;border:1px solid #ccd3df;border-radius:8px}}
h2{{font-size:1.15rem}}.value{{font-size:2rem;margin:.5rem 0}}
.ok{{color:#146331}}.alert{{color:#ac1622}}.insufficient_data{{color:#775000}}
.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:white}}
th,td{{padding:.6rem;text-align:left;border:1px solid #ccd3df}}td{{overflow-wrap:anywhere}}
</style>
<h1>VendeMais · Observabilidade local</h1>
<p>Snapshot de referência: {safe(now.isoformat())} (UTC). Atualize executando o gerador novamente.</p>
<p class="notice">{provenance} Eventos P2 não possuem marcador de origem; sua origem não pode ser confirmada pelo arquivo.</p>
{notice}<section class="cards">{''.join(cards)}</section>
<p>Estados recalculados com as regras existentes. insufficient_data não significa recuperação.
Qualidade mede apenas o contrato estrutural. Um estado alert não abre automaticamente um P2 neste painel.</p>
<h2>Eventos P2 recentes · últimos {limit} até a referência</h2>
<p>Histórico de entrega local: opened (abertura), reminder (lembrete), resolved (recuperação).
Não representa envio ao Slack nem confirma o estado atual de um incidente.</p>
<div class="scroll"><table><thead><tr><th>Horário</th><th>Evento</th><th>ID</th><th>Erro (%)</th>
<th>Amostras</th><th>Condição</th><th>Entrega</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
{'<p>Nenhum evento P2 disponível até a referência.</p>' if not rows else ''}
</html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--telemetry', type=Path, default=Path('logs/observability.jsonl'))
    parser.add_argument('--alerts', type=Path, default=Path('logs/thresholds/alerts.jsonl'))
    parser.add_argument('--output', type=Path, default=Path('logs/dashboard.html'))
    parser.add_argument('--at', type=timestamp, help='Referência ISO 8601 com fuso; padrão: agora UTC')
    parser.add_argument('--pending', action='store_true', default=None)
    parser.add_argument('--active', action='store_true', default=None)
    parser.add_argument('--telemetry-complete', action='store_true')
    parser.add_argument('--synthetic', action='store_true', help='Permitir custo sintético na avaliação')
    args = parser.parse_args()
    try:
        # Never overwrite the source logs or threshold lifecycle files.
        if args.output.suffix.lower() != '.html':
            raise ValueError('Saída deve ter extensão .html')
        if args.output.resolve() in (args.telemetry.resolve(), args.alerts.resolve()):
            raise ValueError('Saída não pode substituir uma fonte')
        warnings = []
        telemetry = read_jsonl(args.telemetry, warnings)
        alerts = read_jsonl(args.alerts, warnings)
        html = render(telemetry, alerts, args.at or datetime.now(timezone.utc),
                      warnings=warnings, pending=args.pending, active=args.active,
                      telemetry_complete=args.telemetry_complete, allow_synthetic=args.synthetic)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding='utf-8')
        print(f'Dashboard: {args.output.resolve()}')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Dashboard não gerado: verifique formato, fusos e permissões das fontes ({type(exc).__name__}).')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
