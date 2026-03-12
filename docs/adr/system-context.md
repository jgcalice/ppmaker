# PPMaker — System Context (C4 Level 1)

## Context Diagram

```mermaid
C4Context
    title PPMaker — System Context

    Person(user, "Professional User", "Analyst, consultant, or manager who needs to create presentations")

    System(ppmaker, "PPMaker", "Web app that transforms text into professional PowerPoint presentations using AI")

    System_Ext(claude, "Anthropic Claude API", "LLM that generates storytelling structure and slide content")
    System_Ext(pptx_engine, "python-pptx", "Library that generates .pptx files from templates")

    Rel(user, ppmaker, "Inputs content text, selects template, downloads PPTX", "HTTPS")
    Rel(ppmaker, claude, "Sends prompt chain for storytelling generation", "HTTPS / SSE")
    Rel(ppmaker, pptx_engine, "Calls locally to generate PPTX in-memory", "In-process")
```

## Container Diagram (C4 Level 2)

```mermaid
C4Container
    title PPMaker — Containers

    Person(user, "Professional User")

    Container(frontend, "Frontend", "Next.js 14", "4-step creation flow: template selection, content input, storytelling review, PPTX download. SSE streaming for real-time AI progress.")
    Container(backend, "Backend API", "Python FastAPI", "REST + SSE API. Orchestrates AI prompt chain and PPTX generation. Stateless — no database required for MVP.")
    ContainerDb(templates, "Template Store", "Filesystem", "template_padrao/ directory with .pptx template files and .json metadata (palette, fonts, layouts)")

    System_Ext(claude, "Anthropic Claude API", "LLM generation")

    Rel(user, frontend, "Uses", "HTTPS")
    Rel(frontend, backend, "API calls + SSE stream", "HTTP/REST")
    Rel(backend, claude, "Prompt chain (6 archetypes)", "HTTPS / streaming")
    Rel(backend, templates, "Reads .pptx + .json", "File I/O")
```

## Data Flow (Sequence)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Next.js)
    participant BE as Backend (FastAPI)
    participant AI as Claude API
    participant FS as Template Store

    User->>FE: 1. Select template
    FE->>BE: GET /api/v1/templates
    BE->>FS: Scan template_padrao/
    FS-->>BE: .json metadata files
    BE-->>FE: Template list
    FE-->>User: Display template cards

    User->>FE: 2. Input content + context
    FE->>BE: POST /api/v1/storytelling (SSE)
    BE->>AI: Prompt chain (planner → architect → story_builder → visual_director → content_gen → editor)
    AI-->>BE: Streaming response chunks
    BE-->>FE: SSE events (type: chunk)
    FE-->>User: Progressive outline display
    BE-->>FE: SSE event (type: done, data: StorytellingOutline)

    User->>FE: 3. Review & edit outline
    User->>FE: 4. Generate PPTX
    FE->>BE: POST /api/v1/generate-pptx
    BE->>FS: Load .pptx template
    FS-->>BE: Template file
    BE->>BE: python-pptx: populate slides from outline
    BE-->>FE: Binary .pptx file
    FE-->>User: Download PPTX
```

## Key Architectural Decisions

| # | Decision | ADR |
|---|----------|-----|
| 1 | SSE for streaming AI responses (not polling or WebSockets) | [ADR-001](ADR-001-sse-vs-polling.md) |
| 2 | python-pptx for PPTX generation (not Aspose or LibreOffice) | [ADR-002](ADR-002-pptx-generation.md) |
| 3 | Dashed-border rectangles for placeholder slides | [ADR-003](ADR-003-placeholder-strategy.md) |
