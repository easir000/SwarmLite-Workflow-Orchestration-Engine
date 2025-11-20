import structlog
import logging
import re
from datetime import datetime
from typing import Dict, Any

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class WorkflowLogger:
    def __init__(self):
        self.logger = logger.bind(component="workflow_engine")
    
    def log_task_start(self, workflow_id: str, task_id: str, task_type: str, data_classification: str = "public"):
        self.logger.info(
            "task_started",
            workflow_id=workflow_id,
            task_id=task_id,
            task_type=task_type,
            data_classification=data_classification,
            timestamp=datetime.now().isoformat()
        )
    
    def log_task_end(self, workflow_id: str, task_id: str, status: str, duration_ms: float, result: Any = None):
        # DO NOT mask result - just log it directly
        self.logger.info(
            "task_completed",
            workflow_id=workflow_id,
            task_id=task_id,
            status=status,
            duration_ms=duration_ms,
            result=result,  # No masking
            timestamp=datetime.now().isoformat()
        )
    
    def log_error(self, workflow_id: str, task_id: str, error: str, context: Dict[str, Any] = None):
        try:
            log_data = {
                "workflow_id": workflow_id,
                "task_id": task_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
            if context:
                log_data.update(context)
            
            self.logger.error("task_error", **log_data)
        except Exception as e:
            # If logging fails, just print to console to avoid infinite loop
            print(f"ERROR LOGGING FAILED: {str(e)}")
    
    def log_workflow_status(self, workflow_id: str, status: str, context: Dict[str, Any] = None):
        try:
            log_data = {
                "workflow_id": workflow_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            if context:
                log_data.update(context)
            
            self.logger.info("workflow_status", **log_data)
        except Exception as e:
            # If logging fails, just print to console to avoid infinite loop
            print(f"WORKFLOW STATUS LOG FAILED: {str(e)}")
    
    def log_governance_event(self, workflow_id: str, event_type: str, details: Dict[str, Any]):
        try:
            self.logger.info(
                "governance_event",
                workflow_id=workflow_id,
                event_type=event_type,
                details=details,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            # If logging fails, just print to console to avoid infinite loop
            print(f"GOVERNANCE EVENT LOG FAILED: {str(e)}")