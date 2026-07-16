<div align="center">

# 🎓 PeerForge

### The auditable review-rehearsal platform for researchers

Upload your manuscript → get interrogated by an AI review panel grounded in *your own* materials → rehearse your answers → walk away with a signed, publicly verifiable readiness record.

</div>

---

## What is this?

PeerForge is an **AI academic peer-review rehearsal platform**. A PhD student, researcher, or author uploads their paper or thesis; PeerForge builds a panel of AI reviewers that critique it **grounded in the uploaded document**, lets them practice answering the panel (by text or voice), tracks readiness across ten academic dimensions, and issues a **tamper-evident, publicly verifiable certificate**.

Unlike generic AI review tools, every reviewer claim hard-links to the exact source line it quotes (**SHA-256 re-verified live**), unsupported claims are flagged as **evidence gaps**, and the final certificate is **Ed25519-signed** so an institution can verify it without logging in.

## The three pillars

- 🔍 **Glass-Box Provenance** — every critique traces to a verified source line in your own PDF, or is flagged as a gap.
- 👥 **Committee Twin** — build AI twins of your real reviewers from their actual publications.
- 📜 **Readiness Certificate** — a signed, publicly verifiable record of your readiness trajectory.

## The application lives in [`arinar-v2/`](arinar-v2/)

The full monorepo — Next.js frontend + FastAPI backend + Celery workers — is under **[`arinar-v2/`](arinar-v2/)**.

👉 **See [`arinar-v2/README.md`](arinar-v2/README.md) for full documentation, feature list, architecture, and quick-start.**

```bash
cd arinar-v2
docker compose -f infra/docker/docker-compose.yml up -d db redis minio   # infra
# then start the API (apps/api) and frontend (apps/web) — see arinar-v2/README.md
./run_app.sh                                                              # or one-command startup
```

## Tech stack

Next.js 15 · FastAPI (Python 3.11) · PostgreSQL · Redis · MinIO/S3 · Celery · OpenRouter (BYOK) · Supabase auth · Ed25519 signing.

## License

Proprietary — © 2026 PeerForge. All rights reserved. See [`arinar-v2/LICENSE`](arinar-v2/LICENSE).
