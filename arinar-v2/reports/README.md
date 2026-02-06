# Cursor Report Protocol

This folder is the single source of truth for ticket execution reports from Cursor.

## Required Rules (Mandatory)
1. Every ticket run must write a report file before claiming completion.
2. Reports must be stored under `reports/tickets/`.
3. File naming format:
   - `TICKET-XX[-sub]-YYYY-MM-DD-vN.md`
   - examples:
     - `TICKET-04-2026-02-06-v1.md`
     - `TICKET-03.1-2026-02-06-v2.md`
4. Cursor must update `reports/tickets/INDEX.md` for every new report.
5. Chat output from Cursor must be short:
   - only: report path, pass/fail status, blockers.
   - no long inline report in chat.

## Report Bootstrap Command
- Create a new report file from template:
- `bash scripts/new_ticket_report.sh TICKET-XX`
- Then fill the created file and update `reports/tickets/INDEX.md`.

## Required Sections In Every Report
- Summary
- Changed files (created/modified/deleted)
- Commands run + key output
- Gate checklist with PASS/FAIL per item
- Negative test evidence
- Known limitations
- Blockers / founder input needed
- Definition of done verdict

## Verification Expectations
- Claims are not accepted without command evidence.
- If a dependency is unavailable (for example, Docker daemon not running), report must mark that gate as `NOT VERIFIED`, not `PASS`.
