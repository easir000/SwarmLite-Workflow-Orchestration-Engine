from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import os
from dotenv import load_dotenv
from src.config.config import Config
from ..orchestrator.parser import WorkflowParser
from ..orchestrator.engine import WorkflowEngine
from ..orchestrator.state_manager import StateManager
from ..utils.retry_handler import RetryHandler
from ..models.workflow import Workflow, WorkflowStatus
from ..orchestrator.governance import GovernanceEngine

# Load environment variables
load_dotenv()

app = FastAPI(
    title="SwarmLite API", 
    version="1.0.0",
    debug=Config.DEBUG
)

# Initialize components
state_manager = StateManager(db_url=Config.DATABASE_URL)
retry_handler = RetryHandler()
workflow_engine = WorkflowEngine(state_manager, retry_handler)
workflow_parser = WorkflowParser()

# Store active workflows
active_workflows: Dict[str, Workflow] = {}

class WorkflowDefinition(BaseModel):
    definition: str
    idempotency_key: Optional[str] = None

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str

@app.post("/workflows/start", response_model=WorkflowResponse)
async def start_workflow(
    definition: WorkflowDefinition,
    x_request_source: str = Header(None),
    x_client_id: str = Header(None)
):
    # Validate required headers per governance policy
    required_headers = ["X-Request-Source", "X-Client-ID"]
    if not x_request_source or not x_client_id:
        raise HTTPException(status_code=400, detail=f"Missing required headers: {required_headers}")
    
    try:
        # Check if workflow already exists for idempotency key
        if definition.idempotency_key:
            existing_workflow_id = state_manager.get_workflow_by_idempotency(definition.idempotency_key)
            if existing_workflow_id:
                return WorkflowResponse(
                    workflow_id=existing_workflow_id,
                    status="already_processed",
                    message=f"Workflow with idempotency key {definition.idempotency_key} already processed"
                )
        
        # Parse workflow definition
        workflow = workflow_parser.parse(definition.definition, definition.idempotency_key)
        workflow_parser.validate_dag(workflow)
        
        # Store workflow
        active_workflows[workflow.id] = workflow
        
        # Start workflow execution
        workflow_id = await workflow_engine.start_workflow(workflow)
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="started",
            message=f"Workflow {workflow_id} started successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    try:
        status = workflow_engine.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        history = workflow_engine.get_workflow_history(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": status.value,
            "history": [
                {
                    "task_id": h.task_id,
                    "status": h.status,
                    "timestamp": h.timestamp.isoformat(),
                    "details": h.details
                } for h in history
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflows/{workflow_id}/stop")
async def stop_workflow(workflow_id: str):
    try:
        stopped = await workflow_engine.stop_workflow(workflow_id)
        if not stopped:
            raise HTTPException(status_code=404, detail="Workflow not found or already completed")
        
        return {"message": f"Workflow {workflow_id} stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_workflows": len(active_workflows)}

@app.get("/health/compliance")
async def compliance_check():
    required_envs = ["DB_ENCRYPTION_KEY", "AUDIT_SECRET_KEY", "OPENAI_API_KEY"]
    missing = [k for k in required_envs if not os.getenv(k)]
    
    return {
        "status": "healthy" if not missing else "degraded",
        "compliance": {
            "data_encryption": bool(os.getenv("DB_ENCRYPTION_KEY")),
            "audit_trail": bool(os.getenv("AUDIT_SECRET_KEY")),
            "llm_api_key": bool(os.getenv("OPENAI_API_KEY")),
            "hipaa_compliant": len(missing) == 0,
            "missing_keys": missing
        }
    }

@app.get("/health/governance")
async def governance_status():
    try:
        governance = GovernanceEngine()
        return {
            "policy_version": governance.config["policy_version"],
            "policy_owner": governance.config["policy_owner"],
            "compliance_standards": governance.config["compliance_standards"],
            "enforced_rules": {
                "llm_models_allowed": len(governance.config["rules"]["llm_allowed_models"]),
                "banned_prompts": len(governance.config["rules"]["banned_prompts"]),
                "retention_days": governance.config["rules"]["max_data_retention_days"],
                "required_headers": governance.config["rules"]["required_headers"]
            },
            "status": "active"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

@app.get("/")
async def root():
    return {"message": "SwarmLite Workflow Engine API", "version": "1.0.0"}