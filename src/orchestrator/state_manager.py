from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base  # ← NEW: Updated import
from datetime import datetime
from typing import List, Optional
from ..models.workflow import WorkflowState, Task, Workflow, WorkflowStatus
from ..utils.logger import WorkflowLogger
import json
import hmac
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

Base = declarative_base()

class WorkflowStateModel(Base):
    __tablename__ = 'workflow_states'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(255), nullable=False)
    task_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    details = Column(Text, nullable=True)
    signature = Column(String(64), nullable=True)  # NEW
    signed_at = Column(DateTime, nullable=True)   # NEW

class StateManager:
    def __init__(self, db_url: str = None):
        # Use environment variable for database URL, fallback to default
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///swarmlite.db")
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.logger = WorkflowLogger()
    
    def save_state(self, workflow_state: WorkflowState):
        """Save workflow state to database"""
        try:
            db_state = WorkflowStateModel(
                workflow_id=workflow_state.workflow_id,
                task_id=workflow_state.task_id,
                status=workflow_state.status,
                timestamp=workflow_state.timestamp,
                details=json.dumps(workflow_state.details)
            )
            
            # Use environment variable for audit secret key
            secret_key = os.getenv("AUDIT_SECRET_KEY")
            if secret_key:
                payload = f"{db_state.workflow_id}|{db_state.task_id}|{db_state.status}|{db_state.timestamp}|{db_state.details}"
                db_state.signature = hmac.new(
                    secret_key.encode(), 
                    payload.encode(), 
                    hashlib.sha256
                ).hexdigest()
                db_state.signed_at = datetime.now()
            
            self.session.add(db_state)
            self.session.commit()
            self.logger.log_workflow_status(workflow_state.workflow_id, "state_saved", {"task_id": workflow_state.task_id})
        except Exception as e:
            self.session.rollback()
            self.logger.log_error("state_manager", "save_state", str(e))
            raise e
    
    def get_workflow_state(self, workflow_id: str) -> List[WorkflowState]:
        """Retrieve workflow execution history"""
        try:
            db_states = self.session.query(WorkflowStateModel).filter_by(workflow_id=workflow_id).all()
            states = []
            for db_state in db_states:
                state = WorkflowState(
                    workflow_id=db_state.workflow_id,
                    task_id=db_state.task_id,
                    status=db_state.status,
                    timestamp=db_state.timestamp,
                    details=json.loads(db_state.details) if db_state.details else {},
                    signature=db_state.signature,
                    signed_at=db_state.signed_at
                )
                states.append(state)
            return states
        except Exception as e:
            self.logger.log_error("state_manager", "get_workflow_state", str(e))
            raise e
    
    def get_current_task_status(self, workflow_id: str, task_id: str) -> Optional[str]:
        """Get current status of a specific task"""
        try:
            db_state = self.session.query(WorkflowStateModel).filter_by(
                workflow_id=workflow_id,
                task_id=task_id
            ).order_by(WorkflowStateModel.timestamp.desc()).first()
            
            return db_state.status if db_state else None
        except Exception as e:
            self.logger.log_error("state_manager", "get_current_task_status", str(e))
            raise e
    
    def persist_workflow(self, workflow):
        """Persist complete workflow state"""
        state = WorkflowState(
            workflow_id=workflow.id,
            task_id=None,
            status=workflow.status.value,
            timestamp=datetime.now(),
            details={
                "tasks": [task.id for task in workflow.tasks],
                "status": workflow.status.value,
                "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
                "idempotency_key": workflow.idempotency_key
            }
        )
        self.save_state(state)
    
    def persist_task(self, workflow_id: str, task):
        """Persist task state"""
        state = WorkflowState(
            workflow_id=workflow_id,
            task_id=task.id,
            status=task.status.value,
            timestamp=datetime.now(),
            details={
                "type": task.type,
                "data_classification": task.data_classification.value,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error": task.error,
                "result": str(task.result) if task.result else None,
                "retry_count": task.retry_count
            }
        )
        self.save_state(state)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """Get current workflow status"""
        try:
            latest_state = self.session.query(WorkflowStateModel).filter_by(
                workflow_id=workflow_id,
                task_id=None
            ).order_by(WorkflowStateModel.timestamp.desc()).first()
            
            if latest_state:
                return WorkflowStatus(latest_state.status)
            return None
        except Exception as e:
            self.logger.log_error("state_manager", "get_workflow_status", str(e))
            raise e
    
    def get_workflow_by_idempotency(self, idempotency_key: str) -> Optional[str]:
        """Get workflow ID by idempotency key"""
        try:
            # This requires a separate table or a different approach
            # For now, we'll search in the details field for idempotency_key
            db_state = self.session.query(WorkflowStateModel).filter(
                WorkflowStateModel.details.like(f'%{idempotency_key}%')
            ).order_by(WorkflowStateModel.timestamp.desc()).first()
            
            return db_state.workflow_id if db_state else None
        except Exception as e:
            self.logger.log_error("state_manager", "get_workflow_by_idempotency", str(e))
            raise e