import json
from pathlib import Path
import requests

api = 'http://127.0.0.1:8000'
rows = []

try:
    h = requests.get(f'{api}/health', timeout=10)
    health_ok = h.status_code == 200
    health_status = h.status_code
except Exception as exc:
    health_ok = False
    health_status = f'error: {exc}'

for i in range(1, 11):
    site_id = f'LF_REAL_{i:03d}'
    row = {
        'site_id': site_id,
        'http_status': None,
        'scan_id': None,
        'incident_id': None,
        'inference_mode': None,
        'evidence_http': None,
        'result': 'fail'
    }
    if not health_ok:
        row['http_status'] = health_status
        row['result'] = 'fail_health'
        rows.append(row)
        continue

    try:
        r = requests.post(f'{api}/sites/{site_id}/scan', json={'force_refresh': True}, timeout=45)
        row['http_status'] = r.status_code
        if not r.ok:
            row['result'] = 'fail_scan_http'
            try:
                row['error'] = r.json()
            except Exception:
                row['error'] = r.text
            rows.append(row)
            continue

        data = r.json() if r.content else {}
        row['scan_id'] = data.get('scan_id')
        row['incident_id'] = data.get('incident_id')

        if row['scan_id']:
            ev = requests.get(f"{api}/scans/{row['scan_id']}/evidence", timeout=20)
            row['evidence_http'] = ev.status_code
            if ev.ok:
                evj = ev.json() if ev.content else {}
                md = evj.get('metadata') if isinstance(evj, dict) else None
                inf = md.get('inference') if isinstance(md, dict) else None
                row['inference_mode'] = inf.get('mode') if isinstance(inf, dict) else None
        row['result'] = 'success'
    except Exception as exc:
        row['result'] = 'fail_exception'
        row['error'] = str(exc)
    rows.append(row)

success_count = sum(1 for r in rows if r['result'] == 'success')
fail_count = len(rows) - success_count
report = {
    'api_health_status': health_status,
    'success_count': success_count,
    'fail_count': fail_count,
    'rows': rows,
}

out = Path('data/processed/live_scan_summary.json')
out.write_text(json.dumps(report, indent=2), encoding='utf-8')

print(f'API_HEALTH_STATUS {health_status}')
print(f'SUCCESS_COUNT {success_count}')
print(f'FAIL_COUNT {fail_count}')
print('TABLE_START')
for r in rows:
    print(f"| {r.get('site_id','')} | {r.get('http_status','')} | {r.get('scan_id','')} | {r.get('incident_id','')} | {r.get('inference_mode','')} | {r.get('evidence_http','')} | {r.get('result','')} |")
print('TABLE_END')
print(f'REPORT_PATH {out.as_posix()}')
