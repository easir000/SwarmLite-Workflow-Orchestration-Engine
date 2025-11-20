from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

class DataClassification(Enum):
    PUBLIC = "public"
    PHI = "phi"  # Protected Health Information
    PII = "pii"  # Personally Identifiable Information
    CONFIDENTIAL = "confidential"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"

class TaskType(Enum):
    HTTP = "http"
    PYTHON = "python"
    DATABASE = "database"
    LLM = "llm"
    RAG = "rag"

@dataclass
class Task:
    id: str
    type: str
    depends_on: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    data_classification: DataClassification = DataClassification.PUBLIC  # NEW
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    retry_count: int = 0

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    delay_seconds: int = 2
    exponential_backoff: bool = True

@dataclass
class Workflow:
    id: str
    tasks: List[Task] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    compensation_handlers: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None  # NEW

@dataclass
class WorkflowState:
    workflow_id: str
    task_id: str
    status: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None  # NEW
    signed_at: Optional[datetime] = None  # NEW