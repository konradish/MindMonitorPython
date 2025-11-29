import argparse, json, os, uuid, hashlib, subprocess, psycopg2
from datetime import datetime, timezone

def git_head(): 
    try: 
        return subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    except: 
        return None

def dirty():
    try: 
        return bool(subprocess.check_output(['git','status','--porcelain'], text=True).strip())
    except: 
        return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subject', default='konrad')
    ap.add_argument('--device', default='Muse')
    ap.add_argument('--sample-rate', type=int, default=256)
    ap.add_argument('--config-json', required=True)
    ap.add_argument('--config-version', default='v1')
    ap.add_argument('--db', default=os.environ.get('DATABASE_URL'))
    args = ap.parse_args()

    cfg = open(args.config_json,'rb').read()
    cfg_hash = hashlib.sha256(cfg).hexdigest()
    sid = str(uuid.uuid4())

    conn = psycopg2.connect(args.db)
    with conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO config_bundle(id, version, git_head_sha, dirty, content_hash, content_json)
                       VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                       (args.config_version, git_head(), dirty(), cfg_hash, cfg.decode('utf-8')))
        cur.execute("SELECT id FROM config_bundle WHERE content_hash=%s ORDER BY created_at DESC LIMIT 1", (cfg_hash,))
        cfg_id = cur.fetchone()[0]
        cur.execute("""INSERT INTO session(id, subject, started_at, device, sample_rate, config_id)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                       (sid, args.subject, datetime.now(timezone.utc), args.device, args.sample_rate, cfg_id))
    conn.close()
    print(sid)

if __name__ == "__main__":
    main()