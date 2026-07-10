import logging
import sys

def setup_logging():
    """Sets up unified application logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Clean handler for standard outputs
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
    # 2. FIX: Intercept Uvicorn's internal loggers and force our format
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(logger_name)
        # Clear existing default uvicorn handlers so they don't double-print
        uv_logger.handlers = [] 
        uv_handler = logging.StreamHandler(sys.stdout)
        uv_handler.setFormatter(formatter)
        uv_logger.addHandler(uv_handler)