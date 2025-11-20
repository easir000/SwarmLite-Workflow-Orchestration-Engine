import yaml
import json
from typing import Dict, Any, Union
from ..models.workflow import Workflow, Task, RetryPolicy, DataClassification
from ..utils.logger import WorkflowLogger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class WorkflowParser:
    def __init__(self):
        self.logger = WorkflowLogger()
    
    def parse(self, workflow_definition: Union[str, Dict], idempotency_key: str = None) -> Workflow:
        """
        Parse YAML/JSON workflow definition into Workflow object
        """
        if isinstance(workflow_definition, str):
            try:
                # Try YAML first
                workflow_data = yaml.safe_load(workflow_definition)
            except yaml.YAMLError:
                try:
                    # Fall back to JSON
                    workflow_data = json.loads(workflow_definition)
                except json.JSONDecodeError:
                    raise ValueError("Invalid workflow definition format")
        else:
            workflow_data = workflow_definition
        
        # Validate required fields
        if 'workflow_id' not in workflow_data or 'tasks' not in workflow_data:  # ← FIXED: Added 'data'
            raise ValueError("Workflow definition must contain 'workflow_id' and 'tasks'")
        
        workflow = Workflow(id=workflow_data['workflow_id'], idempotency_key=idempotency_key)
        
        # Parse retry policy
        retry_policy_data = workflow_data.get('retry_policy', {})
        workflow.retry_policy = RetryPolicy(
            max_attempts=retry_policy_data.get('max_attempts', 3),
            delay_seconds=retry_policy_data.get('delay_seconds', 2),
            exponential_backoff=retry_policy_data.get('exponential_backoff', True)
        )
        
        # Parse tasks
        for task_data in workflow_data['tasks']:
            task = Task(
                id=task_data['id'],
                type=task_data['type'],
                depends_on=task_data.get('depends_on', []),
                config=task_data.get('config', {}),
                data_classification=DataClassification(task_data.get('data_classification', 'public'))
            )
            workflow.tasks.append(task)
        
        # Parse compensation handlers
        compensation_data = workflow_data.get('compensation_handlers', {})
        for task_id, comp_handler in compensation_data.items():
            workflow.compensation_handlers[task_id] = comp_handler
        
        self.logger.log_workflow_status(workflow.id, "parsed", {"task_count": len(workflow.tasks)})
        
        return workflow
    
    def validate_dag(self, workflow) -> bool:
        """
        Validate that the workflow forms a valid DAG (no cycles)
        """
        from networkx import DiGraph, has_path
        import networkx as nx
        
        graph = DiGraph()
        
        # Add all tasks as nodes
        for task in workflow.tasks:
            graph.add_node(task.id)
        
        # Add dependency edges
        for task in workflow.tasks:
            for dependency in task.depends_on:
                if dependency not in [t.id for t in workflow.tasks]:
                    raise ValueError(f"Dependency '{dependency}' not found in workflow tasks")
                graph.add_edge(dependency, task.id)
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("Workflow contains circular dependencies")
        
        return True