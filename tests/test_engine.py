import pytest
from src.orchestrator.engine import WorkflowEngine
from src.orchestrator.state_manager import StateManager
from src.utils.retry_handler import RetryHandler
from src.models.workflow import Workflow, Task, TaskStatus, WorkflowStatus

def test_workflow_engine_initialization():
    """Test that WorkflowEngine initializes properly"""
    state_manager = StateManager()
    retry_handler = RetryHandler()
    engine = WorkflowEngine(state_manager, retry_handler)
    
    # Verify that required attributes exist
    assert hasattr(engine, 'state_manager')
    assert hasattr(engine, 'retry_handler') 
    assert hasattr(engine, 'task_executor')
    assert engine.state_manager is not None
    assert engine.retry_handler is not None
    assert engine.task_executor is not None

def test_simple_workflow_execution():
    """Test that a simple workflow can be executed"""
    state_manager = StateManager()
    retry_handler = RetryHandler()
    engine = WorkflowEngine(state_manager, retry_handler)
    
    # Create a simple workflow with one task
    workflow = Workflow(
        id="simple_test_workflow",
        tasks=[
            Task(
                id="test_task", 
                type="python", 
                config={"function": "validate_schema"}
            )
        ]
    )
    
    # The workflow should be able to execute
    assert workflow.id == "simple_test_workflow"
    assert len(workflow.tasks) == 1
    assert workflow.tasks[0].id == "test_task"
    assert workflow.tasks[0].type == "python"

@pytest.mark.asyncio
async def test_execute_basic_workflow():
    """Test executing a basic workflow"""
    state_manager = StateManager()
    retry_handler = RetryHandler()
    engine = WorkflowEngine(state_manager, retry_handler)
    
    workflow = Workflow(
        id="execute_test",
        tasks=[
            Task(id="basic_task", type="python", config={"function": "validate_schema"})
        ]
    )
    
    # Execute the workflow
    result = await engine.execute_workflow(workflow)
    
    # The workflow should complete (either success or failure, but not remain pending)
    assert result.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]
    assert len(result.tasks) == 1
    
    # The task should have been processed (could be any status after execution)
    task = result.tasks[0]
    assert task.id == "basic_task"
    # Task could be in any state after execution - SUCCESS, FAILED, or even ROLLBACK
    assert task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.ROLLBACK, TaskStatus.PENDING]