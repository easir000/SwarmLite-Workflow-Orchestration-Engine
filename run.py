import asyncio
from datetime import datetime
from src.config.config import Config
from src.orchestrator.parser import WorkflowParser
from src.orchestrator.engine import WorkflowEngine
from src.orchestrator.state_manager import StateManager
from src.utils.retry_handler import RetryHandler
from src.orchestrator.governance import GovernanceEngine
import yaml

async def main():
    # Validate configuration
    Config.validate_required_keys()
    
    # Initialize components with configuration
    state_manager = StateManager(db_url=Config.DATABASE_URL)
    retry_handler = RetryHandler(max_attempts=3, delay_seconds=2)
    workflow_engine = WorkflowEngine(state_manager, retry_handler)
    workflow_parser = WorkflowParser()
    governance = GovernanceEngine()  # Uses governance.yaml from config
    
    # Load example workflow
    with open('examples/reliable_workflow.yaml', 'r') as f:
        workflow_yaml = f.read()
    
    # Parse workflow
    workflow = workflow_parser.parse(workflow_yaml)
    workflow_parser.validate_dag(workflow)
    
    # Validate governance
    governance.validate_workflow(workflow)
    
    print(f"Starting workflow: {workflow.id}")
    print(f"Tasks: {[task.id for task in workflow.tasks]}")
    print(f"Governance policy enforced by: {governance.config['policy_owner']}")
    
    # Execute workflow
    result = await workflow_engine.execute_workflow(workflow)
    
    execution_time = (result.completed_at - result.started_at).total_seconds() if result.completed_at and result.started_at else 'N/A'
    print(f"Workflow completed with status: {result.status}")
    print(f"Execution time: {execution_time} seconds")
    
    # Show task results
    for task in result.tasks:
        print(f"Task {task.id}: {task.status} (attempts: {task.retry_count})")

if __name__ == "__main__":
    asyncio.run(main())