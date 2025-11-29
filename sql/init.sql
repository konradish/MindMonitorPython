CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS config_bundle (
  id UUID PRIMARY KEY,
  version TEXT,
  git_head_sha TEXT,
  dirty BOOLEAN NOT NULL DEFAULT false,
  content_hash TEXT NOT NULL,
  content_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session (
  id UUID PRIMARY KEY,
  subject TEXT,
  started_at TIMESTAMPTZ NOT NULL,
  device TEXT,
  sample_rate INT,
  config_id UUID NOT NULL REFERENCES config_bundle(id),
  raw_path TEXT, raw_sha256 TEXT, raw_bytes BIGINT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS eeg_window (
  session_id UUID NOT NULL,
  ts_start   TIMESTAMPTZ NOT NULL,
  ts_end     TIMESTAMPTZ NOT NULL,
  alpha_rel  REAL, beta_rel REAL, theta_rel REAL, delta_rel REAL, gamma_rel REAL,
  entropy    REAL,
  artifact_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
  features       JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (session_id, ts_start)
);
SELECT create_hypertable('eeg_window', by_range('ts_start'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS detection (
  session_id UUID NOT NULL,
  span TSRANGE NOT NULL,
  label TEXT NOT NULL,
  source TEXT NOT NULL, -- 'rule' | 'ml'
  score REAL,
  extra JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS detection_span_gist ON detection USING GIST (span);

CREATE TABLE IF NOT EXISTS annotation (
  session_id UUID NOT NULL,
  span TSRANGE NOT NULL,
  label TEXT NOT NULL,
  author TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS annotation_span_gist ON annotation USING GIST (span);

CREATE TABLE IF NOT EXISTS metrics (
  ts TIMESTAMPTZ NOT NULL,
  name TEXT NOT NULL,
  value DOUBLE PRECISION,
  dims JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS eeg_baseline (
  name TEXT PRIMARY KEY,
  alpha_rel REAL NOT NULL,
  beta_rel REAL NOT NULL,
  theta_rel REAL NOT NULL,
  delta_rel REAL NOT NULL,
  gamma_rel REAL NOT NULL,
  samples INT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE MATERIALIZED VIEW IF NOT EXISTS eeg_window_1s
WITH (timescaledb.continuous) AS
SELECT session_id,
       time_bucket('1 second', ts_start) AS ts,
       avg(alpha_rel) AS alpha_rel, avg(beta_rel) AS beta_rel,
       avg(theta_rel) AS theta_rel, avg(delta_rel) AS delta_rel,
       avg(gamma_rel) AS gamma_rel, avg(entropy) AS entropy
FROM eeg_window
GROUP BY session_id, time_bucket('1 second', ts_start);

SELECT add_continuous_aggregate_policy('eeg_window_1s',
  start_offset => INTERVAL '7 days',
  end_offset   => INTERVAL '1 minute',
  schedule_interval => INTERVAL '1 minute');