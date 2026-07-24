import logging
import os
from datetime import datetime

# Configure logging
LOG_FILE = "trip_audit.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_event(level: str, category: str, message: str, details: str = ""):
    """Logs an event to file and console."""
    log_msg = f"[{category.upper()}] {message} | Details: {details}"
    
    if level.lower() == "error":
        logging.error(log_msg)
    elif level.lower() == "warning":
        logging.warning(log_msg)
    else:
        logging.info(log_msg)

def get_recent_logs(limit: int = 20) -> list[str]:
    """Reads the most recent audit log entries for debugging UI."""
    if not os.path.exists(LOG_FILE):
        return ["No audit logs found yet."]
    
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
        return [line.strip() for line in lines[-limit:]]
