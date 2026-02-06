# apps/web - Next.js Frontend Application

## Purpose
Next.js application providing UI rendering and Backend-for-Frontend (BFF) layer.

## Ownership
**Team**: Frontend
**Primary Contact**: TBD

## Responsibilities
- Server-side rendering and client-side hydration
- UI component rendering
- Client-side routing and state management
- BFF API routes for UI-specific concerns

## Technology Stack
- Next.js 14+ (App Router)
- React 18+
- TypeScript
- Tailwind CSS (or design system TBD)

## Boundaries

### ✅ Allowed
- React components and hooks
- Next.js API routes that aggregate/transform backend data
- Client-side state management (React Query, Zustand)
- UI utilities and helpers
- Import from `packages/contracts`, `packages/ui`

### ❌ Forbidden
- Direct database access
- Business logic implementation
- Policy enforcement
- Direct imports from `apps/api` or `apps/workers`
- Direct secret/credential management

## API Routes (BFF Pattern)
Use Next.js API routes only for:
- Aggregating multiple FastAPI calls
- Transforming backend responses for UI
- Handling UI-specific auth flows
- Session management

**All business logic must live in `apps/api`**

## Development
```bash
# Install dependencies
pnpm install

# Run dev server
pnpm dev

# Build
pnpm build

# Run tests
pnpm test
```

## Related Docs
- ADR-0001: Repository Boundaries
- ADR-0002: Service Boundaries
- WORKSPACE-MAP.md
