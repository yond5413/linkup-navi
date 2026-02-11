# Linkup Navi PRD Alignment Sprint

## Sprint Overview

**Goal:** Full architectural alignment with `new-prd.md`  
**Duration:** 10 hours (4 parallel workstreams)  
**Branch Strategy:** Git Worktrees for parallel development  
**Data Policy:** Fresh migration acceptable (non-proprietary data)

---

## Git Worktrees Strategy

### Branch Structure

```
main (production)
├── feature/content-model (Agent 1 - Foundation)
├── feature/intent-router (Agent 2 - Core Intelligence)  
├── feature/domain-pipelines (Agent 3 - Domain Features)
└── feature/adaptive-routing (Agent 4 - Integration)
```

### Setup Commands

```bash
# Commit current work first
git add -A && git commit -m "chore: agent-native refactor phase 1"

# Create worktrees for parallel work
git worktree add ../linkup-navi-content-model feature/content-model
git worktree add ../linkup-navi-intent-router feature/intent-router
git worktree add ../linkup-navi-domain feature/domain-pipelines
git worktree add ../linkup-navi-adaptive feature/adaptive-routing

# Each agent works in their respective directory
# ../linkup-navi-content-model
# ../linkup-navi-intent-router
# ../linkup-navi-domain
# ../linkup-navi-adaptive
```

### Merge Strategy

```bash
# Phase 1: Merge feature branches sequentially (1 → 2 → 3 → 4)
git checkout feature/intent-router
git merge feature/content-model --no-ff -m "merge: content-model into intent-router"

git checkout feature/domain-pipelines
git merge feature/intent-router --no-ff -m "merge: intent-router into domain-pipelines"

git checkout feature/adaptive-routing  
git merge feature/domain-pipelines --no-ff -m "merge: domain-pipelines into adaptive-routing"

# Phase 2: Final merge to main
git checkout main
git merge feature/adaptive-routing --no-ff -m "feat: complete PRD alignment"
```

---

## Workstream Assignments

### AGENT 1: Foundation & Data (2.5 hours)
**Directory:** `../linkup-navi-content-model`  
**Focus:** ContentItem model and ContentStore service

#### Task 1.1: ContentItem Model (30 min)
**File:** `backend/app/models/content_item.py`

```python
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class SourceType(Enum):
    PDF = "pdf"
    EMAIL = "email"
    MESSAGE = "message"
    RESEARCH = "research"
    NOTE = "note"

class ContentItem(BaseModel):
    id: str
    source_type: SourceType
    title: str
    content: str
    metadata: Dict[str, Any]
    file_path: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    thread_id: Optional[str] = None
    embedded_at: Optional[datetime] = None
    embedding_id: Optional[int] = None
```

**Deliverable:** ContentItem model with SourceType enum

---

#### Task 1.2: ContentStore Service (1 hour)
**File:** `backend/app/services/content_store.py`

```python
from typing import List, Optional
from app.models.content_item import ContentItem, SourceType
from app.services.vector_memory import get_vector_memory_service

class ContentStore:
    async def add_pdf(self, file_path: str, content: str) -> ContentItem:
        """Add PDF content to store."""
    
    async def add_email(self, subject: str, sender: str, body: str) -> ContentItem:
        """Add email content to store."""
    
    async def add_research(self, query: str, result: dict) -> ContentItem:
        """Add research result to store."""
    
    async def add_note(self, title: str, content: str) -> ContentItem:
        """Add note to store."""
    
    async def query_by_source(self, source_type: SourceType) -> List[ContentItem]:
        """Query content by source type."""
    
    async def query_by_thread(self, thread_id: str) -> List[ContentItem]:
        """Get all messages in a thread."""
    
    async def query_semantic(self, query: str, top_k: int = 5) -> List[ContentItem]:
        """Semantic search across all content."""
    
    async def get_by_id(self, item_id: str) -> Optional[ContentItem]:
        """Get content item by ID."""
```

**Integrations:**
- Vector memory service (for auto-embedding)
- SQLite (for metadata persistence)

**Deliverable:** ContentStore with all CRUD operations

---

#### Task 1.3: Database Schema & Migration (1 hour)
**Files:** 
- `backend/app/db/schema.py` (update)
- `backend/app/db/migrate_content.py` (new)

**Schema Update:**
```python
@dataclass
class ContentItemModel:
    id: str
    source_type: str
    title: str
    content: str
    metadata: str  # JSON string
    file_path: Optional[str]
    sender: Optional[str]
    recipients: Optional[str]  # JSON list
    timestamp: Optional[str]
    thread_id: Optional[str]
    embedded_at: Optional[str]
    embedding_id: Optional[int]
```

**Migration Script:**
```python
async def migrate_to_content_items():
    """Migrate existing session_files to content_items table."""
    # Read all session files
    # Convert each to ContentItem
    # Insert into content_items table
    # Update imports in other modules
```

**Deliverable:** 
- Updated schema with content_items table
- Working migration script
- Backward compatibility

---

### AGENT 2: Core Intelligence (3 hours)
**Directory:** `../linkup-navi-intent-router`  
**Focus:** Intent routing, memory-aware planning, durable execution

#### Task 2.1: Intent-Aware Task Router (1 hour)
**File:** `backend/app/core/intent_router.py`

```python
from enum import Enum
from typing import List, Dict, Any
from pydantic import BaseModel

class TaskType(Enum):
    FIND_EMAIL = "find_email"
    FIND_DOCUMENT = "find_document"
    EXTRACT_CONTEXT = "extract_context"
    EXTRACT_DEADLINES = "extract_deadlines"
    EXTRACT_ACTIONS = "extract_actions"
    MATCH_TONE = "match_tone"
    DRAFT_REPLY = "draft_reply"
    RESEARCH_ENTITY = "research_entity"
    SYNTHESIZE = "synthesize"
    VERIFY_CLAIM = "verify_claim"

class Task(BaseModel):
    task_type: TaskType
    target: str  # What to search for
    parameters: Dict[str, Any] = {}

class TaskRouter:
    async def decompose_intent(self, user_input: str) -> List[Task]:
        """
        Dynamic task decomposition based on user intent.
        
        Example: "Draft reply to investor email about funding"
        → [FIND_EMAIL("investor email"), EXTRACT_CONTEXT("funding discussion"), 
           MATCH_TONE("investor@vc.com"), DRAFT_REPLY("funding update")]
        """
```

**Integrations:**
- LLMClient for intent parsing
- ContentStore for context queries

**Deliverable:** TaskRouter with dynamic decomposition

---

#### Task 2.2: Memory-Aware Planner (1 hour)
**File:** `backend/app/core/memory_planner.py`

```python
from typing import List, Dict, Any
from pydantic import BaseModel
from app.core.intent_router import Task

class ExecutionPlan(BaseModel):
    tasks: List[Task]
    gaps_identified: List[str]
    research_needed: List[str]
    context_from_memory: Dict[str, Any]

class MemoryAwarePlanner:
    async def create_plan(
        self, 
        goal: str, 
        tasks: List[Task],
        session_id: str
    ) -> ExecutionPlan:
        """
        Create plan with context from memory.
        
        1. Query FAISS for related content
        2. Identify gaps in available context
        3. Determine research needs
        4. Build execution plan with context
        """
```

**Integrations:**
- ContentStore for context retrieval
- TaskRouter for task definitions

**Deliverable:** MemoryPlanner with gap analysis

---

#### Task 2.3: Durable Executor (1 hour)
**File:** `backend/app/core/durable_executor.py`

```python
from typing import Any, Dict
from app.core.memory_planner import ExecutionPlan

class Checkpoint:
    task_index: int
    task_result: Dict[str, Any]
    timestamp: str

class DurableExecutor:
    async def execute_with_recovery(
        self,
        plan: ExecutionPlan,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute plan with checkpointing and recovery.
        
        1. Check for existing checkpoint
        2. If checkpoint exists, resume from there
        3. Execute each task, saving checkpoint after each
        4. On crash, resume from last checkpoint
        5. Return consolidated results
        """
    
    async def checkpoint(self, session_id: str, task_index: int, result: Any):
        """Save checkpoint to SQLite."""
    
    async def get_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """Get latest checkpoint for session."""
```

**Integrations:**
- SQLite for checkpoint storage
- TaskRouter for task execution

**Deliverable:** DurableExecutor with crash recovery

---

### AGENT 3: Domain Pipelines (2.5 hours)
**Directory:** `../linkup-navi-domain`  
**Focus:** Email processing, fact checking

#### Task 3.1: Email Processor (1 hour)
**File:** `backend/app/services/email_processor.py`

```python
from typing import List, Dict, Any, Optional
from app.models.content_item import ContentItem
from app.services.content_store import ContentStore

class EmailProcessor:
    async def parse_eml(self, file_path: str) -> ContentItem:
        """Parse .eml file and extract content."""
        # Extract headers: to, from, subject, date, message-id, in-reply-to
        # Extract body (plain text and HTML)
        # Detect thread from References/In-Reply-To headers
    
    async def extract_action_items(self, content: str) -> List[str]:
        """Extract action items from email body."""
    
    async def query_thread(
        self, 
        content_store: ContentStore, 
        thread_id: str
    ) -> List[ContentItem]:
        """Get all emails in a thread."""
    
    async def get_tone_examples(
        self,
        content_store: ContentStore,
        sender_email: str,
        limit: int = 5
    ) -> List[ContentItem]:
        """Get previous emails from sender for tone matching."""
```

**Integrations:**
- ContentStore for thread retrieval
- Vector memory for tone search

**Deliverable:** EmailProcessor with thread reconstruction

---

#### Task 3.2: Reply Generator with Tone (45 min)
**File:** `backend/app/services/reply_generator.py`

```python
from typing import Dict, Any
from app.models.content_item import ContentItem

class ReplyGenerator:
    async def generate_reply(
        self,
        original_email: ContentItem,
        tone_examples: List[ContentItem],
        user_intent: str,
        action_items: List[str]
    ) -> Dict[str, Any]:
        """
        Generate reply matching sender's tone.
        
        1. Build prompt with original email, tone examples, action items
        2. Generate draft
        3. Evaluate tone match score
        4. If score < 0.7, regenerate with stronger tone guidance
        5. Return draft + confidence score
        """
    
    def _evaluate_tone_match(self, draft: str, examples: List[str]) -> float:
        """Evaluate how well draft matches tone."""
```

**Integrations:**
- LLMClient for generation
- EmailProcessor for context

**Deliverable:** ReplyGenerator with tone scoring

---

#### Task 3.3: Fact Checker (45 min)
**File:** `backend/app/core/fact_checker.py`

```python
from typing import List, Dict, Any
from pydantic import BaseModel

class FactClaim(BaseModel):
    claim: str
    is_verified: bool
    confidence: float
    sources: List[str]
    evidence_summary: str

class FactChecker:
    async def verify_claim(
        self,
        claim: str,
        sources: List[Dict[str, Any]]
    ) -> FactClaim:
        """
        Verify a claim against sources.
        
        1. Decompose claim into atomic facts
        2. Search each fact in Linkup
        3. Search each fact in local docs
        4. Cross-reference findings
        5. Assess evidence strength
        6. Return verdict: Supported/Contradicted/Unverified
        """
    
    async def verify_report(
        self,
        user_claim: str,
        linkup_results: Dict[str, Any],
        local_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate full verification report."""
```

**Integrations:**
- LinkupClient for web search
- ContentStore for local docs

**Deliverable:** FactChecker with verification reports

---

### AGENT 4: Adaptive Routing & Integration (2 hours)
**Directory:** `../linkup-navi-adaptive`  
**Focus:** Smart LLM routing, final integration

#### Task 4.1: Resource Profiler (30 min)
**File:** `backend/app/core/resource_profiler.py`

```python
from dataclasses import dataclass
import psutil

@dataclass
class ResourceProfile:
    available_ram_gb: float
    cpu_percent: float
    gpu_available: bool
    ollama_healthy: bool
    ollama_models: List[str]

class ResourceProfiler:
    async def get_profile(self) -> ResourceProfile:
        """
        Check system resources.
        
        - Available RAM
        - CPU load
        - GPU availability (NVIDIA CUDA check)
        - Ollama health (is local LLM running?)
        - Available Ollama models
        """
    
    def estimate_task_complexity(self, task_type: str) -> str:
        """Estimate task complexity: simple/medium/complex."""
```

**Deliverable:** ResourceProfiler with system checks

---

#### Task 4.2: Adaptive LLM Router (45 min)
**File:** `backend/app/services/llm_router.py`

```python
from enum import Enum
from typing import Any, Dict
from app.core.resource_profiler import ResourceProfile

class ModelTier(Enum):
    LOCAL_FAST = "ollama:0.5b"      # Simple extraction
    LOCAL_QUALITY = "ollama:3b"     # Medium tasks
    LOCAL_COMPLEX = "ollama:7b"      # Complex reasoning
    CLOUD_FAST = "openrouter:flash"  # Cheap cloud
    CLOUD_QUALITY = "openrouter:pro" # High quality
    CLOUD_BEST = "openrouter:claude" # Best quality

class LLMRouter:
    async def route(
        self,
        task_type: str,
        profile: ResourceProfile,
        user_tier: str = "free"
    ) -> ModelTier:
        """
        Route task to appropriate LLM.
        
        Decision tree:
        1. Can run local? → Check RAM, Ollama health
        2. Simple task → LOCAL_FAST
        3. Medium task → LOCAL_QUALITY  
        4. Complex task → LOCAL_COMPLEX or CLOUD_QUALITY
        5. Free tier → CLOUD_FAST
        6. Enterprise → CLOUD_BEST
        """
    
    async def execute(
        self,
        prompt: str,
        model: ModelTier,
        system_prompt: str = None
    ) -> Any:
        """Execute LLM call through appropriate client."""
    
    async def fallback(
        self,
        prompt: str,
        original_model: ModelTier,
        error: Exception
    ) -> Any:
        """Fallback to next tier on failure."""
```

**Integrations:**
- ResourceProfiler
- Existing LLMClient (Ollama, OpenRouter)

**Deliverable:** LLMRouter with smart routing

---

#### Task 4.3: Final Integration (45 min)
**File:** `backend/app/core/orchestrator.py` (major update)

**New Mode: "full"**

```python
class FullOrchestrator:
    async def run(
        self,
        user_input: str,
        session_id: str,
        files: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Full PRD-aligned execution flow:
        
        1. TaskRouter.decompose_intent() → List[Task]
        2. MemoryPlanner.create_plan() → ExecutionPlan
        3. DurableExecutor.execute() → Results
        4. Return unified response
        """
```

**Integration Points:**
- TaskRouter
- MemoryPlanner
- DurableExecutor
- EmailProcessor (if email detected)
- FactChecker (if claim detected)
- LLMRouter

**Deliverable:** Complete orchestrator with all new components

---

## Testing Requirements (Per Agent)

### Agent 1 Testing
```bash
# Test ContentItem model
python -c "
from app.models.content_item import ContentItem, SourceType
item = ContentItem(
    id='test-1',
    source_type=SourceType.PDF,
    title='Test PDF',
    content='...',
    metadata={}
)
print('ContentItem:', item)

# Test ContentStore
from app.services.content_store import ContentStore
store = ContentStore()
# Add content, query by source, query semantic
```

---

### Agent 2 Testing
```bash
# Test TaskRouter
python -c "
from app.core.intent_router import TaskRouter
router = TaskRouter()
tasks = await router.decompose_intent('Draft reply to investor about funding')
print('Tasks:', [t.task_type.value for t in tasks])
"

# Test MemoryPlanner
python -c "
from app.core.memory_planner import MemoryPlanner
planner = MemoryPlanner()
plan = await planner.create_plan('Prepare meeting', tasks, session_id)
print('Gaps:', plan.gaps_identified)
"

# Test DurableExecutor
python -c "
from app.core.durable_executor import DurableExecutor
executor = DurableExecutor()
# Execute plan with crash simulation
"
```

---

### Agent 3 Testing
```bash
# Test EmailProcessor
python -c "
from app.services.email_processor import EmailProcessor
processor = EmailProcessor()
item = await processor.parse_eml('test.eml')
print('Email:', item.sender, item.thread_id)
"

# Test ReplyGenerator
python -c "
from app.services.reply_generator import ReplyGenerator
generator = ReplyGenerator()
result = await generator.generate_reply(email, tone_examples, 'respond')
print('Tone score:', result.confidence)
"

# Test FactChecker
python -c "
from app.core.fact_checker import FactChecker
checker = FactChecker()
report = await checker.verify_report('Acme raised \$50M', linkup, local)
print('Verdict:', report.verdict)
"
```

---

### Agent 4 Testing
```bash
# Test ResourceProfiler
python -c "
from app.core.resource_profiler import ResourceProfiler
profile = await ResourceProfiler().get_profile()
print('RAM:', profile.available_ram_gb)
print('Ollama:', profile.ollama_healthy)
"

# Test LLMRouter
python -c "
from app.services.llm_router import LLMRouter
router = LLMRouter()
model = await router.route('extract_deadlines', profile)
print('Selected model:', model.value)

# Test full integration
python -c "
from app.core.orchestrator import AgentOrchestrator
orchestrator = AgentOrchestrator()
result = await orchestrator.run('Prepare for meeting', session_id, mode='full')
"
```

---

## Interface Contracts

### Contract 1: ContentStore ↔ All Components

```python
# backend/app/services/content_store.py
class ContentStore:
    async def add(item: ContentItem) -> str: ...
    async def get(id: str) -> Optional[ContentItem]: ...
    async def query_by_source(type: SourceType) -> List[ContentItem]: ...
    async def query_semantic(query: str, top_k: int) -> List[ContentItem]: ...
    async def query_thread(thread_id: str) -> List[ContentItem]: ...
    async def delete(id: str) -> bool: ...
```

---

### Contract 2: TaskRouter ↔ MemoryPlanner

```python
# backend/app/core/intent_router.py
class TaskRouter:
    async def decompose_intent(user_input: str) -> List[Task]: ...

# backend/app/core/memory_planner.py  
class MemoryPlanner:
    async def create_plan(
        goal: str,
        tasks: List[Task],
        session_id: str
    ) -> ExecutionPlan: ...
```

---

### Contract 3: MemoryPlanner ↔ DurableExecutor

```python
# backend/app/core/durable_executor.py
class DurableExecutor:
    async def execute(
        plan: ExecutionPlan,
        session_id: str
    ) -> Dict[str, Any]: ...
```

---

### Contract 4: LLMRouter ↔ All

```python
# backend/app/services/llm_router.py
class LLMRouter:
    async def route(
        task_type: str,
        profile: ResourceProfile,
        user_tier: str = "free"
    ) -> ModelTier: ...
    
    async def generate(
        prompt: str,
        model: ModelTier,
        system_prompt: str = None
    ) -> str: ...
```

---

## Merge Sequence

### Phase 1: Sequential Merges (within worktrees)

```bash
# Agent 1: Merge content-model into intent-router
cd ../linkup-navi-intent-router
git fetch ../linkup-navi-content-model
git merge feature/content-model --no-ff -m "merge: content-model into intent-router"

# Agent 2: Merge intent-router into domain-pipelines
cd ../linkup-navi-domain
git fetch ../linkup-navi-intent-router
git merge feature/intent-router --no-ff -m "merge: intent-router into domain-pipelines"

# Agent 3: Merge domain-pipelines into adaptive-routing
cd ../linkup-navi-adaptive
git fetch ../linkup-navi-domain
git merge feature/domain-pipelines --no-ff -m "merge: domain-pipelines into adaptive-routing"
```

### Phase 2: Final Merge to Main

```bash
cd /path/to/linkup-navi
git checkout main
git merge feature/adaptive-routing --no-ff -m "feat: complete PRD alignment"

# Clean up worktrees
git worktree remove ../linkup-navi-content-model
git worktree remove ../linkup-navi-intent-router
git worktree remove ../linkup-navi-domain
git worktree remove ../linkup-navi-adaptive

# Delete feature branches
git branch -D feature/content-model
git branch -D feature/intent-router
git branch -D feature/domain-pipelines
git branch -D feature/adaptive-routing
```

---

## Rollback Plan

If issues arise:

```bash
# Rollback to before sprint
git checkout main
git reset --hard HEAD@{1}

# Or rollback specific feature
git checkout feature/adaptive-routing
git reset --hard HEAD@{1}
# Fix issues, continue work
```

---

## Quick Reference Commands

```bash
# Setup
git add -A && git commit -m "chore: checkpoint before sprint"
git worktree add ../linkup-navi-content-model feature/content-model
git worktree add ../linkup-navi-intent-router feature/intent-router
git worktree add ../linkup-navi-domain feature/domain-pipelines
git worktree add ../linkup-navi-adaptive feature/adaptive-routing

# Daily sync (pull latest from main)
git checkout main && git pull
cd ../linkup-navi-content-model && git pull ../linkup-navi main
cd ../linkup-navi-intent-router && git pull ../linkup-navi main
# ... etc

# Final merge
cd ../linkup-navi-adaptive
git merge feature/content-model
git merge feature/intent-router
git merge feature/domain-pipelines
git checkout main && git merge feature/adaptive-routing

# Cleanup
git worktree remove ../linkup-navi-content-model
git worktree remove ../linkup-navi-intent-router
git worktree remove ../linkup-navi-domain
git worktree remove ../linkup-navi-adaptive
```

---

## Definition of Done

Each agent must deliver:

- [ ] Code implemented in assigned files
- [ ] All tests pass (see Testing Requirements above)
- [ ] Type checking passes (`python -m py_compile`)
- [ ] No new linting errors
- [ ] Integration test with dependent components
- [ ] Documentation (docstrings for all public methods)
- [ ] Ready for merge (no conflicts)

---

## Timeline

| Hour | Agent 1 | Agent 2 | Agent 3 | Agent 4 |
|------|---------|---------|---------|---------|
| 0-0.5 | ContentItem model | IntentRouter | EmailProcessor | ResourceProfiler |
| 0.5-1.5 | ContentStore | MemoryPlanner | ReplyGenerator | LLMRouter |
| 1.5-2.5 | DB Schema + Migration | DurableExecutor | FactChecker | Integration |
| 2.5-3 | Testing | Testing | Testing | Final Merge |

---

## Success Criteria

- [ ] All 4 workstreams complete
- [ ] Cross-domain queries work ("What did Acme say in emails about funding?")
- [ ] Durable execution survives crash mid-task
- [ ] Email tone matching generates consistent replies
- [ ] Fact checker verifies claims with sources
- [ ] Adaptive routing selects appropriate LLM
- [ ] All tests pass
- [ ] Code merged to main
