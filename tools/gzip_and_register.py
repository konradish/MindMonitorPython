import argparse, gzip, hashlib, os, shutil, uuid, json, subprocess
import psycopg2

def sha256(path, chunk=1024*1024):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest(), os.path.getsize(path)

def ensure_gz(src_csv):
    if src_csv.endswith('.gz'):
        return src_csv
    dst = src_csv + '.gz'
    with open(src_csv, 'rb') as f_in, gzip.open(dst, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    return dst

def git_head_sha():
    try:
        return subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    except Exception:
        return None

def git_dirty():
    try:
        out = subprocess.check_output(['git','status','--porcelain'], text=True)
        return len(out.strip())>0
    except Exception:
        return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--session', required=True)
    ap.add_argument('--csv', required=True)
    ap.add_argument('--config-json', required=True)
    ap.add_argument('--config-version', default='v1')
    ap.add_argument('--db', default=os.environ.get('DATABASE_URL'))
    args = ap.parse_args()

    gz = ensure_gz(args.csv)
    digest, nbytes = sha256(gz)

    cfg_blob = open(args.config_json,'rb').read()
    cfg_hash = hashlib.sha256(cfg_blob).hexdigest()

    conn = psycopg2.connect(args.db)
    with conn, conn.cursor() as cur:
        # Persist config snapshot (idempotent by content hash)
        cur.execute("""
          INSERT INTO config_bundle(id, version, git_head_sha, dirty, content_hash, content_json)
          VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)
          ON CONFLICT DO NOTHING
        """, (args.config_version, git_head_sha(), git_dirty(), cfg_hash, cfg_blob.decode('utf-8')))
        # Attach file to session
        cur.execute("""
          UPDATE session SET raw_path=%s, raw_sha256=%s, raw_bytes=%s
          WHERE id=%s
        """, (gz, digest, nbytes, args.session))
    conn.close()
    print(f"Registered: {gz} sha256={digest} bytes={nbytes}")

if __name__ == "__main__":
    main()