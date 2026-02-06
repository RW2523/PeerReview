# Arinar V2 - AI-Native Knowledge Platform

## Overview
Arinar V2 is a modular monorepo implementing a privacy-first, policy-governed knowledge platform with AI-powered capabilities.

## Architecture Philosophy
- **Strict boundaries**: Clear separation between UI, API, and workers
- **API-first**: Contracts defined before implementation
- **Hybrid approach**: Next.js for UI + BFF, Python microservices for domain logic
- **No assumptions**: Policy-enforced responses with proper guardrails

## Workspace Structure

```
arinar-v2/
├── apps/                    # Deployable applications
│   ├── web/                # Next.js app (UI + BFF endpoints only)
│   ├── api/                # FastAPI app (domain APIs, orchestration)
│   └── workers/            # Background jobs (Temporal/ingestion)
├── packages/               # Shared libraries
│   ├── contracts/          # OpenAPI/JSON schemas/types
│   ├── ui/                 # Reusable UI components
│   ├── prompts/            # Prompt templates + utilities
│   └── tooling/            # Lint/test/dev scripts
├── infra/                  # Infrastructure configuration
│   ├── migrations/         # SQL migrations
│   └── docker/             # Local infrastructure configs
├── tests/                  # Test suites
│   ├── e2e/               # End-to-end tests
│   └── integration/        # Cross-service integration tests
└── docs/                   # Documentation
    ├── architecture/       # ADRs and architecture docs
    └── runbooks/           # Operational guides
```

## Key Principles

### 1. Boundary Enforcement
- No business logic in `apps/web` UI components
- No direct DB writes from frontend
- No cross-imports that bypass package boundaries
- See `WORKSPACE-MAP.md` for detailed import rules

### 2. Standards Compliance
All code must follow:
- File naming conventions
- File size limits (300-500 lines)
- API contract requirements
- Test coverage requirements

See `/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md` for complete standards.

### 3. Duplicate Prevention
- Search before creating new modules
- Extend existing functionality when domain matches
- Use CI checks to prevent duplicate exports

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- pnpm (for Node.js packages)

### Development Setup
```bash
# Install dependencies
pnpm install

# Start local infrastructure
docker-compose up -d

# Run migrations
pnpm migrate:dev

# Start development servers
pnpm dev
```

## Documentation
- Architecture decisions: `docs/architecture/`
- Operational runbooks: `docs/runbooks/`
- Workspace boundaries: `WORKSPACE-MAP.md`
- Ticket execution reports: `reports/tickets/`

## Engineering Standards
This workspace follows strict engineering standards to prevent codebase drift and ensure consistency across AI-assisted development.

**Mandatory reading**: `/2026-goals-codex/15-engineering-standards-and-anti-chaos-rules.md`

## Current Status
**Phase**: Bootstrap and Foundation (Q1 2026)

See `/2026-goals-codex/tickets/` for current implementation tickets.
