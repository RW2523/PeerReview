# Ticket Queue

## Stage 0 (Completed)
1. `TICKET-01-monorepo-bootstrap-and-boundaries.md`
2. `TICKET-02-api-contracts-and-schema-foundation.md`
3. `TICKET-03-ci-quality-gates-and-anti-dup-checks.md`
4. `TICKET-04-local-infra-db-bootstrap-and-initial-migrations.md`

## Stage 1 (Now)
Run in strict order:
1. `TICKET-05.1-api-test-gates-and-ci-alignment.md`
2. `TICKET-06-m2-realtime-controls-and-live-feed.md`

## Stage 1 (Completed)
1. `TICKET-05-m1-debate-in-a-box-api.md`

Rule:
- Do not start next ticket until current ticket passes its Definition of Done.
- Model-provider rule for all tickets: **OpenRouter-only**. Do not integrate direct OpenAI/Anthropic/Google SDKs.
- Terminology note: `OpenAPI` in tickets means API contract specification, not OpenAI provider usage.
- Reporting rule (mandatory): Cursor must write ticket outcomes to `/Users/pv/Downloads/arinar-6-IPSS-V5/arinar-v2/reports/tickets/` and update `/Users/pv/Downloads/arinar-6-IPSS-V5/arinar-v2/reports/tickets/INDEX.md`. Do not send full reports in chat.
