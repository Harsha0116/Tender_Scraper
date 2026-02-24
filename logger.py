import logging
import sys


_LOGGER: logging.Logger | None = None
_RUN_ID: str = ""


class RunIdFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = _RUN_ID
        return True


def setup_logger(run_id: str, level: int = logging.INFO) -> logging.Logger:
    
    global _LOGGER, _RUN_ID
    _RUN_ID = run_id

    logger = logging.getLogger("nprocure")
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(run_id)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(fmt)
    handler.addFilter(RunIdFilter())

    logger.addHandler(handler)
    logger.propagate = False

    _LOGGER = logger
    return logger


def get_logger(name: str = "nprocure") -> logging.Logger:
    
    if _LOGGER is None:
        raise RuntimeError("Call setup_logger(run_id) before get_logger().")
    child = _LOGGER.getChild(name.replace("nprocure.", ""))
    child.addFilter(RunIdFilter())
    return child
