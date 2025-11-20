import asyncio
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after other imports to avoid circular dependencies
from ..models.workflow import Task, TaskStatus, DataClassification
from ..utils.logger import WorkflowLogger
from ..utils.retry_handler import RetryHandler

class TaskExecutor:
    def __init__(self, retry_handler: RetryHandler):
        self.retry_handler = retry_handler
        self.logger = WorkflowLogger()
        # Register available task types
        self.task_handlers = {
            'http': self._execute_http_task,
            'python': self._execute_python_task,
            'database': self._execute_database_task,
            'llm': self._execute_llm_task,
            'rag': self._execute_rag_task,
            'custom': self._execute_custom_task
        }
    
    async def execute_task(self, workflow_id: str, task: Task) -> Task:
        """
        Execute a single task based on its type
        """
        start_time = datetime.now()
        
        try:
            self.logger.log_task_start(workflow_id, task.id, task.type, task.data_classification.value)
            
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = task.started_at or datetime.now()
            
            # Execute task based on type
            if task.type not in self.task_handlers:
                raise ValueError(f"Unknown task type: {task.type}")
            
            # Execute with retry logic
            result = await self.retry_handler.execute_with_retry(
                self.task_handlers[task.type],
                workflow_id,
                task.id,
                task.config
            )
            
            # Update task completion
            task.status = TaskStatus.SUCCESS
            task.completed_at = datetime.now()
            task.result = result
            # Increment retry_count by 1 for successful execution (first attempt)
            task.retry_count += 1
            duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000
            
            self.logger.log_task_end(workflow_id, task.id, "success", duration_ms, result)
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000 if task.started_at else 0
            
            self.logger.log_task_end(workflow_id, task.id, "failed", duration_ms, str(e))
            self.logger.log_error(workflow_id, task.id, str(e))
        
        return task
    
    async def _execute_python_task(self, config: Dict[str, Any]) -> Any:
        """
        Execute Python task - SAFE VERSION
        """
        # Get function name safely
        func_name = config.get('function', 'default_function')
        params = config.get('params', {})
        
        # Simulate different functions with safe parameter handling
        if func_name == 'clean_dataframe':
            await asyncio.sleep(0.01)
            return {
                "status": "cleaned", 
                "function": func_name,
                "records_processed": 1000,
                "params_used": list(params.keys()) if isinstance(params, dict) else str(type(params))
            }
        elif func_name == 'validate_schema':
            await asyncio.sleep(0.01)
            return {
                "status": "validated", 
                "function": func_name,
                "valid": True,
                "errors": [],
                "params_used": list(params.keys()) if isinstance(params, dict) else str(type(params))
            }
        elif func_name == 'transform_data':
            await asyncio.sleep(0.01)
            return {
                "status": "transformed", 
                "function": func_name,
                "output_size": 500,
                "params_used": list(params.keys()) if isinstance(params, dict) else str(type(params))
            }
        else:
            # Default case for any other function name
            await asyncio.sleep(0.01)
            return {
                "status": "executed",
                "function": func_name,
                "params_received": list(params.keys()) if isinstance(params, dict) else str(type(params))
            }
    
    async def _execute_http_task(self, config: Dict[str, Any]) -> Any:
        """
        Execute HTTP task - SAFE VERSION
        """
        url = config.get('url', 'https://httpbin.org/get')
        method = config.get('method', 'GET')
        await asyncio.sleep(0.01)
        return {
            "status": "http_executed",
            "url": url,
            "method": method
        }
    
    async def _execute_database_task(self, config: Dict[str, Any]) -> Any:
        await asyncio.sleep(0.01)
        return {"status": "database_executed", "config_keys": list(config.keys())}
    
    async def _execute_llm_task(self, config: Dict[str, Any]) -> Any:
        """
        Execute LLM task with safety checks
        """
        import os
        from dotenv import load_dotenv
        load_dotenv()  # Load env vars
        
        try:
            from openai import AsyncOpenAI
        except ImportError:
            # If OpenAI is not available, simulate
            await asyncio.sleep(0.2)
            return {"response": "Simulated LLM response", "confidence": 0.85}
        
        # Use environment variable for API key, fallback to config
        api_key = config.get("api_key", os.getenv("OPENAI_API_KEY"))
        if not api_key:
            raise ValueError("No API key provided for LLM task. Set OPENAI_API_KEY in environment or provide in config.")
        
        client = AsyncOpenAI(api_key=api_key)
        
        prompt = config["prompt"]
        model = config.get("model", "gpt-4-turbo")
        
        # Guardrail: Validate prompt length, disallow system prompt injection
        if len(prompt) > 2000:
            raise ValueError("Prompt exceeds 2000 characters for safety")
        
        # Check for banned phrases
        banned_prompts = ["ignore previous instructions", "pretend you're not an AI", "reveal system prompt"]
        for banned in banned_prompts:
            if banned.lower() in prompt.lower():
                raise ValueError(f"Prompt contains banned phrase: '{banned}'")
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        
        # Simulate confidence scoring (in real system, use embeddings)
        confidence = 0.85  # placeholder
        
        # If confidence is low, trigger human review
        if confidence < 0.75:
            result = "[REVIEW REQUIRED: LOW CONFIDENCE]"
        
        return result
    
    async def _execute_rag_task(self, config: Dict[str, Any]) -> Any:
        """
        Execute RAG task with retrieval and generation
        """
        # Simulate RAG process
        query = config.get("query", "")
        context = config.get("context", "Sample context for RAG")
        
        # In real system: retrieve from vector store, generate response
        await asyncio.sleep(0.2)  # Simulate retrieval and generation
        return {
            "query": query,
            "retrieved_context": context,
            "response": f"Answer to: {query}",
            "confidence": 0.88
        }
    
    async def _execute_custom_task(self, config: Dict[str, Any]) -> Any:
        """
        Execute custom task
        """
        # Placeholder for custom task execution
        await asyncio.sleep(0.1)
        return {"custom_task_completed": True}
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """
        Register a custom task handler
        """
        self.task_handlers[task_type] = handler