
---

## Target Verticals & Implementation

### Vertical 1 — Deal / Strategy / Meeting Prep (Primary MVP)

**Users:** VC analysts, strategy consultants, business ops, founders  
**Tasks:**
- Meeting preparation
- Agenda summarization
- Entity/company research via Linkup
- Briefing generation

**MVP Implementation:**
- Next.js frontend for command input + file upload
- FastAPI backend: context resolver, planner, executor
- Ollama Qwen 2.5 for planning & summarization
- Linkup API for web-based research

**Demo Command:**  
> “Prepare me for tomorrow’s meeting with Acme Corp using agenda.pdf”

**Output:**  
- Agenda summary  
- Key deadlines & risks  
- Linkup research snippet  
- Actionable briefing

---

### Vertical 2 — Legal / Compliance Ops (Optional)

**Users:** In-house legal, compliance teams, contract managers  
**Tasks:**
- Contract summarization
- Deadline & obligation extraction
- Optional verification / flagging unknown references

**MVP Implementation:**
- Text-based PDF upload
- Ollama Qwen prompt specialized for contracts
- FastAPI extracts structured JSON of obligations / deadlines

**Demo Command:**  
> “Summarize this contract and flag all deadlines and obligations”

**Output:**  
- Table of obligations  
- Key deadlines  
- Risk notes (“Unknown party reference”)  

**Notes:** Skip OCR for hackathon; hardcode sample contracts.

---

### Vertical 3 — Technical Product / Program Managers (Optional)

**Users:** PMs, TPMs, program leads  
**Tasks:**
- Meeting notes → task/action extraction
- PRD summarization
- Context-aware follow-ups combining docs & emails

**MVP Implementation:**
- Text file upload / paste notes
- FastAPI + Ollama Qwen converts to structured tasks
- Output readable summary + tasks table

**Demo Command:**  
> “Summarize last week’s engineering meeting notes and create task list”

**Output:**  
- Actionable tasks table  
- Summary paragraph  
- Optional context notes

---

## Implementation Notes & MVP Tips

- **File Handling:** Only explicit references from user commands (`agenda.pdf`, etc.)  
- **Memory:** Session-scoped; optional long-term memory for future work  
- **OCR:** Not required for MVP; mention as future extension  
- **Privacy:** All local files and Ollama inference run locally; Linkup only queried with explicit entities  
- **Judge-Friendly:** Focus on reasoning, planning, and synthesis — not UI polish

---

## Suggested Hackathon Stack

| Component | Choice | Notes |
|-----------|--------|------|
| Frontend | Next.js | Input, file upload, output display |
| Backend | FastAPI | Context resolution, planner, executor |
| LLM | Ollama (Qwen 2.5 7B Instruct) | Planner + summarization |
| Knowledge | Linkup API | Entity research, fact checking, web knowledge |
| Memory | Session-scoped in FastAPI | Optional long-term embeddings |
| PDF Parsing | pdfplumber / PyPDF | OCR optional, future work |

---

## MVP Strategy

1. Focus on **Vertical 1** for demo (meeting prep + briefing)  
2. Optional slices (Verticals 2 & 3) can be shown as “future work”  
3. Hardcode 1–2 sample files per vertical to reduce risk  
4. Skip OCR and advanced integrations for speed  
5. Demonstrate planner → executor → Linkup → output clearly

---

## Demo Flow (Vertical 1 Example)

1. User uploads `agenda.pdf` and types:  
   > “Prepare me for tomorrow’s meeting with Acme Corp”

2. FastAPI context loader reads PDF + session memory

3. Planner (Qwen via Ollama) decomposes goal:  
   - Summarize PDF  
   - Check if Linkup is needed → true for Acme Corp  
   - Plan structured execution

4. Linkup API is called for company research

5. Tool executor synthesizes summary + briefing

6. Output returned to frontend in JSON + human-readable format

---
using qwen2.5:0.5b
**End of README.md**
