import yaml
import os
from datetime import datetime
from typing import Dict, Any
from ..models.workflow import Task, TaskType
from ..utils.logger import WorkflowLogger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GovernanceEngine:
    def __init__(self, config_path: str = None):
        config_path = config_path or os.getenv("GOVERNANCE_CONFIG_PATH", "config/governance.yaml")
        self.config = self._load_config(config_path)
        self.logger = WorkflowLogger()

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Governance config not found: {path}")
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def validate_workflow(self, workflow) -> bool:
        """Enforce governance rules before execution"""
        for task in workflow.tasks:
            # 1. Enforce data classification
            if task.data_classification.value == "phi" and not self.config["rules"]["phi_encryption_required"]:
                raise PermissionError("PHI data requires encryption — policy violation")

            # 2. Enforce LLM model whitelist
            if task.type == "llm" and task.config.get("model") not in self.config["rules"]["llm_allowed_models"]:
                raise ValueError(f"Model '{task.config['model']}' not allowed. Allowed: {self.config['rules']['llm_allowed_models']}")

            # 3. Enforce prompt safety
            if task.type in ["llm", "rag"] and "prompt" in task.config:
                for banned in self.config["rules"]["banned_prompts"]:
                    if banned.lower() in task.config["prompt"].lower():
                        raise ValueError(f"Prompt contains banned phrase: '{banned}'")

            # 4. Enforce idempotency for critical tasks
            if task.type in ["database_write", "external_api_call"] and not workflow.idempotency_key:
                raise ValueError(f"Idempotency key required for {task.type} tasks per governance policy")

        # 5. Validate required headers (if called via API)
        # (Assume this is checked at API layer via middleware)

        self.logger.log_governance_event(workflow.id, "workflow_validation_passed", {"task_count": len(workflow.tasks)})
        return True

    def should_trigger_human_review(self, task, confidence: float) -> bool:
        """Check if confidence falls below threshold for human review"""
        if task.type in ["llm", "rag"] and confidence < self.config["rules"]["hallucination_threshold"]:
            self.logger.log_governance_event(
                task.id,
                "human_review_triggered",
                {"confidence": confidence, "threshold": self.config["rules"]["hallucination_threshold"]}
            )
            return True
        return False

    def enforce_retention(self, workflow_id: str):
        """Simulate automatic cleanup after retention period"""
        # In production: integrate with cloud lifecycle policies
        # For demo: log compliance action
        retention_days = self.config["rules"]["max_data_retention_days"]
        self.logger.info(
            "retention_policy_enforced",
            workflow_id=workflow_id,
            retention_days=retention_days,
            action="scheduled_for_deletion"
        )