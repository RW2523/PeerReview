# Arinar System Architecture

## High-Level System Overview

```mermaid
graph TB
    subgraph Frontend["Frontend - Next.js 15"]
        UI[React UI Components]
        WSClient[WebSocket Client]
        APIClient[API Client]
        Hooks[Custom Hooks]
        
        UI --> WSClient
        UI --> APIClient
        UI --> Hooks
    end
    
    subgraph Backend["Backend - FastAPI Python"]
        APIGateway[API Gateway Main]
        DebateRoutes[Debate Routes]
        AutonomousRoutes[Autonomous Routes]
        EventRoutes[Event Routes]
        WSRoutes[WebSocket Routes]
        
        DebateService[Debate Service]
        TurnOrch[Turn Orchestrator]
        AutonomousService[Autonomous Service]
        WSService[WebSocket Service]
        OpenRouterClient[OpenRouter Client]
        PrepPackService[Prep Pack Service]
        StateMachine[State Machine]
        
        APIGateway --> DebateRoutes
        APIGateway --> AutonomousRoutes
        APIGateway --> EventRoutes
        APIGateway --> WSRoutes
        
        DebateRoutes --> DebateService
        DebateRoutes --> TurnOrch
        AutonomousRoutes --> AutonomousService
        WSRoutes --> WSService
        
        TurnOrch --> OpenRouterClient
        TurnOrch --> PrepPackService
        AutonomousService --> TurnOrch
        WSService --> DebateService
    end
    
    subgraph DataLayer["Data Layer - PostgreSQL"]
        DB[(PostgreSQL Database)]
        Debates[debates table]
        Participants[participants table]
        Events[events table]
        Artifacts[artifacts table]
        PrepPacks[prep_packs table]
        
        DB --> Debates
        DB --> Participants
        DB --> Events
        DB --> Artifacts
        DB --> PrepPacks
    end
    
    subgraph External["External Services"]
        OpenRouter[OpenRouter API<br/>Multiple LLM Models]
        Tavily[Tavily Search API<br/>Web Research]
        MinIO[MinIO<br/>File Storage]
    end
    
    WSClient -.WebSocket.-> WSRoutes
    APIClient -->|HTTP REST| APIGateway
    
    DebateService --> DB
    TurnOrch --> DB
    AutonomousService --> DB
    WSService --> DB
    
    OpenRouterClient -->|LLM Calls| OpenRouter
    PrepPackService -->|Web Search| Tavily
    PrepPackService --> MinIO
    
    style UI fill:#0070F3,color:#fff
    style WSClient fill:#0070F3,color:#fff
    style APIClient fill:#0070F3,color:#fff
    
    style APIGateway fill:#10b981,color:#fff
    style DebateService fill:#10b981,color:#fff
    style TurnOrch fill:#10b981,color:#fff
    style AutonomousService fill:#10b981,color:#fff
    
    style DB fill:#666,color:#fff
    
    style OpenRouter fill:#f59e0b,color:#fff
    style Tavily fill:#f59e0b,color:#fff
    style MinIO fill:#f59e0b,color:#fff
```

---

## Detailed Component Architecture

```mermaid
graph LR
    subgraph FrontendComponents["Frontend Components"]
        SetupPage[Setup Page<br/>Wizard Flow]
        RoomPage[Room Page<br/>Live Debate]
        HistoryPage[History Page<br/>Past Debates]
        
        SetupPage --> BasicInfoStep
        SetupPage --> ParticipantsStep
        SetupPage --> MaterialsStep
        SetupPage --> PreflightStep
        SetupPage --> ReviewStep
        
        RoomPage --> EventFeed
        RoomPage --> DebateControls
        RoomPage --> InterventionBox
        
        ParticipantsStep --> AgentTemplates[80 Plus Agent Templates]
    end
    
    subgraph BackendServices["Backend Services"]
        DebateSvc[Debate Service<br/>CRUD Operations]
        TurnOrc[Turn Orchestrator<br/>Agent Execution]
        AutoSvc[Autonomous Service<br/>YOLO Mode Loop]
        WSSvc[WebSocket Service<br/>Real-time Events]
        PrepSvc[Prep Pack Service<br/>Research and Context]
        
        TurnOrc --> AgentPrompts[Prompt Engineering]
        TurnOrc --> LLMCalls[OpenRouter Integration]
        AutoSvc --> BackgroundTasks[Asyncio Tasks]
        PrepSvc --> WebSearch[Tavily API]
        PrepSvc --> FileStorage[MinIO Storage]
    end
    
    subgraph DatabaseSchema["Database Schema"]
        DebatesTable[debates<br/>state policy_config autonomous]
        ParticipantsTable[participants<br/>agents and host config]
        EventsTable[events<br/>messages actions system]
        ArtifactsTable[artifacts<br/>documents sections]
        PrepPacksTable[prep_packs<br/>research bundles]
    end
    
    style SetupPage fill:#0070F3,color:#fff
    style RoomPage fill:#0070F3,color:#fff
    style TurnOrc fill:#10b981,color:#fff
    style AutoSvc fill:#10b981,color:#fff
    style DebatesTable fill:#666,color:#fff
```

---

## Data Flow: Autonomous (YOLO) Mode

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant AutoService
    participant TurnOrch
    participant OpenRouter
    participant DB
    participant WebSocket

    User->>Frontend: Enable YOLO Mode + Launch
    Frontend->>API: POST /api/debates/id/start-autonomous
    Note over Frontend,API: Includes X-OpenRouter-Key header BYOK
    
    API->>DB: UPDATE debates SET autonomous_mode true
    API->>AutoService: start_autonomous_debate
    AutoService->>AutoService: Create background task run_autonomous_loop
    API-->>Frontend: status started
    
    loop Every N seconds auto_turn_delay
        AutoService->>DB: Check debate status and limits
        alt Status running AND within limits
            AutoService->>TurnOrch: trigger_next_turn
            TurnOrch->>DB: Get next agent and history
            TurnOrch->>TurnOrch: Build agent prompt with context
            TurnOrch->>OpenRouter: POST chat completion
            OpenRouter-->>TurnOrch: Agent response
            TurnOrch->>DB: INSERT event agent_message
            TurnOrch->>WebSocket: Broadcast event to clients
            WebSocket-->>Frontend: Real-time message update
            Frontend->>Frontend: Display in EventFeed
        else Status paused
            AutoService->>AutoService: Sleep and continue loop
        else Limits reached
            AutoService->>AutoService: conclude_debate
            AutoService->>DB: UPDATE debates SET state ended
            AutoService->>AutoService: Exit loop
        end
    end
    
    User->>Frontend: Click Pause
    Frontend->>API: POST /api/debates/id/pause-autonomous
    API->>DB: UPDATE autonomous_status paused
    Note over AutoService: Loop continues but skips turns
    
    User->>Frontend: Click Resume
    Frontend->>API: POST /api/debates/id/resume-autonomous
    Note over Frontend,API: Includes X-OpenRouter-Key header
    API->>DB: UPDATE autonomous_status running
    API->>AutoService: Restart background task if needed
```

---

## Turn Orchestration Flow

```mermaid
flowchart TD
    Start[trigger_next_turn called] --> CheckState{Debate state<br/>equals running?}
    CheckState -->|No| Error1[Throw StateTransitionError]
    CheckState -->|Yes| GetParticipants[Get participants list]
    
    GetParticipants --> CalcNext[Calculate next participant<br/>current_turn_index mod participant_count]
    CalcNext --> CheckLimits{Max rounds<br/>or timebox<br/>exceeded?}
    CheckLimits -->|Yes| Error2[Throw All rounds complete]
    CheckLimits -->|No| GetHistory[Fetch debate history<br/>and prep packs]
    
    GetHistory --> BuildPrompt[Build agent prompt]
    BuildPrompt --> AddContext[Add conversation history]
    AddContext --> AddMentions[Add mention context]
    AddMentions --> AddInterventions[Add moderator interventions]
    AddInterventions --> AddInstructions[Add turn round awareness]
    
    AddInstructions --> CallLLM[Call OpenRouter API]
    CallLLM --> ParseResponse[Parse LLM response]
    ParseResponse --> CalcRound[Calculate round number<br/>turn_index div participant_count plus 1]
    CalcRound --> PersistEvent[INSERT event to DB<br/>with round number]
    
    PersistEvent --> UpdatePolicy[Update policy_config<br/>increment turn_index and total_turns]
    UpdatePolicy --> BroadcastWS[Broadcast via WebSocket]
    BroadcastWS --> Return[Return event details]
    
    style Start fill:#0070F3,color:#fff
    style CallLLM fill:#f59e0b,color:#fff
    style PersistEvent fill:#666,color:#fff
    style Return fill:#10b981,color:#fff
```

---

## Database Schema

```mermaid
erDiagram
    DEBATES ||--o{ PARTICIPANTS : has
    DEBATES ||--o{ EVENTS : contains
    DEBATES ||--o{ ARTIFACTS : produces
    PARTICIPANTS ||--o{ PREP_PACKS : has
    
    DEBATES {
        uuid debate_id PK
        uuid workspace_id
        string title
        string state
        jsonb policy_config
        boolean autonomous_mode
        string autonomous_status
        int auto_turn_delay_seconds
        timestamp created_at
        timestamp started_at
        timestamp ended_at
    }
    
    PARTICIPANTS {
        uuid participant_id PK
        uuid debate_id FK
        string participant_type
        string role_name
        jsonb agent_config
        timestamp created_at
    }
    
    EVENTS {
        uuid event_id PK
        uuid debate_id FK
        string event_type
        string sender_type
        uuid sender_id FK
        bigint sequence_number
        jsonb content
        timestamp created_at
    }
    
    ARTIFACTS {
        uuid artifact_id PK
        uuid debate_id FK
        string artifact_type
        jsonb metadata
        timestamp created_at
    }
    
    PREP_PACKS {
        uuid prep_pack_id PK
        uuid participant_id FK
        uuid debate_id FK
        jsonb search_results
        string status
        timestamp created_at
    }
```

---

## Key Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15 (React) | Server-side rendering, routing, UI components |
| **State Management** | React Hooks (useState, useEffect, custom hooks) | Client-side state, WebSocket management |
| **Styling** | CSS Modules | Scoped styles, Vercel OLED dark theme |
| **Real-time** | WebSocket (native) | Live event streaming, bi-directional communication |
| **API Layer** | FastAPI (Python) | REST API, WebSocket server, async operations |
| **LLM Integration** | OpenRouter API | Multi-model support (GPT-4, Claude, etc.) |
| **Web Research** | Tavily API | Real-time web search for agent context |
| **Database** | PostgreSQL 15+ | Relational data, JSONB for flexible schemas |
| **File Storage** | MinIO (S3-compatible) | Artifact and document storage |
| **Background Tasks** | Python asyncio | Autonomous debate loops, async operations |
| **Authentication** | JWT tokens | Workspace-based access control |

---

## System Features

### 1. **Debate Setup Wizard**
- 6-step guided setup flow
- 80+ pre-configured agent personas across 15+ categories
- Iconic voices (Elon Musk, Steve Jobs, Jeff Bezos, etc.)
- Medical specialists, legal professionals, tech experts
- Custom agent creation with inline editing
- Prep pack generation with web research (Tavily)
- Host configuration (Ultimate Host as neutral moderator)
- Policy configuration (max rounds, timebox, YOLO mode)

### 2. **Live Debate Room**
- Real-time event feed with WebSocket
- Turn-based orchestration (round-robin)
- Progress tracking (per-agent turn counts, round numbers)
- Intervention system (moderator can inject guidance)
- Autonomous (YOLO) mode with background loop
- Unified pause/resume controls
- Turn separators showing round progression
- @mention support for agent tagging

### 3. **Agent Intelligence**
- Multi-model support via OpenRouter
- Persona-specific system prompts
- Context-aware prompts with full debate history
- Web research integration (prep packs)
- Temperature and token customization per agent
- First principles thinking, strategic analysis, domain expertise

### 4. **Autonomous Debates (YOLO Mode)**
- Background asyncio task loop
- Auto-triggers agents every N seconds (configurable)
- Respects max_rounds and timebox limits
- Pause/resume capability
- Crash recovery and status tracking
- BYOK model (Bring Your Own OpenRouter Key)

### 5. **Event System**
- Sequential event numbering
- Event types: agent_message, system_message, human_message, intervention, state_update, presence_update
- WebSocket broadcasting to all connected clients
- Historical event replay (since sequence number)
- Persistent storage in PostgreSQL

---

## File Structure

```
arinar-v2/
├── apps/
│   ├── web/ (Next.js Frontend)
│   │   └── src/
│   │       ├── app/
│   │       │   ├── setup/          # Setup wizard
│   │       │   ├── room/           # Live debate room
│   │       │   └── history/        # Past debates
│   │       ├── components/
│   │       │   ├── setup/          # Setup step components
│   │       │   ├── room/           # Room components (EventFeed, Controls)
│   │       │   └── layout/         # AppNav, UserMenu
│   │       ├── hooks/              # Custom React hooks
│   │       ├── lib/
│   │       │   ├── api.ts          # API client
│   │       │   └── wsClient.ts     # WebSocket client
│   │       └── styles/             # Global styles
│   │
│   └── api/ (FastAPI Backend)
│       └── src/
│           ├── main.py                        # FastAPI app entry
│           ├── routes/
│           │   ├── debates.py                 # Debate CRUD
│           │   ├── autonomous.py              # YOLO mode endpoints
│           │   ├── events.py                  # Event streaming
│           │   ├── websocket.py               # WebSocket endpoint
│           │   └── artifacts.py               # Artifact management
│           ├── debate_service.py              # Debate business logic
│           ├── turn_orchestrator.py           # Turn execution & prompting
│           ├── autonomous_debate_service.py   # Autonomous loop
│           ├── websocket_service.py           # WebSocket manager
│           ├── openrouter_client.py           # LLM integration
│           ├── agent_templates.py             # 80+ agent personas
│           ├── state_machine.py               # Debate state transitions
│           ├── database.py                    # DB connection pool
│           └── tasks/
│               ├── preflight.py               # Prep pack generation
│               └── web_search.py              # Tavily integration
│
├── migrations/                     # SQL migrations
│   ├── 001_initial_schema.sql
│   ├── 007_autonomous_debates.sql
│   └── ...
│
└── docker-compose.yml              # PostgreSQL + MinIO services
```

---

## Key Flows

### Setup → Launch Flow
1. User fills Basic Info (title, problem statement, agenda, outcomes, limits)
2. User selects participants from 80+ templates or existing agents
3. User optionally enables Ultimate Host as moderator
4. User optionally enables YOLO mode (autonomous)
5. System generates prep packs (web research) for each agent
6. System runs preflight checks
7. User reviews configuration
8. User clicks Launch → Creates debate + participants in DB
9. If YOLO enabled: Starts autonomous background loop
10. Redirect to Room page

### Agent Turn Flow
1. TurnOrchestrator determines next agent (round-robin based on turn_index)
2. Fetches debate history, prep packs, interventions
3. Builds context-rich prompt with:
   - Agent's system prompt (persona)
   - Problem statement & desired outcomes
   - Full conversation history
   - @mention context (agents who already spoke)
   - Moderator interventions (if any)
   - Turn/round awareness
4. Calls OpenRouter API with agent's model
5. Parses LLM response
6. Calculates round number: `(turn_index // participant_count) + 1`
7. Persists event to DB with round number
8. Updates policy_config (increment turn_index, total_turns)
9. Broadcasts event via WebSocket
10. Frontend displays message in EventFeed

### WebSocket Event Broadcasting
1. Client connects to `/ws/debates/{debate_id}?token=JWT&since=0`
2. Server validates JWT and workspace access
3. Server sends historical events (since sequence number)
4. Client subscribes to real-time events
5. When events occur (agent messages, state changes):
   - Server creates event envelope
   - Broadcasts to all connected clients for that debate
   - Clients update UI reactively

---

## State Machine

```mermaid
stateDiagram-v2
    [*] --> pending: Create Debate
    pending --> running: Start Debate
    running --> paused: Pause
    paused --> running: Resume
    running --> ended: End or Conclude
    paused --> ended: End
    ended --> [*]
    
    note right of running: Autonomous mode can be independently paused or resumed without affecting debate state
```

---

## Autonomous Service States

```mermaid
stateDiagram-v2
    [*] --> idle: Service Initialized
    idle --> running: start_autonomous_debate
    running --> paused: pause_autonomous_debate
    paused --> running: resume_autonomous_debate
    running --> completed: Debate limits reached
    running --> crashed: Exception in loop
    crashed --> running: resume_autonomous_debate
    completed --> [*]
    
    note right of running: Background asyncio task checks status every loop iteration and triggers turns automatically
```

---

## Security & Authentication

- **JWT-based authentication** for all API endpoints
- **Workspace-based access control** (multi-tenancy ready)
- **CORS configured** for cross-origin frontend-backend communication
- **Bring Your Own Key (BYOK)** model for OpenRouter API
  - API key sent via `X-OpenRouter-Key` header
  - Never stored server-side (privacy & security)
- **WebSocket authentication** via query parameter token

---

## Scalability Considerations

1. **Database**: PostgreSQL with JSONB for flexible schemas
   - Indexed on debate_id, sequence_number for fast queries
   - Connection pooling via psycopg2
   
2. **WebSocket**: In-memory connection manager
   - Currently single-instance (future: Redis pub/sub for multi-instance)
   
3. **Background Tasks**: Python asyncio
   - Multiple debates can run autonomously in parallel
   - Each debate = separate background task
   
4. **LLM Calls**: Async/await throughout
   - Non-blocking I/O for OpenRouter API calls
   - Rate limiting handled by OpenRouter
   
5. **File Storage**: MinIO (S3-compatible)
   - Scalable object storage for artifacts
   - Can be replaced with AWS S3, GCS, etc.

---

## Future Enhancements

- [ ] **Telegram Integration**: Stream debates to Telegram, mobile control
- [ ] **Redis pub/sub**: Multi-instance WebSocket support
- [ ] **Observability**: Structured logging, metrics, tracing
- [ ] **Agent memory**: Persistent memory across debates
- [ ] **Coalition support**: Private messaging between agents
- [ ] **Advanced interventions**: Clarifying questions from agents to host
- [ ] **Voice synthesis**: Text-to-speech for agent messages
- [ ] **Export formats**: PDF reports, audio podcasts

---

*Generated: Feb 2026 | Arinar v2 - Multi-Agent Debate Platform*
