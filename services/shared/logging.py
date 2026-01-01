import logging

# --------------------------------------------------
# Base logging setup
# --------------------------------------------------

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s trace=%(trace_id)s %(name)s - %(message)s",
    )


class TraceAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.setdefault("trace_id", self.extra.get("trace_id", "-"))
        kwargs["extra"] = extra
        return msg, kwargs


# --------------------------------------------------
# Public helpers
# --------------------------------------------------

def get_trace_logger(trace_id: str, logger_name: str = "voxcortex"):
    """
    Returns a logger bound to a trace_id.
    """
    base_logger = logging.getLogger(logger_name)
    return TraceAdapter(base_logger, {"trace_id": trace_id})


def trace_logger(trace_id: str, actor: str, message: str):
    """
    Convenience one-liner logger.
    """
    log = get_trace_logger(trace_id, actor)
    log.info(message)
