#!/usr/bin/env python3
"""
Quick verification script for database ingestion.

This script runs the verification queries mentioned in the acceptance checklist
to ensure single-source ingestion is working correctly.

Usage:
    uv run python tools/verify_ingestion.py --session-id <UUID>
    uv run python tools/verify_ingestion.py --session-id <UUID> --host-db
"""

import argparse
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Verify database ingestion")
    parser.add_argument('--session-id', required=True, help='Session UUID to verify')
    parser.add_argument('--host-db', action='store_true', help='Use host database port (5590)')
    args = parser.parse_args()
    
    # Validate session UUID
    try:
        session_uuid = uuid.UUID(args.session_id)
    except ValueError:
        print(f"❌ Invalid session UUID: {args.session_id}")
        return 1
    
    # Database URL
    if args.host_db:
        db_url = os.environ.get(
            'DATABASE_URL',
            'postgresql://eeg:eegpass@localhost:5590/eeg'
        )
    else:
        db_url = os.environ.get(
            'DATABASE_URL',
            'postgresql://eeg:eegpass@db:5432/eeg'
        )
    
    try:
        conn = psycopg2.connect(db_url)
        print(f"✅ Connected to database")
        print(f"🔍 Verifying session: {session_uuid}")
        print()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check 1: Window count and time range
            print("📊 1. Window count and time range:")
            cur.execute("""
                SELECT count(*) AS n, 
                       min(ts_start) as min_ts, 
                       max(ts_start) as max_ts,
                       EXTRACT(EPOCH FROM (max(ts_start) - min(ts_start))) / 60 as duration_min
                FROM eeg_window
                WHERE session_id = %s
            """, (str(session_uuid),))
            
            row = cur.fetchone()
            if row and row['n'] > 0:
                print(f"   Windows: {row['n']}")
                print(f"   Time range: {row['min_ts']} to {row['max_ts']}")
                print(f"   Duration: {row['duration_min']:.1f} minutes")
            else:
                print("   ⚠️ No windows found")
            print()
            
            # Check 2: Continuous aggregate
            print("📈 2. Continuous aggregate (latest 5 entries):")
            cur.execute("""
                SELECT ts, alpha_rel, beta_rel, theta_rel, delta_rel, gamma_rel
                FROM eeg_window_1s
                WHERE session_id = %s
                ORDER BY ts DESC 
                LIMIT 5
            """, (str(session_uuid),))
            
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    print(f"   {row['ts']}: α={row['alpha_rel']:.1f}% β={row['beta_rel']:.1f}% θ={row['theta_rel']:.1f}% δ={row['delta_rel']:.1f}% γ={row['gamma_rel']:.1f}%")
            else:
                print("   ⚠️ No continuous aggregate data found")
            print()
            
            # Check 3: Duplicate detection
            print("🔍 3. Duplicate detection check:")
            cur.execute("""
                SELECT ts_start, count(*) as c
                FROM eeg_window
                WHERE session_id = %s
                GROUP BY ts_start 
                HAVING count(*) > 1
                ORDER BY ts_start ASC 
                LIMIT 5
            """, (str(session_uuid),))
            
            duplicates = cur.fetchall()
            if duplicates:
                print("   ❌ DUPLICATES FOUND:")
                for dup in duplicates:
                    print(f"      {dup['ts_start']}: {dup['c']} copies")
                print("   ⚠️ This indicates double-parsing - both monitor and wrapper are writing!")
            else:
                print("   ✅ No duplicates found")
            print()
            
            # Check 4: Session metadata
            print("🗃️ 4. Session metadata:")
            cur.execute("""
                SELECT s.subject, s.started_at, s.device, s.sample_rate, s.notes,
                       cb.git_head_sha, cb.content_hash, cb.version, cb.content_json
                FROM session s
                LEFT JOIN config_bundle cb ON s.config_id = cb.id
                WHERE s.id = %s
            """, (str(session_uuid),))
            
            session = cur.fetchone()
            if session:
                print(f"   Subject: {session['subject']}")
                print(f"   Started: {session['started_at']}")
                print(f"   Device: {session['device']}")
                print(f"   Sample Rate: {session['sample_rate']} Hz")
                print(f"   Notes: {session['notes']}")
                print(f"   Git SHA: {session['git_head_sha']}")
                print(f"   Config Version: {session['version']}")
                if session['content_json']:
                    desc = session['content_json'].get('description', 'No description')
                    print(f"   Config: {desc}")
            else:
                print("   ⚠️ Session metadata not found")
            print()
            
            # Check 5: Detection intervals
            print("🎯 5. Detection intervals (latest 3):")
            cur.execute("""
                SELECT label, span, source, score
                FROM detection
                WHERE session_id = %s
                ORDER BY lower(span) DESC
                LIMIT 3
            """, (str(session_uuid),))
            
            detections = cur.fetchall()
            if detections:
                for det in detections:
                    print(f"   {det['label']}: {det['span']} (source: {det['source']}, score: {det['score']})")
            else:
                print("   ℹ️ No detection intervals found")
            print()
            
            # Check 6: Data quality indicators
            print("📏 6. Data quality indicators:")
            cur.execute("""
                SELECT 
                    AVG(alpha_rel + beta_rel + theta_rel + delta_rel + gamma_rel) as total_power_avg,
                    MIN(alpha_rel + beta_rel + theta_rel + delta_rel + gamma_rel) as total_power_min,
                    MAX(alpha_rel + beta_rel + theta_rel + delta_rel + gamma_rel) as total_power_max,
                    AVG(entropy) as avg_entropy,
                    COUNT(CASE WHEN alpha_rel = 0 AND beta_rel = 0 THEN 1 END) as zero_power_count
                FROM eeg_window
                WHERE session_id = %s
            """, (str(session_uuid),))
            
            quality = cur.fetchone()
            if quality and quality['total_power_avg'] is not None:
                print(f"   Total power: avg={quality['total_power_avg']:.1f}%, min={quality['total_power_min']:.1f}%, max={quality['total_power_max']:.1f}%")
                print(f"   Average entropy: {quality['avg_entropy']:.3f}")
                print(f"   Zero-power windows: {quality['zero_power_count']}")
                
                # Quality warnings
                if quality['total_power_avg'] < 95 or quality['total_power_avg'] > 105:
                    print("   ⚠️ Power percentages don't sum to ~100% - check relative power calculation")
                if quality['zero_power_count'] > 0:
                    print("   ⚠️ Some windows have zero power - check data quality")
            else:
                print("   ⚠️ No quality data available (no windows found)")
        
        conn.close()
        print()
        print("✅ Verification complete!")
        
        # Summary recommendations
        if duplicates:
            print("🚨 ISSUE: Duplicates found - ensure only one process is writing to database")
            return 1
        elif not rows:
            print("⚠️ WARNING: No data found - check if ingestion is running")
            return 1
        else:
            print("✅ All checks passed - ingestion appears to be working correctly")
            return 0
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())