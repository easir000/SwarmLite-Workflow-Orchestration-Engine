import asyncio
import networkx as nx
from typing import Dict, List, Optional
from datetime import datetime
from ..models.workflow import Workflow, Task, TaskStatus, WorkflowStatus
from ..utils.logger import WorkflowLogger
from ..utils.retry_handler import RetryHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class WorkflowEngine:
    def __init__(self, state_manager, retry_handler: RetryHandler):
        self.state_manager = state_manager
        self.retry_handler = retry_handler
        # Import inside to avoid circular imports
        from .task_executor import TaskExecutor
        from .governance import GovernanceEngine
        self.task_executor = TaskExecutor(retry_handler)
        self.governance = GovernanceEngine()
        self.logger = WorkflowLogger()
        self.running_workflows: Dict[str, asyncio.Task] = {}
    
    async def execute_workflow(self, workflow: Workflow) -> Workflow:
        """
        Execute workflow with dependency resolution and fault tolerance
        """
        try:
            # --- GOVERNANCE ENFORCEMENT ---
            self.governance.validate_workflow(workflow)
            
            workflow.started_at = datetime.now()
            workflow.status = WorkflowStatus.RUNNING
            
            # Persist initial workflow state
            self.state_manager.persist_workflow(workflow)
            
            # Build dependency graph
            graph = self._build_dependency_graph(workflow)
            
            # Execute tasks in topological order
            execution_order = list(nx.topological_sort(graph))
            
            # Track task results
            task_results = {}
            
            # Keep track of completed task IDs
            completed_tasks = set()
            
            for task_id in execution_order:
                task = next((t for t in workflow.tasks if t.id == task_id), None)
                if not task:
                    continue
                
                # Check if task is already completed (idempotency)
                current_status = self.state_manager.get_current_task_status(workflow.id, task.id)
                if current_status == TaskStatus.SUCCESS.value:
                    self.logger.log_task_end(workflow.id, task.id, "already_completed", 0)
                    completed_tasks.add(task.id)
                    continue
                
                # Check dependencies using completed_tasks set
                dependencies_satisfied = all(dep_id in completed_tasks for dep_id in task.depends_on)
                if not dependencies_satisfied:
                    # If dependencies aren't satisfied, skip this task and continue
                    continue
                
                # Execute task
                executed_task = await self.task_executor.execute_task(workflow.id, task)
                
                # Persist task state
                self.state_manager.persist_task(workflow.id, executed_task)
                
                # Update workflow task
                for i, t in enumerate(workflow.tasks):
                    if t.id == task.id:
                        workflow.tasks[i] = executed_task
                        break
                
                # Store result for potential use by dependent tasks
                task_results[task.id] = executed_task.result
                
                # Add to completed tasks if successful
                if executed_task.status == TaskStatus.SUCCESS:
                    completed_tasks.add(task.id)
                
                # If task failed, handle rollback
                if executed_task.status == TaskStatus.FAILED:
                    await self._handle_failure(workflow, executed_task)
                    return workflow
            
            # Workflow completed successfully
            workflow.status = WorkflowStatus.SUCCESS
            workflow.completed_at = datetime.now()
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            # Log the error with proper handling
            self.logger.log_error(workflow.id, "workflow", str(e))
        
        # Persist final workflow state
        try:
            self.state_manager.persist_workflow(workflow)
        except Exception as e:
            self.logger.log_error(workflow.id, "final_persist", str(e))
        
        return workflow
    
    def _build_dependency_graph(self, workflow) -> nx.DiGraph:
        """
        Build dependency graph from workflow tasks
        """
        graph = nx.DiGraph()
        
        # Add all tasks as nodes
        for task in workflow.tasks:
            graph.add_node(task.id)
        
        # Add dependency edges
        for task in workflow.tasks:
            for dependency in task.depends_on:
                graph.add_edge(dependency, task.id)
        
        return graph
    
    async def _handle_failure(self, workflow, failed_task: Task):
        """
        Handle workflow failure with rollback logic
        """
        workflow.status = WorkflowStatus.FAILED
        
        # Execute compensation handlers for failed and successfully completed tasks
        for task in workflow.tasks:
            if task.id in workflow.compensation_handlers and task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                compensation_func = workflow.compensation_handlers[task.id]
                
                # Check if compensation_func is a string (function name) or callable
                try:
                    if isinstance(compensation_func, str):
                        # If it's a string, log it but don't execute (for demo purposes)
                        self.logger.log_error(workflow.id, f"compensation_{task.id}", f"Compensation function {compensation_func} not implemented")
                        task.status = TaskStatus.ROLLBACK
                    else:
                        # If it's a callable, execute it
                        self.retry_handler.execute_compensation(compensation_func, workflow.id, task.id)
                        task.status = TaskStatus.ROLLBACK
                except Exception as e:
                    self.logger.log_error(workflow.id, f"compensation_{task.id}", str(e))
        
        self.logger.log_workflow_status(workflow.id, "failed_with_rollback")
    
    async def start_workflow(self, workflow: Workflow) -> str:
        """
        Start workflow execution asynchronously
        """
        workflow_id = workflow.id
        task = asyncio.create_task(self.execute_workflow(workflow))
        self.running_workflows[workflow_id] = task
        
        return workflow_id
    
    async def stop_workflow(self, workflow_id: str) -> bool:
        """
        Stop a running workflow
        """
        if workflow_id in self.running_workflows:
            task = self.running_workflows[workflow_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.running_workflows[workflow_id]
            return True
        return False
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """
        Get current workflow status
        """
        return self.state_manager.get_workflow_status(workflow_id)
    
    def get_workflow_history(self, workflow_id: str) -> List:
        """
        Get workflow execution history
        """
        return self.state_manager.get_workflow_state(workflow_id)