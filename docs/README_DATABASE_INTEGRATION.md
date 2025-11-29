# Database-Enabled Consciousness Monitor

This implementation provides database integration for the EEG consciousness monitor with **single-compute architecture** to avoid double parsing and timing drift.

## 🏗️ Architecture

### Single Source of Truth
- **One parser/processor**: The consciousness monitor computes windows once
- **Database instrumentation**: Computed results are "tee'd" to TimescaleDB  
- **No duplicate work**: Avoids double FFTs, double parsing, or timing mismatches
- **Consistent results**: UI display and database contain identical computed values

### Mode System
- **`--db-only`**: Silent database ingestion (no UI output) 
- **`--ui-only`**: Original monitor behavior (no database writes)
- **`--dual`**: Both UI and database (requires explicit `--double-parse-ok` flag)

## 🚀 Quick Start

### 1. Start Database (with Host Access)
```bash
# Restart containers to expose database on port 5590
docker compose down && docker compose up -d

# Verify database is accessible
docker compose exec db psql -U eeg -d eeg -c "SELECT version();"
```

### 2. Start Your Workflow

#### Option A: Database-Only Mode (Recommended)
```bash
# Generate session ID
SESSION_ID=$(uuidgen)
echo "Session: $SESSION_ID"

# Start database ingestion (silent, no UI)
DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
uv run python consciousness_monitor_db_v2.py \
  --db-only \
  --session-id $SESSION_ID \
  --csv "C:/projects/MindMonitorPython/mind_monitor_complete.csv"
```

#### Option B: UI-Only Mode (Original Behavior)
```bash
# Original consciousness monitor (no database)
uv run python consciousness_monitor_db_v2.py \
  --ui-only \
  --konrad-mode --cycle-detection --sample-rate 88 --window 2.0 --update 60.0
```

#### Option C: Dual Mode (Use with Caution)
```bash
# Both UI and database (potential timing drift)
SESSION_ID=$(uuidgen)
uv run python consciousness_monitor_db_v2.py \
  --dual --double-parse-ok \
  --session-id $SESSION_ID \
  --csv "mind_monitor_complete.csv" \
  --konrad-mode --cycle-detection --sample-rate 88 --window 2.0 --update 60.0
```

### 3. Verify Ingestion
```bash
# Run verification script
uv run python tools/verify_ingestion.py --session-id $SESSION_ID --host-db

# Manual verification queries
docker compose exec db psql -U eeg -d eeg -c "
SELECT count(*) AS n, min(ts_start), max(ts_start) 
FROM eeg_window WHERE session_id = '$SESSION_ID';"
```

## 📊 Database Schema

### Core Tables
- **`session`**: Session metadata with config linkage
- **`eeg_window`**: Raw computed windows (primary data)
- **`eeg_window_1s`**: Continuous aggregate (1-second intervals)
- **`detection`**: State detection intervals
- **`config_bundle`**: Configuration tracking (git SHA + content hash)

### Data Flow
1. **Muse-player** → CSV file (live append)
2. **Consciousness monitor** → Computes band powers, detections
3. **Database instrumentation** → Emits to TimescaleDB
4. **Continuous aggregates** → Update automatically

## 🔧 Key Features

### Session Management
- **Automatic session creation** with metadata
- **Config bundle linkage** (git SHA + parameter hash)
- **Author tracking** from `EEG_AUTHOR` environment variable

### Graceful Shutdown
- **Signal handling** (SIGINT/SIGTERM)
- **Detection interval closure** on shutdown
- **Batch flushing** before exit

### Data Consistency
- **Single computation path** (no duplicate processing) 
- **Timezone normalization** (all timestamps in UTC)
- **Primary key constraints** prevent duplicates
- **Retry logic** for database resilience

## 📈 Verification Checklist

Run after 2-3 minutes of ingestion:

```sql
-- 1. Window count and time range
SELECT count(*) AS n, min(ts_start), max(ts_start)
FROM eeg_window WHERE session_id = '<SESSION_UUID>';

-- 2. Continuous aggregate updating
SELECT * FROM eeg_window_1s 
WHERE session_id = '<SESSION_UUID>' 
ORDER BY ts DESC LIMIT 5;

-- 3. No duplicates (CRITICAL)
SELECT ts_start, count(*) c FROM eeg_window 
WHERE session_id = '<SESSION_UUID>'
GROUP BY 1 HAVING count(*)>1 
ORDER BY ts_start ASC LIMIT 5;
```

**If query #3 returns rows**: You have duplicates! This means both monitor and wrapper are writing.

## 🛡️ Best Practices

### File Management
- **Keep recording as `.csv`** while appending
- **Gzip only after session ends** using `gzip_and_register.py`
- **Use absolute paths** or forward slashes on Windows

### Database Access
- **Container mode**: Uses internal `db:5432` connection
- **Host mode**: Uses exposed `localhost:5590` connection
- **Environment variable**: `DATABASE_URL` overrides defaults

### Performance Tuning
- **Batch size**: 250-1000 rows for efficient inserts
- **Connection pooling**: Single connection per session
- **Backpressure handling**: Retry logic with exponential backoff

## 🔍 Troubleshooting

### Common Issues

**"Database components not available"**
```bash
# Install missing dependencies
uv add psycopg2-binary
```

**"CSV file does not exist"**
```bash
# Use absolute path
--csv "C:/projects/MindMonitorPython/mind_monitor_complete.csv"
```

**"Database connection failed"**
```bash
# Check container status
docker compose ps

# Check port accessibility  
telnet localhost 5590

# Try container connection instead
DATABASE_URL="postgresql://eeg:eegpass@db:5432/eeg" uv run python...
```

**Duplicates detected**
- Only run ONE database writer at a time
- Use `--ui-only` if you don't want database writes
- Use `--db-only` for silent ingestion

### Debug Mode
```bash
# Enable debug logging
uv run python consciousness_monitor_db_v2.py --db-only --debug --session-id $SESSION_ID --csv "file.csv"
```

## 📂 File Structure

```
tools/
├── consciousness_monitor_db_v2.py    # Main database-enabled wrapper (RECOMMENDED)
├── consciousness_monitor_db.py       # Legacy dual-parser version (avoid)
├── verify_ingestion.py               # Verification script
├── tail_import.py                    # Standalone CSV tailer
├── historical_import.py              # Batch historical import
└── README_ingestion.md               # Detailed ingestion documentation

compose.yml                           # Updated with exposed database port
migrations/003_checkpoint_and_aliases.sql  # Database schema updates
```

## 🎯 Recommended Workflow

### For Live Recording
```bash
# Terminal 1: Start muse-player  
.\muse-player -l udp:5000 -C mind_monitor_complete.csv

# Terminal 2: Start database ingestion
SESSION_ID=$(uuidgen)
echo "Session: $SESSION_ID"

DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
uv run python consciousness_monitor_db_v2.py \
  --db-only \
  --session-id $SESSION_ID \
  --csv "mind_monitor_complete.csv"

# Terminal 3: Verify progress (optional)
watch -n 10 "uv run python tools/verify_ingestion.py --session-id $SESSION_ID --host-db"
```

### For Historical Analysis
```bash
# Import large historical file
uv run python tools/historical_import.py \
  --session-id $(uuidgen) \
  --csv "large_historical_recording.csv"
```

### Data Export
```bash
# Export session for analysis
uv run python tools/export_downsample.py \
  --session $SESSION_ID \
  --hz 1 \
  --out "exported_session.csv"
```

This architecture ensures **single source of truth**, **no timing drift**, and **efficient database integration** while preserving your existing consciousness monitoring workflow.