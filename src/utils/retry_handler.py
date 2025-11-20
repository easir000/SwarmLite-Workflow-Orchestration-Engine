import asyncio
import random
from typing import Callable, Any, Optional
from .logger import WorkflowLogger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RetryHandler:
    def __init__(self, max_attempts: int = 3, delay_seconds: int = 2, exponential_backoff: bool = True):
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds
        self.exponential_backoff = exponential_backoff
        self.logger = WorkflowLogger()
    
    async def execute_with_retry(self, func: Callable, workflow_id: str, task_id: str, *args, **kwargs) -> Any:
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                return result
            except Exception as e:
                last_exception = e
                # Simplified error logging - no context parameter that might have 'data'
                self.logger.log_error(
                    workflow_id, 
                    task_id, 
                    str(e)
                    # Removed context parameter to avoid potential variable conflicts
                )
                
                if attempt < self.max_attempts - 1:
                    # Calculate delay with exponential backoff
                    delay = self.delay_seconds * (2 ** attempt) if self.exponential_backoff else self.delay_seconds
                    # Add jitter to prevent thundering herd
                    delay += random.uniform(0, 1)
                    
                    await asyncio.sleep(delay)
        
        raise last_exception

    def execute_compensation(self, compensation_func: Callable, *args, **kwargs):
        """Execute compensation function without retry logic"""
        try:
            if asyncio.iscoroutinefunction(compensation_func):
                return asyncio.run(compensation_func(*args, **kwargs))
            else:
                return compensation_func(*args, **kwargs)
        except Exception as e:
            self.logger.log_error("compensation", "compensation", str(e))
            raise e