import argparse, os, psycopg2, pandas as pd
import math

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--session', required=True)
    ap.add_argument('--hz', type=float, default=10.0)
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', default=os.environ.get('DATABASE_URL'))
    args = ap.parse_args()

    conn = psycopg2.connect(args.db)
    if int(args.hz) == 1:
        q = """SELECT ts as time, alpha_rel,beta_rel,theta_rel,delta_rel,gamma_rel,entropy
               FROM window_1s WHERE session_id=%s ORDER BY ts"""
        df = pd.read_sql(q, conn, params=[args.session])
    else:
        # 1) pull windows ordered
        q = """SELECT ts_start as time, alpha_rel,beta_rel,theta_rel,delta_rel,gamma_rel,entropy
               FROM eeg_window WHERE session_id=%s ORDER BY ts_start"""
        df = pd.read_sql(q, conn, params=[args.session])
    conn.close()

    if df.empty:
        df.to_csv(args.out, index=False)
        print("No rows")
        return

    if int(args.hz) != 1:
        # 2) estimate hop (median dt)
        dt = (pd.to_datetime(df['time']).diff().dt.total_seconds().dropna().median() or 1.0)
        target_step = 1.0/args.hz
        k = max(1, int(round(target_step / dt)))
        df = df.iloc[::k].copy()

    df.to_csv(args.out, index=False)
    print(f"Wrote {args.out} rows={len(df)}")

if __name__ == "__main__":
    main()