Linkup Navi: Multi-Domain Desktop Intelligence Agent
Architectural Specification v2.0
Vision: A privacy-first, AGI-inspired desktop agent that unifies documents, emails, messages, and research through semantic memory and intent-aware task routing.

flowchart TB
    subgraph UserLayer["👤 User Interface Layer"]
        UI[Electron Desktop App]
        QuickCapture[Global Quick Capture<br/>⌘⇧Space]
        SysTray[System Tray Menu]
    end

    subgraph APILayer["🔌 API Gateway Layer"]
        FastAPI[FastAPI Local Server<br/>localhost:8000]
        IPC[Electron IPC Bridge]
        Auth[Local Auth & Key Store]
    end

    subgraph CoreLayer["🧠 Core Intelligence Layer"]
        Router[Intent-Aware Task Router]
        Planner[Memory-Aware Planner]
        Executor[Durable Task Executor]
        Evaluator[Quality Evaluator]
    end

    subgraph MemoryLayer["💾 Unified Memory Layer"]
        FAISS[FAISS Vector Index<br/>Semantic Search]
        SQLite[(SQLite Metadata<br/>Content & Sessions)]
        ContentStore[Content Store<br/>PDFs | Emails | Research]
    end

    subgraph ToolLayer["🛠️ Tool Integration Layer"]
        PDF[PDF Processor]
        Email[Email Processor]
        Research[Linkup Research]
        LLM[LLM Router<br/>Local | Cloud]
    end

    subgraph External["☁️ External Services (Optional)"]
        Linkup[Linkup API]
        Cohere[Cohere Embeddings]
        OpenRouter[OpenRouter LLMs]
        Ollama[Ollama Local<br/>Fallback]
    end

    UI --> IPC --> FastAPI
    FastAPI --> Router
    Router --> Planner
    Planner --> Executor
    Executor --> ToolLayer

    Router -.->|Query| MemoryLayer
    Planner -.->|Retrieve Context| FAISS
    Executor -.->|Store Results| ContentStore

    ToolLayer --> External

    ContentStore --> FAISS
    FAISS --> SQLite


2. Content Unification Model
All content types normalized to ContentItem for memory integration:

classDiagram
    class ContentItem {
        +String id
        +SourceType source_type
        +String title
        +String content
        +Dict metadata
        +Optional~String~ file_path
        +Optional~String~ sender
        +Optional~List~ recipients
        +Optional~DateTime~ timestamp
        +Optional~String~ thread_id
        +Optional~DateTime~ embedded_at
        +Optional~int~ embedding_id
    }

    class SourceType {
        <<enumeration>>
        PDF
        EMAIL
        MESSAGE
        RESEARCH
        NOTE
    }

    class ContentStore {
        +add_pdf(file_path, content) ContentItem
        +add_email(subject, sender, body) ContentItem
        +add_research(query, result) ContentItem
        +add_note(title, content) ContentItem
        +query_by_source(source_type) List~ContentItem~
        +get_thread(thread_id) List~ContentItem~
    }

    class VectorMemory {
        +add(text) int
        +query(query, filters, top_k) List~Result~
        +update_filters(embedding_id, metadata)
    }

    ContentItem --> SourceType
    ContentStore --> ContentItem : creates
    ContentStore --> VectorMemory : auto-embeds

    3. Intent-Aware Task Routing
Dynamic task decomposition based on user intent, not just content type:

flowchart LR
    UserInput["User Input<br/>'Draft reply to investor email<br/>about funding'"]

    subgraph Router["Intent Router"]
        Parse[Parse Intent]
        Classify[Classify Tasks]
        Route[Route to Handlers]
    end

    subgraph Tasks["Generated Tasks"]
        T1[Task: FIND_EMAIL<br/>target: recent investor email]
        T2[Task: EXTRACT_CONTEXT<br/>funding discussion thread]
        T3[Task: MATCH_TONE<br/>sender: investor@vc.com]
        T4[Task: DRAFT_REPLY<br/>intent: funding update]
    end

    subgraph Handlers["Tool Handlers"]
        H1[Email Processor]
        H2[FAISS Memory]
        H3[Reply Generator]
    end

    UserInput --> Parse
    Parse --> Classify
    Classify --> Route
    Route --> T1
    Route --> T2
    Route --> T3
    Route --> T4

    T1 --> H1
    T2 --> H2
    T3 --> H2
    T4 --> H3

4. Memory-Aware Planning Flow
Planner retrieves relevant context before building execution plan:

sequenceDiagram
    actor User
    participant Router as Task Router
    participant Planner as Memory-Aware Planner
    participant FAISS as FAISS Memory
    participant Linkup as Linkup API
    participant Executor as Durable Executor
    participant Store as Content Store

    User->>Router: "Prepare briefing on Acme Corp<br/>using agenda.pdf"

    Router->>Router: Parse intent: SYNTHESIZE_BRIEFING
    Router->>Planner: Create plan with context

    Planner->>FAISS: query("Acme Corp recent news")
    FAISS-->>Planner: [research_item_1, email_mention_2]

    Planner->>FAISS: query("agenda.pdf topics")
    FAISS-->>Planner: [pdf_content_summary]

    Planner->>Planner: Identify gaps:<br/>- Missing recent Acme news<br/>- Need current funding status

    Planner->>Linkup: research("Acme Corp funding 2024")
    Linkup-->>Planner: {answer, sources}

    Planner->>Store: add_research(query, result)
    Store->>FAISS: auto-embed new research

    Planner->>Executor: Execute plan with all context

    loop Durable Execution
        Executor->>Executor: Step 1: Parse PDF
        Executor->>Executor: Step 2: Extract deadlines
        Executor->>Executor: Step 3: Synthesize with research
        note right of Executor: Each step checkpointed<br/>to SQLite for recovery
    end

    Executor-->>User: Briefing with PDF + Research combined

5. Multi-Domain Processing Pipeline
Unified handling of different content sources:

flowchart TB
    subgraph Input["Content Input"]
        PDF[PDF Upload]
        EML[.eml File Drop]
        MSG[Message Paste]
        Query[Research Query]
    end

    subgraph Normalize["Normalization Layer"]
        PDFProc[PDF Processor<br/>pdfplumber]
        EmailProc[Email Processor<br/>email.parser]
        TextProc[Text Processor<br/>clean + chunk]
        ResearchProc[Research Formatter<br/>Linkup → structured]
    end

    subgraph Enrich["Enrichment Layer"]
        Extract[Entity Extraction<br/>lightweight LLM]
        Actions[Action Item Detection<br/>rules + model]
        Meta[Metadata Inference<br/>priority, type, thread]
    end

    subgraph Store["Storage & Indexing"]
        SQLite[(SQLite<br/>Metadata & Relations)]
        FS[File System<br/>Original files)]
        FAISS2[FAISS<br/>Vector embeddings]
    end

    subgraph Retrieve["Retrieval APIs"]
        Semantic[Semantic Search<br/>FAISS + Cohere]
        Temporal[Temporal Query<br/>"last 7 days"]
        Thread[Thread Reconstruction<br/>email chains]
        Source[Source Filter<br/>"only emails"]
    end

    PDF --> PDFProc
    EML --> EmailProc
    MSG --> TextProc
    Query --> ResearchProc

    PDFProc --> Extract
    EmailProc --> Extract
    TextProc --> Extract
    ResearchProc --> Extract

    Extract --> Actions --> Meta

    Meta --> SQLite
    Meta --> FS
    Meta --> FAISS2

    SQLite --> Retrieve
    FAISS2 --> Retrieve

6. Email-Specific Pipeline
Specialized flow for email processing with tone matching:

sequenceDiagram
    participant User
    participant EmailProc as Email Processor
    participant Analyzer as Content Analyzer
    participant Memory as Tone Memory
    participant Generator as Reply Generator
    participant Eval as Tone Evaluator

    User->>EmailProc: Upload investor.eml
    EmailProc->>EmailProc: Parse headers & body
    EmailProc->>Analyzer: Extract action items
    Analyzer-->>EmailProc: ["respond to funding question", "send cap table"]

    User->>User: "Draft reply maintaining tone"

    Note over Memory: Retrieve tone examples
    Memory->>Memory: Query FAISS for<br/>emails from investor@vc.com
    Memory-->>Generator: [past_reply_1, past_reply_2]

    Generator->>Generator: Build prompt with:<br/>- Original email<br/>- Action items<br/>- Tone examples<br/>- User intent

    Generator->>Generator: Generate draft (local model)

    Generator->>Eval: Check tone match
    Eval->>Memory: Compare against examples
    Eval-->>Generator: Score: 0.85 (good)

    alt Score < 0.7
        Generator->>Generator: Regenerate with<br/>stronger tone guidance
    end

    Generator-->>User: Draft reply + tone confidence score

7. Fact-Checking Verification Flow
Structured verification against external and local sources:

flowchart LR
    Claim["User Claim:<br/>'Acme raised $50M Series B'"]

    subgraph Decompose["Claim Decomposition"]
        D1[Fact 1: Acme raised funding]
        D2[Fact 2: Amount was $50M]
        D3[Fact 3: Round was Series B]
    end

    subgraph Verify["Verification Engine"]
        V1[Search Linkup]
        V2[Check Local Docs]
        V3[Cross-reference]
    end

    subgraph Assess["Assessment"]
        A1[Evidence Strength]
        A2[Source Reliability]
        A3[Conflict Detection]
    end

    subgraph Report["Verification Report"]
        R1[Verdict: Supported/Contradicted/Unverified]
        R2[Confidence: 0-1]
        R3[Evidence Summary]
        R4[Recommended Action]
    end

    Claim --> D1
    Claim --> D2
    Claim --> D3

    D1 --> V1
    D1 --> V2
    D2 --> V1
    D3 --> V1

    V1 --> V3
    V2 --> V3

    V3 --> A1
    V3 --> A2
    V3 --> A3

    A1 --> R1
    A2 --> R2
    A3 --> R3
    A3 --> R4

8. Adaptive Resource Router
Smart routing between local and cloud based on resources and task complexity:

flowchart TD
    Task["Incoming Task"]

    subgraph Profile["Resource Profile Check"]
        Mem[Available RAM]
        CPU[CPU Load]
        GPU[GPU Available]
        Ollama[Ollama Health]
    end

    subgraph Decision["Routing Decision"]
        CanLocal["Can run local?"]
        Complexity["Task Complexity"]
        Urgency["User Tier/Urgency"]
    end

    subgraph Local["Local Execution"]
        L1[Ollama 0.5B<br/>Fast extraction]
        L2[Ollama 3B<br/>Quality synthesis]
        L3[Ollama 7B<br/>Complex reasoning]
    end

    subgraph Cloud["Cloud Execution"]
        C1[Gemini Flash<br/>Cheap & fast]
        C2[Gemini Pro<br/>High quality]
        C3[Claude/GPT-4<br/>Best quality]
    end

    subgraph Queue["Deferred Execution"]
        Q1[Queue for idle time]
        Q2[Notify when complete]
    end

    Task --> Profile
    Profile --> Decision

    Decision -->|Yes + Simple| L1
    Decision -->|Yes + Medium| L2
    Decision -->|Yes + Complex| L3

    Decision -->|No + Free tier| C1
    Decision -->|No + Pro tier| C2
    Decision -->|No + Enterprise| C3

    Decision -->|Resource constrained| Q1
    Q1 --> Q2

    L1 --> Result["Result + Metadata"]
    L2 --> Result
    L3 --> Result
    C1 --> Result
    C2 --> Result
    C3 --> Result
    Q2 --> Result

    Result --> Store[(SQLite Cost Log)]

9. Data Flow: Complete User Session
End-to-end flow from user input to persistent result:

sequenceDiagram
    participant UI as Electron UI
    participant API as FastAPI
    participant Router as Task Router
    participant Memory as Memory Layer
    participant Tools as Tool Layer
    participant Ext as External APIs
    participant DB as SQLite

    Note over UI,DB: Session: "Prepare for Acme meeting"

    UI->>API: POST /prep-with-files<br/>{command, files: [agenda.pdf]}
    API->>Router: parse_intent()

    Router->>Router: Classify: MEETING_PREP
    Router->>Router: Detect entities: ["Acme Corp"]

    Router->>Memory: Check existing research
    Memory-->>Router: Found: research_2024_01_15

    Router->>Memory: Check for recent news
    Memory-->>Router: Stale (>7 days)

    Router->>Router: Create tasks:<br/>1. Parse PDF<br/>2. Update research<br/>3. Synthesize briefing

    Router->>API: Return task plan
    API-->>UI: Stream: "Parsing PDF..."

    API->>Tools: Execute: parse_pdf
    Tools->>DB: Store extracted text
    Tools->>Memory: Embed to FAISS
    API-->>UI: Stream: "Researching Acme..."

    API->>Ext: Linkup.search("Acme Corp news 2024")
    Ext-->>API: {results}
    API->>Tools: Format research
    Tools->>DB: Store as ContentItem
    Tools->>Memory: Embed research

    API-->>UI: Stream: "Synthesizing briefing..."

    API->>Tools: Generate briefing<br/>(PDF + Research + Memory context)
    Tools->>Memory: Retrieve related emails
    Memory-->>Tools: [email_from_acme_ceo]

    Tools->>Tools: Synthesize with all context
    Tools->>DB: Store final briefing

    API-->>UI: Complete briefing + metadata

    Note over UI,DB: All content now in unified memory<br/>for future "reference last meeting" queries

10. Component Interaction Matrix

| Component                | Receives From             | Sends To         | Key Responsibility                    |
| ------------------------ | ------------------------- | ---------------- | ------------------------------------- |
| **Task Router**          | User input, Content items | Planner, Memory  | Intent parsing, task decomposition    |
| **Memory-Aware Planner** | Tasks, Memory context     | Executor         | Gap analysis, plan construction       |
| **Durable Executor**     | Plan, Tools               | Evaluator, Store | Checkpointed execution, retry logic   |
| **Content Store**        | Processed content         | FAISS, SQLite    | Unified storage, auto-embedding       |
| **FAISS Memory**         | Text chunks, Queries      | Planner, Tools   | Semantic retrieval, similarity search |
| **Email Processor**      | .eml files                | Content Store    | Parse, extract actions, detect tone   |
| **Reply Generator**      | Email, Tone examples      | User             | Context-aware draft generation        |
| **Fact Checker**         | Claims, Sources           | User             | Verification with evidence            |
| **Adaptive Router**      | Tasks, System stats       | LLM clients      | Cost/quality optimization             |
| **Quality Evaluator**    | Execution results         | Improvement Loop | Automated quality assessment          |


11. Deployment Architecture: Electron + Embedded Python
flowchart TB
    subgraph ElectronApp["Electron Application"]
        Main[Main Process<br/>Node.js]
        Renderer[Renderer Process<br/>React/Vue]
        Preload[Preload Script<br/>Secure Bridge]

        subgraph EmbeddedPython["Embedded Python Runtime"]
            PyProcess[Python Subprocess<br/>PyInstaller binary]
            FastAPI2[FastAPI Server<br/>localhost:dynamic]

            subgraph PyModules["Python Modules"]
                Core[Core Layer]
                Tools[Tool Layer]
                Memory2[Memory Layer]
            end
        end
    end

    subgraph LocalData["User Data Directory"]
        SQLite2[(SQLite DB)]
        FAISS3[FAISS Index Files]
        Docs[Document Storage]
        Config[Config & Keys]
    end

    subgraph External2["External Services"]
        Linkup2[Linkup API]
        Cohere2[Cohere Embeddings]
        OpenRouter2[OpenRouter]
    end

    Main -->|spawns| PyProcess
    Main -->|IPC| Preload
    Preload -->|HTTP| FastAPI2
    Renderer -->|IPC| Preload

    FastAPI2 --> Core
    Core --> Tools
    Core --> Memory2

    Tools -->|optional| Linkup2
    Memory2 -->|optional| Cohere2
    Tools -->|fallback| OpenRouter2

    PyModules -->|reads/writes| LocalData

12. Key Design Decisions
12.1 Why FAISS as Core Memory?
Speed: Sub-10ms retrieval for 10k+ documents
Privacy: Runs entirely locally
Flexibility: Supports metadata filtering + semantic search
Cost: Zero ongoing cost vs Pinecone/Weaviate
12.2 Why Task Router vs. LLM Planning?
Reliability: Deterministic, testable, no hallucination
Speed: No LLM latency for routing decisions
Cost: Zero routing cost
Observability: Clear execution paths
12.3 Why Content Unification?
Cross-domain queries: "What did Acme say in emails about the contract?"
Consistent memory: All sources embed same way
Simplified retrieval: Single query interface
12.4 Why Durable Execution?
Crash recovery: Resume mid-task after app restart
Background processing: Email digest at 8am, even if laptop was asleep
Audit trail: Complete execution history for compliance

13. Implementation Phases
gantt
    title Implementation Roadmap
    dateFormat  YYYY-MM-DD
    section Foundation
    Content Unification       :a1, 2024-01-01, 7d
    FAISS Integration         :a2, after a1, 5d
    SQLite Schema             :a3, after a1, 3d

    section Core Intelligence
    Task Router               :b1, after a2, 7d
    Memory-Aware Planner      :b2, after b1, 5d
    Durable Executor          :b3, after b2, 7d

    section Domain Features
    Email Processor           :c1, after a3, 5d
    Reply Generator           :c2, after c1, 5d
    Fact Checker              :c3, after b2, 5d

    section Desktop Integration
    Electron Shell            :d1, after a1, 10d
    Python Embedding          :d2, after d1, 5d
    IPC Bridge                :d3, after d2, 3d

    section Polish
    Adaptive Router           :e1, after b3, 5d
    Quality Evaluator         :e2, after e1, 5d
    Improvement Loop          :e3, after e2, 5d

14. Success Metrics
| Metric                         | Target  | Measurement                        |
| ------------------------------ | ------- | ---------------------------------- |
| Intent Classification Accuracy | >90%    | Manual review of 100 queries       |
| Memory Retrieval Precision     | >85%    | Relevance scoring on test set      |
| Email Reply Acceptance Rate    | >70%    | User edits <20% of draft           |
| Fact Check Confidence          | >80%    | Verified claims / total claims     |
| End-to-end Latency (simple)    | <3s     | PDF summary, local model           |
| End-to-end Latency (complex)   | <10s    | Research + synthesis, cloud        |
| Crash Recovery Rate            | 100%    | Simulated crashes during execution |
| User Data Retention            | 0 leaks | Security audit                     |
