import logging
import json
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields from record
        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "details"):
            log_data["details"] = record.details
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_data)

def configure_logging():
    """Configure application logging"""
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Optionally add file handler for persistent logs
    file_handler = logging.FileHandler("app.log")
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    return logger
