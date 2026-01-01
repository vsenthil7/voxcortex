import logging
import sys

# =========================================
# Trace Injection Filter (GLOBAL)
# =========================================

class TraceContextFilter(logging.Filter):
    """
    Ensures every LogRecord has a trace_id.
    Prevents formatter crashes from 3rd-party loggers.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return True


# =========================================
# Logger Setup
# =========================================

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s trace=%(trace_id)s %(name)s - %(message)s"
    )

    handler.setFormatter(formatter)
    handler.addFilter(TraceContextFilter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 🔒 CRITICAL: reset handlers to avoid duplication
    root.handlers.clear()
    root.addHandler(handler)


# =========================================
# Trace-Aware Logger Helper
# =========================================

def trace_logger(trace_id: str, logger_name: str = "voxcortex"):
    """
    Returns a logger bound to a trace_id.
    """
    logger = logging.getLogger(logger_name)

    class _TraceAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            extra = kwargs.get("extra", {})
            extra["trace_id"] = trace_id
            kwargs["extra"] = extra
            return msg, kwargs

    return _TraceAdapter(logger, {})


# =========================================
# Auto-initialize logging ON IMPORT
# =========================================

setup_logging()
