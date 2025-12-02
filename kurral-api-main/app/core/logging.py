"""
Logging configuration
"""

import logging
import sys
from pathlib import Path


def setup_logging():
    """Configure application logging"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Setup handlers
    handlers = [logging.StreamHandler(sys.stdout)]

    # Try to add file handler, fall back to console only if it fails
    try:
        log_file = log_dir / "kurral-api.log"
        handlers.append(logging.FileHandler(log_file))
    except PermissionError:
        print(f"⚠️  Warning: Cannot write to {log_dir}. Logging to console only.")

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )

    # Set third-party loggers to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

