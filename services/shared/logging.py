import logging
import os

# --- Ensure trace_id always exists on LogRecord ---
_old_factory = logging.getLogRecordFactory()

def record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    if not hasattr(record, "trace_id"):
        record.trace_id = "-"
    return record

logging.setLogRecordFactory(record_factory)


def setup_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s trace=%(trace_id)s %(name)s - %(message)s"
    )
