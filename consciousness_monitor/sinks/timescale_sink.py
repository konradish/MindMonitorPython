from typing import Iterable, Dict, Any
import os, time, psycopg2, psycopg2.extras, json

class TimescaleSink:
    def __init__(self, db_url=None, batch=500):
        self.db = db_url or os.environ['DATABASE_URL']
        self.batch = batch

    def _conn(self):
        return psycopg2.connect(self.db)

    def on_windows(self, rows: Iterable[Dict[str,Any]]):
        buf = []
        for r in rows:
            # Convert numpy types to Python native types for PostgreSQL
            def convert_numpy(value):
                if hasattr(value, 'item'):  # numpy scalar
                    return value.item()
                return float(value) if value is not None else None
            
            # Custom JSON encoder for complex objects
            def make_json_serializable(obj):
                if hasattr(obj, 'to_dict'):  # Custom objects with to_dict method
                    return obj.to_dict()
                elif hasattr(obj, 'as_dict'):  # Custom objects with as_dict method
                    return obj.as_dict()
                elif hasattr(obj, '__dict__'):  # General objects with attributes
                    return {k: make_json_serializable(v) for k, v in obj.__dict__.items() 
                           if not k.startswith('_')}
                elif isinstance(obj, dict):
                    return {k: make_json_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [make_json_serializable(item) for item in obj]
                elif hasattr(obj, 'item'):  # numpy scalars
                    return obj.item()
                else:
                    return obj
            
            # Serialize JSON fields safely
            artifact_flags_data = r.get('artifact_flags', {})
            features_data = r.get('features', {})
            
            artifact_flags = json.dumps(make_json_serializable(artifact_flags_data))
            features = json.dumps(make_json_serializable(features_data))
            
            # Ensure session_id is a string (convert UUID objects)
            session_id = str(r['session_id'])
            
            buf.append((
               session_id, r['ts_start'], r['ts_end'],
               convert_numpy(r.get('alpha_rel')), convert_numpy(r.get('beta_rel')), convert_numpy(r.get('theta_rel')),
               convert_numpy(r.get('delta_rel')), convert_numpy(r.get('gamma_rel')), convert_numpy(r.get('entropy')),
               artifact_flags, features
            ))
            if len(buf) >= self.batch:
                self._flush(buf); buf.clear()
        if buf: self._flush(buf)

    def _flush(self, buf):
        for attempt in range(3):
            try:
                with self._conn() as conn, conn.cursor() as cur:
                    psycopg2.extras.execute_values(cur, """
                      INSERT INTO eeg_window
                      (session_id, ts_start, ts_end, alpha_rel,beta_rel,theta_rel,delta_rel,gamma_rel,entropy,artifact_flags,features)
                      VALUES %s
                      ON CONFLICT (session_id, ts_start) DO NOTHING
                    """, buf, page_size=self.batch, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)")
                return
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def on_detection(self, session_id, start, end, label, source="rule", score=None, extra=None):
        span = f'[{start},{end})'
        # Ensure session_id is a string (convert UUID objects)
        session_id_str = str(session_id)
        
        # Convert extra dict to JSON string if needed
        extra_json = json.dumps(extra or {})
        
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("""
              INSERT INTO detection(session_id, span, label, source, score, extra)
              VALUES (%s, %s::tsrange, %s, %s, %s, %s::jsonb)
            """, (session_id_str, span, label, source, score, extra_json))