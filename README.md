# CronBeats Python SDK (Ping)

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

## Progress Updates

```python
client.progress(50, "Processing batch 50/100")

client.progress({
    "seq": 75,
    "message": "Almost done",
})
```

## Notes

- SDK uses `POST` for telemetry requests.
- `job_key` must be exactly 8 Base62 characters.
- Retries happen only for network errors, HTTP `429`, and HTTP `5xx`.
- Default 5s timeout ensures the SDK never blocks your cron job if CronBeats is unreachable.
