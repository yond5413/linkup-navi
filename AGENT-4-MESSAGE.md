# Agent 4 Briefing Guide

## Quick Summary

All of Agents 1, 2, 3 are now integrated and pushed to `agent-refactor` branch.

---

## Key Information for Agent 4

### Branch

```
agent-refactor
```

### Main Entry Points

```python
# Option A: Use UnifiedAgent (recommended)
from app import create_unified_agent
agent = create_unified_agent()
result = await agent.run_full("user request")

# Option B: Use AgentOrchestrator with mode="full"
from app.core.orchestrator import AgentOrchestrator
orchestrator = AgentOrchestrator()
result = await orchestrator.run(command="request", mode="full")

# Option C: Import individual components
from app import TaskRouter, ContentStore, EmailProcessor, FactChecker
```

### Available Components

| Component | Import From | Purpose |
|-----------|-------------|---------|
| `TaskRouter` | `app.core.intent_router` | Decompose user intent into tasks |
| `MemoryAwarePlanner` | `app.core.memory_planner` | Create plans with context |
| `DurableExecutor` | `app.core.durable_executor` | Execute with checkpointing |
| `ContentStore` | `app.services.content_store` | Store/query content |
| `EmailProcessor` | `app.services.email_processor` | Parse emails |
| `ReplyGenerator` | `app.services.reply_generator` | Generate replies |
| `FactChecker` | `app.core.fact_checker` | Verify claims |
| `UnifiedAgent` | `app` or `app.agents` | Combined workflow |
| `EmailAgent` | `app` or `app.agents` | Email-focused workflow |

### Test Command

```bash
cd backend && python -c "from app import create_unified_agent; print('Agent 4 ready!')"
```

---

## Files Agent 4 Should Review

```
backend/app/agents/unified_agent.py    # Main combined workflow
backend/app/core/orchestrator.py      # Updated with mode="full"
backend/app/__init__.py               # Clean export hierarchy
backend/app/core/intent_router.py     # Task decomposition
backend/app/core/memory_planner.py    # Planning
backend/app/services/content_store.py  # Content storage
```

---

## What Agent 4 Should Focus On

Based on the SPRINT.md, Agent 4 handles:

- ✅ **Resource Profiler** - Check system resources (RAM, CPU, GPU, Ollama)
- ✅ **Adaptive LLM Router** - Route tasks to appropriate LLM (local vs cloud)
- ✅ **Final Integration** - Orchestrate everything with `mode="full"`

### Integration Points

- All Agent 1, 2, 3 files are import-ready from `app`
- `UnifiedAgent` provides the main workflow Agent 4 can extend
- `AgentOrchestrator` already supports `mode="full"`

---

## One Important Note

The `create_content_store()` function was added to `content_store.py`. Agent 4 should use it instead of direct instantiation:

```python
# ✅ Correct
from app import create_content_store
store = create_content_store()

# ❌ Avoid
from app.services.content_store import ContentStore
store = ContentStore()  # May fail without vector service
```

---

## Summary for Agent 4

> "All agents 1, 2, 3 are integrated in the `agent-refactor` branch. Use `from app import ...` for clean imports. The `UnifiedAgent` combines everything and is ready to use. Check `backend/app/agents/unified_agent.py` for the main workflow. Run `python -c 'from app import create_unified_agent'` to verify setup."

---

## Quick Verification Checklist

- [ ] Clone/pull `agent-refactor` branch
- [ ] Run: `cd backend && python -c "from app import create_unified_agent; print('Ready!')"`
- [ ] Review `backend/app/agents/unified_agent.py`
- [ ] Review `backend/app/core/orchestrator.py` (note `mode="full"`)
- [ ] Begin Agent 4 implementation

---

## File Changes Summary

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/agents/__init__.py` | 15 | Agents directory exports |
| `backend/app/agents/unified_agent.py` | 180 | Combines IntentRouter + MemoryPlanner + DurableExecutor + Agent 3 tools |
| `backend/app/agents/email_agent.py` | 140 | Combines EmailProcessor + ReplyGenerator + FactChecker |

### Files Updated

| File | Changes |
|------|---------|
| `backend/app/__init__.py` | Full export hierarchy for all agents |
| `backend/app/core/__init__.py` | Agent 2 + FactChecker exports |
| `backend/app/core/orchestrator.py` | Added `mode="full"` using UnifiedAgent |
| `backend/app/services/content_store.py` | Added `create_content_store()` factory |
| `backend/app/services/email_processor.py` | Added ContentStore integration |
| `backend/app/services/reply_generator.py` | Added ContentStore integration |
| `backend/app/core/fact_checker.py` | Added ContentStore integration |

### Git Status

```
✓ Committed: feat: integrate agents 1,2,3 with unified agent layer
✓ Pushed: agent-refactor branch
✓ Remote: https://github.com/yond5413/linkup-navi/pull/new/agent-refactor
```
