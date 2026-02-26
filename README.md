# CronBeats Python SDK (Ping)

[![PyPI version](https://img.shields.io/pypi/v/cronbeats-python)](https://pypi.org/project/cronbeats-python/)
[![Downloads](https://img.shields.io/pypi/dm/cronbeats-python)](https://pypi.org/project/cronbeats-python/)
[![Python versions](https://img.shields.io/pypi/pyversions/cronbeats-python)](https://pypi.org/project/cronbeats-python/)

Official Python SDK for CronBeats ping telemetry.

## Install

```bash
pip install cronbeats-python
```

## Quick Usage

```python
from cronbeats_python import PingClient

client = PingClient("abc123de")
client.start()
# ...your work...
client.success()
```

## Real-World Cron Job Example

```python
from cronbeats_python import PingClient

client = PingClient("abc123de")
client.start()

try:
    # your actual cron work
    process_emails()
    client.success()
except Exception:
    client.fail()
```

## Progress Tracking

Track your job's progress in real-time. CronBeats supports two distinct modes:

### Mode 1: With Percentage (0-100)
Shows a **progress bar** and your status message on the dashboard.

✓ **Use when**: You can calculate meaningful progress (e.g., processed 750 of 1000 records)

```python
# Percentage mode: 0-100 with message
client.progress(50, "Processing batch 500/1000")

# Or using dict
client.progress({
    "seq": 75,
    "message": "Almost done - 750/1000",
})
```

### Mode 2: Message Only
Shows **only your status message** (no percentage bar) on the dashboard.

✓ **Use when**: Progress isn't measurable or you only want to send status updates

```python
# Message-only mode: None seq, just status updates
client.progress(None, "Connecting to database...")
client.progress(None, "Starting data sync...")
```

### What you see on the dashboard
- **Mode 1**: Progress bar (0-100%) + your message → "75% - Processing batch 750/1000"
- **Mode 2**: Only your status message → "Connecting to database..."

### Complete Example

```python
from cronbeats_python import PingClient

client = PingClient("abc123de")
client.start()

try:
    # Message-only updates for non-measurable steps
    client.progress(None, "Connecting to database...")
    db = connect_to_database()
    
    client.progress(None, "Fetching records...")
    total = db.count()
    
    # Percentage updates for measurable progress
    for i in range(total):
        process_record(i)
        
        if i % 100 == 0:
            percent = int((i * 100) / total)
            client.progress(percent, f"Processed {i} / {total} records")
    
    client.progress(100, "All records processed")
    client.success()
    
except Exception:
    client.fail()
    raise
```

## Notes

- SDK uses `POST` for telemetry requests.
- `job_key` must be exactly 8 Base62 characters.
- Retries happen only for network errors, HTTP `429`, and HTTP `5xx`.
- Default 5s timeout ensures the SDK never blocks your cron job if CronBeats is unreachable.
