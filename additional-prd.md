# AGI-Inspired Desktop Intelligence Agent

## Product Requirements Document (PRD)

### Overview

This project demonstrates a **privacy-first, AGI-inspired desktop intelligence agent** capable of:

* Multi-domain reasoning (emails, documents, meetings)
* Context awareness and memory
* Autonomous task planning and execution
* Knowledge transfer across tasks
* Adaptive behavior based on user interaction

> **Note:** This is not true AGI. The goal is to simulate general intelligence behaviors using current AI technologies.

---

### Hackathon Architecture

#### Conceptual AGI-Inspired Architecture

```
┌──────────────────────────────────────────────┐
│ User (Natural Language Goals)                │
│ “Prepare me for tomorrow’s meeting”          │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Context & Reference Resolver                 │
│ - Resolves “this doc”, “that email”         │
│ - Tracks session artifacts                   │
│ - Maintains short-term context               │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Planner / Reasoner (Local LLM)              │
│ - Intent inference                           │
│ - Goal decomposition                         │
│ - Decides if external knowledge is required  │
│ - Outputs structured execution plan (JSON)  │
└───────────────┬───────────────┬──────────────┘
                │               │
┌───────────────▼──────────┐ ┌──▼────────────────┐
│ Tool Executor             │ │ Knowledge Agent   │
│ (Local Actions)           │ │ (Linkup API)      │
│ - Document analysis        │ │ - Query creation │
│ - Email / calendar ops     │ │ - Multi-hop search│
│ - File system access       │ │ - Fact checking  │
└───────────────┬──────────┘ └───────┬──────────┘
                │                    │
                └──────────────┬─────┘
                               │
┌──────────────────────────────▼────────────────┐
│ Evaluator / Self-Critic                        │
│ - Verifies goal completion                     │
│ - Handles partial failures                     │
│ - Adjusts or retries plan                      │
└───────────────────┬────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────┐
│ Memory (Local-First)                           │
│ - Session memory                               │
│ - Optional long-term preferences               │
│ - Embeddings + structured facts                │
└────────────────────────────────────────────────┘
```

#### Hackathon MVP Architecture

```
┌──────────────────────────────────────────────┐
│ Next.js Web Interface                        │
│ - Natural language command                   │
│ - Local file upload (PDF, DOCX)              │
│ - Displays plan, reasoning, and output       │
└───────────────────┬──────────────────────────┘
                    │ HTTP (JSON)
┌───────────────────▼──────────────────────────┐
│ FastAPI Agent Runtime                        │
│ - Context resolution                         │
│ - Session-scoped memory                      │
│ - Planner & executor logic                   │
│  ┌────────────────────────────────────────┐  │
│  │ Planner (Qwen 2.5 via Ollama)          │  │
│  │ - Intent inference                       │  │
│  │ - Step planning (JSON)                   │  │
│  │ - Search decision                        │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │ Tool Execution                          │  │
│  │ - Document parsing (PDF)                │  │
│  │ - Summarization                         │  │
│  │ - Synthesis                             │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │ Knowledge Agent (Linkup API)            │  │
│  │ - Entity research                       │  │
│  │ - Fact verification                      │  │
│  │ - Recent company/news context           │  │
│  └────────────────────────────────────────┘  │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Ollama (Local Inference Engine)               │
│ - Qwen 2.5 Instruct                           │
│ - OpenAI-compatible API                       │
│ - Local-first privacy                         │
└──────────────────────────────────────────────┘
```

---

### Target Verticals & Implementation

#### Vertical 1 — Deal / Strategy / Meeting Prep (Primary MVP)

**Users:** VC analysts, strategy consultants, business ops, founders
**Tasks:**

* Meeting preparation
* Agenda summarization
* Entity/company research via Linkup
* Briefing generation
  **MVP Implementation:** Next.js + FastAPI + Ollama Qwen + Linkup API
  **Demo Command:** “Prepare me for tomorrow’s meeting with Acme Corp using agenda.pdf”
  **Output:** Agenda summary, deadlines, risks, research snippet, briefing

#### Vertical 2 — Legal / Compliance Ops (Optional)

**Users:** In-house legal, compliance teams, contract managers
**Tasks:**

* Contract summarization
* Deadline & obligation extraction
* Optional verification / flagging unknown references
  **MVP Implementation:** Text-based PDF upload, FastAPI + Qwen specialized prompts, structured JSON output
  **Demo Command:** “Summarize this contract and flag all deadlines and obligations”
  **Output:** Obligations table, deadlines, risk notes

#### Vertical 3 — Technical Product / Program Managers (Optional)

**Users:** PMs, TPMs, program leads
**Tasks:**

* Meeting notes → task/action extraction
* PRD summarization
* Context-aware follow-ups combining docs & emails
  **MVP Implementation:** Text file upload, FastAPI + Ollama Qwen, structured tasks output
  **Demo Command:** “Summarize last week’s engineering meeting notes and create task list”
  **Output:** Tasks table, summary paragraph, optional context notes

---

### Implementation Notes & MVP Tips

* File Handling: Only explicit references from user commands (`agenda.pdf`, etc.)
* Memory: Session-scoped; optional long-term memory for future work
* OCR: Not required for MVP; mention as future extension
* Privacy: Local files & Ollama inference local; Linkup only queried with explicit entities
* Focus: Reasoning, planning, and synthesis, not UI polish

### Suggested Hackathon Stack

| Component   | Choice                        | Notes                                         |
| ----------- | ----------------------------- | --------------------------------------------- |
| Frontend    | Next.js                       | Input, file upload, output display            |
| Backend     | FastAPI                       | Context resolution, planner, executor         |
| LLM         | Ollama (Qwen 2.5 7B Instruct) | Planner + summarization                       |
| Knowledge   | Linkup API                    | Entity research, fact checking, web knowledge |
| Memory      | Session-scoped in FastAPI     | Optional long-term embeddings                 |
| PDF Parsing | pdfplumber / PyPDF            | OCR optional, future work                     |

### MVP Strategy

1. Focus on Vertical 1 for demo
2. Optional slices (Verticals 2 & 3) for future work
3. Hardcode 1–2 sample files per vertical
4. Skip OCR for speed
5. Demonstrate planner → executor → Linkup → output clearly

### Demo Flow (Vertical 1 Example)

1. User uploads `agenda.pdf` + types command
2. FastAPI context loader reads PDF + session memory
3. Planner (Qwen via Ollama) decomposes goal + decides Linkup usage
4. Linkup API retrieves relevant info
5. Tool executor synthesizes briefing
6. Output returned to frontend in JSON + human-readable format

---

**End of PRD**
