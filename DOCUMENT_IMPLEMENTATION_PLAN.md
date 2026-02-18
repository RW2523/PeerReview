# Document Collaboration Feature - Implementation Plan

**Status**: In Progress  
**Started**: February 17, 2026  
**Phase**: 1 - Core Document Collaboration

---

## File Structure

```
apps/web/src/
├── components/
│   └── document/
│       ├── DocumentEditor.tsx          (100 lines) - Main Tiptap editor
│       ├── DocumentToolbar.tsx         (80 lines)  - Editor controls
│       ├── DocumentProgress.tsx        (60 lines)  - Section progress
│       ├── DocumentSectionHeader.tsx   (40 lines)  - Section headers
│       ├── AgentWritingIndicator.tsx   (50 lines)  - Agent presence
│       └── index.ts                    (10 lines)  - Exports
│
├── lib/
│   ├── document/
│   │   ├── types.ts                    (150 lines) - All type definitions
│   │   ├── templates.ts                (200 lines) - Template library
│   │   ├── yjs-provider.ts             (120 lines) - Yjs connection
│   │   ├── schema.ts                   (100 lines) - JSON schemas
│   │   └── utils.ts                    (80 lines)  - Helper functions
│   │
│   └── hooks/
│       ├── useDocument.ts              (150 lines) - Document state
│       ├── useDocumentSync.ts          (100 lines) - Real-time sync
│       └── useDocumentTemplate.ts      (80 lines)  - Template management
│
└── app/
    └── room/
        └── DocumentPanel.tsx           (120 lines) - Document view panel

apps/api/src/
├── routes/
│   └── documents.py                    (200 lines) - REST endpoints
│
├── services/
│   ├── document_service.py             (250 lines) - CRUD operations
│   ├── document_orchestrator.py        (300 lines) - Agent coordination
│   └── document_agent_writer.py        (200 lines) - Agent writing
│
├── websocket/
│   └── document_hub.py                 (250 lines) - WebSocket handler
│
└── schemas/
    └── documents.py                    (150 lines) - Pydantic models
```

**Total Files**: 23  
**Max File Size**: 300 lines  
**Principle**: Each file has single responsibility

---

## Phase 1 Implementation Order

### Step 1: Foundation (Types & Dependencies)
- [x] Install dependencies
- [ ] Create type definitions
- [ ] Create template structures
- [ ] Create JSON schemas

### Step 2: Frontend Document Infrastructure
- [ ] Yjs provider setup
- [ ] Document editor component
- [ ] Document toolbar
- [ ] Section management

### Step 3: Backend Document Infrastructure
- [ ] Database schema updates
- [ ] Document service (CRUD)
- [ ] REST API endpoints
- [ ] WebSocket handler

### Step 4: Integration
- [ ] Connect editor to backend
- [ ] Real-time sync testing
- [ ] Document panel in room
- [ ] Template selection UI

### Step 5: Testing & Polish
- [ ] Multi-user testing
- [ ] Performance optimization
- [ ] Error handling
- [ ] Documentation

---

## Dependencies to Install

### Frontend
```bash
npm install --workspace apps/web \
  @tiptap/react \
  @tiptap/starter-kit \
  @tiptap/extension-collaboration \
  @tiptap/extension-collaboration-cursor \
  y-websocket \
  yjs \
  zustand
```

### Backend
```bash
pip install \
  y-py \
  websockets
```

---

## Component Responsibilities

### Frontend

**DocumentEditor.tsx**
- Renders Tiptap editor
- Handles user input
- Displays agent cursors
- Max 100 lines

**DocumentToolbar.tsx**
- Format controls (bold, italic, lists)
- Export button
- Template selector
- Max 80 lines

**DocumentProgress.tsx**
- Shows section completion
- Agent assignments
- Word count tracking
- Max 60 lines

**useDocument.ts**
- Document state management
- Template application
- Section tracking
- Max 150 lines

**yjs-provider.ts**
- WebSocket connection
- Yjs document sync
- Awareness (presence)
- Max 120 lines

### Backend

**document_service.py**
- Create/read/update documents
- Template management
- Metadata storage
- Max 250 lines

**document_orchestrator.py**
- Assigns sections to agents
- Triggers agent writes
- Tracks progress
- Validates completion
- Max 300 lines

**document_agent_writer.py**
- Listens to debate events
- Generates structured content
- Writes to Yjs document
- Max 200 lines

**document_hub.py**
- WebSocket server
- Yjs sync protocol
- Awareness broadcast
- Max 250 lines

---

## Database Schema

```sql
-- New table for documents
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debate_id UUID NOT NULL REFERENCES debates(debate_id) ON DELETE CASCADE,
    template_id VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'in_progress',
    yjs_state_vector BYTEA,  -- Yjs document state
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_documents_debate ON documents(debate_id);
CREATE INDEX idx_documents_status ON documents(status);

-- Document sections tracking
CREATE TABLE document_sections (
    section_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    section_key VARCHAR(100) NOT NULL,
    assigned_agent_id UUID REFERENCES agents(agent_id),
    assigned_agent_name VARCHAR(200),
    word_limit INTEGER,
    word_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(document_id, section_key)
);

CREATE INDEX idx_sections_document ON document_sections(document_id);
CREATE INDEX idx_sections_status ON document_sections(status);
```

---

## API Endpoints

### REST API

```
POST   /documents                    - Create document for debate
GET    /documents/{document_id}      - Get document metadata
PUT    /documents/{document_id}      - Update document
DELETE /documents/{document_id}      - Delete document
GET    /documents/{document_id}/export - Export (PDF/DOCX)

GET    /templates                    - List templates
GET    /templates/{template_id}      - Get template details

GET    /debates/{debate_id}/document - Get debate's document
POST   /debates/{debate_id}/document - Create document for debate
```

### WebSocket

```
ws://localhost:8000/ws/document/{document_id}

Messages:
- sync_step_1: Yjs sync protocol
- sync_step_2: Yjs sync protocol
- awareness: User/agent presence
- update: Document updates
```

---

## Template Structure Example

```typescript
interface DocumentTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  sections: Section[];
}

interface Section {
  id: string;
  title: string;
  type: 'text' | 'list' | 'diagram';
  assignmentStrategy: 'host' | 'role' | 'manual';
  assignedRole?: string;  // e.g., "surgeon", "attorney"
  wordLimit?: number;
  required: boolean;
  schema?: JSONSchema;    // For structured content
  placeholder?: string;
}
```

**Built-in Templates**:
1. Meeting Summary (3 sections)
2. Medical Consultation (5 sections)
3. Legal Analysis (4 sections)
4. Technical Decision (6 sections)
5. Strategic Planning (4 sections)

---

## State Flow

```
1. User enables documentation in setup
   └─> Creates document record in DB
   └─> Assigns template

2. Debate starts
   └─> DocumentOrchestrator listens to events
   └─> Assigns sections to agents based on roles
   └─> Updates document_sections table

3. Agent speaks in debate
   └─> DocumentAgentWriter triggered
   └─> Generates content for assigned section
   └─> Writes to Yjs document via WebSocket
   └─> Frontend updates in real-time

4. All sections complete
   └─> Status: 'completed'
   └─> User can export

5. User exports
   └─> Backend generates PDF/DOCX
   └─> Returns download link
```

---

## Testing Strategy

### Unit Tests
- Template validation
- Section assignment logic
- Word count enforcement
- Schema validation

### Integration Tests
- Yjs sync with multiple clients
- Agent writing to document
- Export generation
- WebSocket reconnection

### E2E Tests
- Full debate with documentation
- Real-time updates across tabs
- Export and download

---

## Performance Considerations

1. **Yjs Document Size**: Limit to 50KB initial state
2. **WebSocket Connections**: Max 100 per document
3. **Agent Writing**: Throttle to 1 write per 5 seconds per agent
4. **State Persistence**: Save Yjs state every 30 seconds
5. **Export Generation**: Queue for large documents (>20 pages)

---

## Next Steps (In Order)

1. ✅ Create implementation plan
2. ⏳ Install dependencies
3. ⏳ Create type definitions
4. ⏳ Build template library
5. ⏳ Implement Yjs provider
6. ⏳ Create DocumentEditor component
7. ⏳ Build backend document service
8. ⏳ Implement WebSocket handler
9. ⏳ Connect frontend to backend
10. ⏳ Test with multiple users

---

**Estimated Time**: 3 weeks  
**Team Size**: 1-2 developers  
**Risk Level**: Low (using proven libraries)
