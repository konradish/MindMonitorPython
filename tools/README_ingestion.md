# EEG Data Ingestion Tools

This directory contains tools for ingesting EEG data from CSV files into TimescaleDB with resumable checkpoints.

## Tools Overview

### 1. Live Tail Ingestion (`tail_import.py`)

Real-time ingestion of live CSV data with minimal latency. Monitors a CSV file for new data and processes it incrementally.

**Use Case:** Monitor live recordings from `OSC Receiver.py` while they're being written.

```bash
# Tail a live recording session  
uv run python tools/tail_import.py --session <UUID> --csv data/live_recording.csv

# Custom polling interval (500ms default)
uv run python tools/tail_import.py --session <UUID> --csv recording.csv --poll-interval 250

# Larger batch size for high-throughput  
uv run python tools/tail_import.py --session <UUID> --csv recording.csv --batch-size 1000
```

**Features:**
- **Resumable**: Maintains checkpoints for crash recovery
- **Edge-case handling**: Handles partial lines, headers, file rotation
- **Low latency**: 500ms polling by default, configurable down to 100ms
- **Memory efficient**: Processes data in small batches

### 2. Historical Import (`historical_import.py`)

Chunked processing of large existing CSV files with memory efficiency.

**Use Case:** Import large historical recordings (GB+ files) without memory issues.

```bash
# Import large historical recording
uv run python tools/historical_import.py --session <UUID> --csv data/large_recording.csv

# Custom chunk size (10k rows default)
uv run python tools/historical_import.py --session <UUID> --csv recording.csv --chunk-size 5000

# Validate existing import
uv run python tools/historical_import.py --session <UUID> --csv recording.csv --validate-only
```

**Features:**
- **Memory efficient**: Processes files in 10k-row chunks by default
- **Resumable**: Checkpoints every chunk, can resume from interruption
- **Format detection**: Auto-detects OSC vs generic CSV formats
- **Integrity checking**: SHA256 checksums prevent duplicate imports
- **Progress tracking**: Detailed logging of import progress

## Database Schema

### Checkpoint Table

Tracks ingestion progress for resumable processing:

```sql
CREATE TABLE ingestion_checkpoint (
  file_path TEXT PRIMARY KEY,         -- Source CSV file path
  session_id UUID NOT NULL,           -- Target session UUID  
  byte_offset BIGINT DEFAULT 0,       -- File position (for tail mode)
  line_number BIGINT DEFAULT 0,       -- Row number (for chunked mode)
  last_ts TIMESTAMPTZ,                -- Last processed timestamp
  file_sha256 TEXT,                   -- File integrity hash
  updated_at TIMESTAMPTZ DEFAULT now() -- Last checkpoint update
);
```

### View Aliases

For backward compatibility with existing tools:

```sql
-- Allows tools expecting 'window' to work with 'eeg_window'
CREATE VIEW "window" AS SELECT * FROM eeg_window;
CREATE VIEW "window_1s" AS SELECT * FROM eeg_window_1s;
```

## Data Processing Pipeline

Both tools follow the same processing pipeline:

1. **Parse CSV** → Detect format (OSC/generic) and extract EEG channels
2. **Compute Features** → Calculate band powers using consciousness_monitor processors
3. **Database Insert** → Batch insert into `eeg_window` table via TimescaleSink
4. **Checkpoint** → Save progress for resumability

## Error Handling & Recovery

### Resumable Processing

Both tools maintain checkpoints in the `ingestion_checkpoint` table:

- **Tail mode**: Tracks byte offset in file
- **Historical mode**: Tracks row number and file hash
- **Crash recovery**: Resume from last successful checkpoint
- **Duplicate prevention**: Primary key constraints prevent re-importing

### File Integrity

- **SHA256 checksums**: Detect file changes between runs
- **Format validation**: Auto-detect and handle different CSV formats  
- **Partial line handling**: Wait for complete lines before processing
- **Header detection**: Skip repeated headers in multi-session files

## Performance Considerations

### Tail Import (Real-time)

- **Polling interval**: Balance between latency (250ms) and CPU usage (1000ms)
- **Batch size**: Balance between memory (100) and database efficiency (1000)
- **Network latency**: Database connection should be low-latency for real-time

### Historical Import (Batch)

- **Chunk size**: Balance between memory (5k) and progress granularity (20k)
- **Database connections**: Single connection per import for consistency
- **I/O patterns**: Sequential file reads for optimal disk performance

## Integration Examples

### Live Recording Workflow

```bash
# Terminal 1: Start live recording
uv run python "OSC Receiver.py" --output live_session.csv

# Terminal 2: Start live ingestion (different session ID)
SESSION_ID=$(uuidgen)
uv run python tools/tail_import.py --session $SESSION_ID --csv live_session.csv

# Terminal 3: Monitor ingestion progress
docker compose exec db psql -U eeg -d eeg -c "SELECT COUNT(*) FROM eeg_window WHERE session_id = '$SESSION_ID';"
```

### Historical Archive Processing

```bash
# Process large historical files
for csv_file in archive/*.csv; do
  SESSION_ID=$(uuidgen)
  echo "Processing $csv_file as session $SESSION_ID"
  uv run python tools/historical_import.py --session $SESSION_ID --csv "$csv_file"
done

# Validate all imports
uv run python tools/export_downsample.py --session $SESSION_ID --hz 1 --out validation.csv
```

### File Rotation Handling

```bash
# Handle daily file rotation
DATE=$(date +%Y%m%d)
uv run python tools/tail_import.py --session $SESSION_ID --csv "recording_$DATE.csv" &

# At midnight, stop tail and start new session
# (implement in cron job or systemd service)
```

## Troubleshooting

### Common Issues

**"File does not exist" error:**
- Ensure CSV file path is absolute or relative to working directory
- Check file permissions are readable

**"Invalid session UUID" error:**
- Use `uuidgen` to generate valid UUIDs
- Ensure UUID format is correct (8-4-4-4-12 hex digits)

**Database connection failures:**
- Verify TimescaleDB is running: `docker compose ps`
- Check connection string matches compose.yml settings
- Ensure database is healthy: `docker compose logs db`

**Memory issues with large files:**
- Reduce chunk size: `--chunk-size 1000`
- Monitor system memory usage during import
- Consider splitting very large files before import

### Debug Mode

Both tools support verbose logging:

```bash
# Enable debug logging
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Then run your import command
"
```

### Database Diagnostics

```sql
-- Check checkpoint status
SELECT * FROM ingestion_checkpoint ORDER BY updated_at DESC;

-- Verify data continuity  
SELECT session_id, COUNT(*), MIN(ts_start), MAX(ts_start)
FROM eeg_window 
GROUP BY session_id;

-- Find data gaps
SELECT session_id, ts_start, 
       LAG(ts_start) OVER (PARTITION BY session_id ORDER BY ts_start) as prev_ts,
       EXTRACT(EPOCH FROM (ts_start - LAG(ts_start) OVER (PARTITION BY session_id ORDER BY ts_start))) as gap_seconds
FROM eeg_window 
WHERE EXTRACT(EPOCH FROM (ts_start - LAG(ts_start) OVER (PARTITION BY session_id ORDER BY ts_start))) > 2.0
ORDER BY session_id, ts_start;
```