import argparse, json, os, psycopg2
from datetime import datetime, timezone

def ts_literal(x):
    # Accept ISO8601 or epoch seconds (int/float)
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x, tz=timezone.utc).isoformat()
    # Assume ISO8601; ensure 'Z'
    return datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(timezone.utc).isoformat()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--session', required=True)
    ap.add_argument('--export', required=True)  # LS JSON export path
    ap.add_argument('--author', default=os.environ.get('EEG_AUTHOR','konrad'))
    ap.add_argument('--db', default=os.environ.get('DATABASE_URL'))
    args = ap.parse_args()

    payload = json.load(open(args.export,'r',encoding='utf-8'))
    rows = []
    for task in payload:
        for ann in task.get('annotations', []):
            for r in ann.get('result', []):
                if r.get('type') != 'timeserieslabels':
                    continue
                start = ts_literal(r['value']['start'])
                end   = ts_literal(r['value']['end'])
                for label in r['value'].get('labels', []):
                    rows.append((args.session, f'[{start},{end})', label, args.author, None))

    conn = psycopg2.connect(args.db)
    with conn, conn.cursor() as cur:
        cur.executemany("""
          INSERT INTO annotation(session_id, span, label, author, notes)
          VALUES (%s, %s::tsrange, %s, %s, %s)
        """, rows)
    conn.close()
    print(f"Imported {len(rows)} annotations into session {args.session}")

if __name__ == "__main__":
    main()