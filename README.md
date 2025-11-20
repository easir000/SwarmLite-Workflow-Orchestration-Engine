# SwarmLite Workflow Orchestration Engine

A lightweight, fault-tolerant workflow orchestration system designed for event-driven, stateful pipelines with audit-grade principles and enterprise compliance.

## 🛡️ Governance & Compliance by Easir Maruf

This engine enforces the **personal AI governance policy** of Easir Maruf, shaped by 13+ years of delivering compliant AI systems in healthcare, legal tech, and government environments under HIPAA, GDPR, ISO 27001, and BD DPA.

All policies are codified in `config/governance.yaml` and enforced at runtime. Key features:

- ✅ PHI/PII masking and encryption
- ✅ LLM model whitelisting and prompt injection blocking
- ✅ Mandatory idempotency for critical operations
- ✅ Automated human review triggers for low-confidence outputs
- ✅ Immutable audit trails with HMAC signatures
- ✅ API request header validation for partner system onboarding
- ✅ Environment-based configuration management with `.env` file support

This is not theoretical compliance — it is **operationalized governance**.

> *"Compliance is not a checkbox. It's a design principle." — Easir Maruf*

## Architecture Overview

SwarmLite follows a modular, event-driven architecture with the following key components:

### Core Components

- **Workflow Parser (`src/orchestrator/parser.py`)**: Parses YAML/JSON workflow definitions and validates DAG structure using NetworkX
- **State Manager (`src/orchestrator/state_manager.py`)**: Persists workflow and task state in SQLite/PostgreSQL with encryption and HMAC signatures
- **Task Executor (`src/orchestrator/task_executor.py`)**: Executes individual tasks with retry and rollback capabilities
- **Workflow Engine (`src/orchestrator/engine.py`)**: Orchestrates task execution based on dependency graphs with topological sorting
- **Governance Engine (`src/orchestrator/governance.py`)**: Enforces AI governance policies at runtime based on `config/governance.yaml`
- **API Layer (`src/api/main.py`)**: REST API for workflow management using FastAPI with required headers validation
- **Configuration Manager (`src/config/config.py`)**: Centralized environment variable management with validation

### Data Models

- **Workflow (`src/models/workflow.py`)**: Represents a complete workflow with tasks, status, retry policy, and compensation handlers
- **Task**: Individual workflow step with type, dependencies, configuration, and data classification
- **WorkflowState**: Persistent state transitions with timestamp, signature, and details

### Utilities

- **Logger (`src/utils/logger.py`)**: Structured logging with PHI/PII masking using structlog
- **Retry Handler (`src/utils/retry_handler.py`)**: Automatic retry with exponential backoff and compensation logic

### Architecture Flow

1. **Parse**: Workflow definition → YAML/JSON → Workflow object
2. **Validate**: Governance rules → DAG validation → Dependency resolution
3. **Execute**: Task execution → State persistence → Retry logic
4. **Monitor**: Real-time status → Audit trail → Compensation on failure

## Assumptions Made

### Security & Compliance
- For demonstration purposes, the system assumes trusted workflow definitions
- Data classification (PHI/PII/Public) is specified in workflow definitions
- Encryption keys are stored in environment variables via `.env` file
- API keys and secrets are managed externally through environment variables

### Scalability & Performance
- Single-node execution suitable for small to medium workloads (up to 20 concurrent workflows)
- SQLite database for simplicity; can be extended to PostgreSQL for production
- Tasks run in the same process space for this prototype
- In-memory task execution with persistent state

### Dependencies & External Services
- HTTP tasks assume reliable external endpoints (simulated in this prototype)
- LLM tasks require OpenAI API key via environment variables or will simulate responses
- Database operations are simulated for demonstration
- Network connectivity is available for HTTP tasks

### Governance & Validation
- Governance policies are loaded from `config/governance.yaml` at startup
- Required headers (`X-Request-Source`, `X-Client-ID`) must be provided for API calls
- Compensation handlers are defined in workflow definitions but may not be implemented
- Prompt injection protection uses predefined banned phrases list

## How to Run Locally (with example workflow)

### Prerequisites
- Python 3.10+ 
- pip
- Git (optional, for cloning)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd swarm-lite

# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your actual API keys and configuration
notepad .env  # On Windows
# Or: nano .env  # On macOS/Linux
```

### Running the Application

#### 1. Run Directly (Simple Workflow)
```bash
python run.py
```

This executes the `examples/reliable_workflow.yaml` which includes:
- 4 tasks with dependencies: `initialize_data` → `process_data` → `validate_output` → `finalize_results`
- Python task types with function simulation
- Governance policy enforcement by Easir Maruf
- Environment-based configuration validation

#### 2. Run with API Server
```bash
# Terminal 1: Start API server
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/governance
curl http://localhost:8000/health/compliance
```

#### 3. Run Tests
```bash
python -m pytest tests/ -v
python -m pytest tests/ --disable-warnings  # To suppress SQLAlchemy warnings
```

### Example Workflow Definition

The system includes example workflows in the `examples/` directory:

**`examples/reliable_workflow.yaml`**:
```yaml
workflow_id: reliable_sample
tasks:
  - id: initialize_data
    type: python
    depends_on: []
    data_classification: "public"
    config:
      function: "validate_schema"
      params:
        initial_data: "ready"
  - id: process_data
    type: python
    depends_on: [initialize_data]
    data_classification: "public"
    config:
      function: "clean_dataframe"
      params:
        columns: ["id", "value", "status"]
  - id: validate_output
    type: python
    depends_on: [process_data]
    data_classification: "public"
    config:
      function: "validate_schema"
      params:
        required_columns: ["id", "value", "status"]
  - id: finalize_results
    type: python
    depends_on: [validate_output]
    data_classification: "public"
    config:
      function: "transform_data"
      params:
        output_format: "json"
retry_policy:
  max_attempts: 2
  delay_seconds: 1
  exponential_backoff: false
compensation_handlers:
  initialize_data: "rollback_initialize"
  process_data: "rollback_process"
  validate_output: "rollback_validate"
  finalize_results: "rollback_finalize"
```

### API Endpoints

| Endpoint | Method | Description | Required Headers |
|----------|--------|-------------|------------------|
| `/health` | GET | System health check | None |
| `/health/compliance` | GET | Compliance status | None |
| `/health/governance` | GET | Governance policy status | None |
| `/workflows/start` | POST | Start new workflow | `X-Request-Source`, `X-Client-ID` |
| `/workflows/{id}/status` | GET | Get workflow status | None |
| `/workflows/{id}/stop` | POST | Stop running workflow | None |

### Example API Usage

```bash
# Start a workflow
curl -X POST http://localhost:8000/workflows/start \
  -H "Content-Type: application/json" \
  -H "X-Request-Source: test" \
  -H "X-Client-ID: test-client" \
  -d '{
    "definition": "workflow_id: api_test\ntasks:\n  - id: task1\n    type: python\n    depends_on: []\n    config:\n      function: \"validate_schema\"\n  - id: task2\n    type: python\n    depends_on: [task1]\n    config:\n      function: \"clean_dataframe\""
  }'

# Check status
curl http://localhost:8000/workflows/api_test/status
```

## Fault-Handling Demo or Explanation

### Retry Logic with Exponential Backoff

The system implements automatic retry with configurable policies:

- **Max Attempts**: Configurable per workflow (default: 3)
- **Delay**: Initial delay with exponential backoff (default: 2 seconds)
- **Jitter**: Randomized delay to prevent thundering herd

**Example**: If a task fails on first attempt, it waits 2 seconds, then 4 seconds, then 8 seconds before giving up.

### Rollback/Compensation on Failure

When a task fails, the system attempts to execute compensation handlers:

1. **Identify Failed Tasks**: Tasks with `FAILED` status
2. **Identify Successful Tasks**: Tasks with `SUCCESS` status that depend on failed tasks
3. **Execute Compensation**: Run compensation handlers in reverse dependency order
4. **Update Status**: Mark tasks as `ROLLBACK`

**Example Compensation Handler**:
```yaml
compensation_handlers:
  fetch_data: "rollback_fetch_data"
  clean_data: "rollback_clean_data"
```

### Idempotency Protection

The system prevents duplicate execution through:

- **Idempotency Keys**: Optional keys provided with workflow start requests
- **State Checking**: Before executing a task, check if it's already completed
- **Persistent Tracking**: Completed task states stored in database

### State Persistence and Recovery

All workflow and task states are persisted:

- **SQLite Database**: `swarmlite.db` with encrypted fields
- **HMAC Signatures**: Immutable audit trail with SHA256 signatures
- **Recovery**: System can resume from any state after interruption

### Dependency Resolution and Fault Isolation

- **DAG Validation**: Prevents circular dependencies at parse time
- **Topological Sorting**: Executes tasks in dependency order
- **Fault Isolation**: Failed tasks don't prevent independent tasks from executing
- **State Tracking**: Completed tasks are not re-executed on retry

### Error Handling and Observability

- **Structured Logging**: All errors logged with context and timestamps
- **PHI/PII Masking**: Sensitive data automatically masked in logs
- **Health Checks**: API endpoints for compliance and governance status
- **Error Context**: Detailed error messages with attempt counts and dependencies

### Example Fault Scenario

1. **Workflow**: `A → B → C` (A depends on nothing, B on A, C on B)
2. **Failure**: Task B fails on all retry attempts
3. **Rollback**: Execute compensation handler for Task B
4. **Isolation**: Task A remains successful, Task C is not executed
5. **Status**: Workflow marked as `FAILED`, Task A = `SUCCESS`, Task B = `ROLLBACK`, Task C = `PENDING`

This fault-tolerant design ensures system reliability while maintaining data integrity and compliance requirements.

## Environment Configuration

### Required Environment Variables

The system uses a `.env` file for secure configuration management:

```env
# Database Configuration (32+ character keys)
DB_ENCRYPTION_KEY=your-32-byte-encryption-key-here-replace-with-actual-key
AUDIT_SECRET_KEY=your-32-byte-audit-signing-key-here-replace-with-actual-key

# API Keys (only set what you need)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_API_KEY=your-google-api-key-here

# Database URL (for production)
DATABASE_URL=sqlite:///swarmlite.db
# For PostgreSQL: postgresql://user:password@localhost/dbname

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=False

# Governance Configuration
GOVERNANCE_CONFIG_PATH=config/governance.yaml

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Configuration Validation

The system validates required environment variables on startup:
- `AUDIT_SECRET_KEY` (minimum 32 characters)
- `DB_ENCRYPTION_KEY` (minimum 32 characters, optional)
- All API keys are validated when used

### Security Best Practices

- **Never commit `.env` to version control**
- Use the `.env.example` file as template
- Store sensitive keys in environment variables
- Validate configuration on application startup

This environment-based configuration ensures secure, production-ready deployment with proper secret management.