# Customer Support Agent — 4-Week Build Plan

Source documents: [BRD v1.0](docs/Customer_Support_Agent_BRD_v1.0.md), [SDD v1.0](docs/Customer_Support_Agent_SDD_v1.0.md)

## Goal and scope

Deliver an evaluated, secure-by-design support agent that runs locally via Docker Compose and covers
BRD phases 1–3 (Foundation, Knowledge MVP, Controlled Tools) plus a slice of phase 5 (hardening).
Pilot, DR drill, canary rollout and real vendor integrations are out of scope for these 4 weeks.

Assumptions: one developer, 5 working days per week, synthetic data only.

## Day-1 decisions (record each as a short ADR in `docs/adr/`)

| ADR | Decision | Rationale |
|---|---|---|
| 001 LLM | Claude Sonnet 5.5 (`claude-sonnet-5-5`) for generation, Haiku 5.5 (`claude-haiku-5-5`) for classification/judging, behind `LLMProvider` | Cheap fast routing; strong structured output |
| 002 Vector store | pgvector in the same PostgreSQL + Postgres full-text search for hybrid retrieval | One fewer service; ACL/version filters are SQL `WHERE` clauses |
| 002a Embeddings | Voyage / OpenAI / local sentence-transformers behind `EmbeddingProvider` | Anthropic has no embeddings API |
| 003 Identity | Locally signed JWT (dev token CLI); `customer_id` comes only from `sub` | Exercises authorization without a real IdP |
| 004 CRM/Ticketing | In-repo fake adapters with failure injection (timeout, 5xx, unknown outcome) | Vendors undecided; fakes make BR-007/BR-018 testable |
| 005 Handoff | Escalation = ticket creation with structured handoff payload (no live transfer) | Simplest path that satisfies BR-008 |
| 007 State | Conversation state in Postgres; no LangGraph checkpointing | Not needed without HITL pauses |
| 008 Deploy | Docker Compose; one managed container target only if Week 4 allows | — |

Package name: keep the existing `src/customer_support_agent/` (the SDD's `customer_support/` is renamed accordingly).

## Explicitly deferred

Redis, reranking, background ingestion queue/worker, Kubernetes, canary rollout, retention/deletion jobs
(document the policy instead), DR drill, `change_account_details`, real IdP/CRM/ticketing, additional channels.
Grow into the SDD folder tree incrementally — create modules only when they get code.

## Ground rules

1. Golden set is written at the start of Week 2, before retrieval code.
2. Authorization lives outside the prompt: tools take `customer_id` from request context, never from model output.
3. Unit tests use `FakeLLM` / `FakeEmbeddings`; the real model is used only in evals.
4. Every BR requirement ends up mapped to a test or eval result (see traceability table at the end).

---

## Week 1 — Foundation

BRs: BR-001, BR-002, BR-011 (partial), BR-015, BR-018 (partial)

| Day | Tasks |
|---|---|
| 1 | Write ADRs 001–008. Add dependencies (fastapi, uvicorn, pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, pgvector, langgraph, anthropic, pyjwt, structlog, httpx; dev: pytest, pytest-asyncio, ruff, pyright/mypy). `docker-compose.yml` with `pgvector/pgvector` Postgres. `.env.example`. `core/settings.py` with fail-fast validation and secret masking. |
| 2 | FastAPI app factory (`main.py`), correlation-ID middleware, structured JSON logging, error contract from SDD §6.3 (`core/exceptions.py`, `api/error_handlers.py`), `/health/live` and `/health/ready` (DB check). |
| 3 | SQLAlchemy models + first Alembic migration: customer, conversation, message, audit_event, tool_execution, source_document, knowledge_chunk (with `vector` + `tsvector` columns). Async session management. |
| 4 | JWT auth dependency + `scripts/issue_dev_token.py`. Customer-scoped repositories (every method requires `customer_id`). `ChatService` with a stub workflow. `POST /api/v1/chat` creating/loading a conversation and persisting user + assistant messages. `LLMProvider` interface + `AnthropicProvider` + `FakeLLM`. |
| 5 | Tests: API contract, error shape, auth required, cross-customer conversation → 404, persistence round-trip. GitHub Actions CI: ruff, type check, pytest with Postgres service. README quickstart. |

**Exit criteria:** `docker compose up` → authenticated chat round-trip persisted; forged `conversation_id` from another customer rejected; CI green.

---

## Week 2 — Knowledge MVP

BRs: BR-003, BR-004, BR-009, BR-013

| Day | Tasks |
|---|---|
| 6 | **Corpus + golden set first.** Write 25–40 Markdown docs for a fictional company in `data/corpus/` (FAQs, shipping, returns, warranty, account policies). Include: one stale/superseded doc, one conflicting pair, one doc containing a prompt-injection payload. Write `evals/datasets/knowledge_v1.jsonl` (~60 cases: answerable, unanswerable, ambiguous, conflicting) with expected source IDs and expected behavior (`answer` / `clarify` / `abstain` / `escalate`). |
| 7 | Ingestion CLI `scripts/ingest_documents.py`: parse Markdown (front-matter: id, version, owner, status), heading-aware chunking, checksum-based idempotency, embed via `EmbeddingProvider`, upsert, validate, then mark version `active` (previous version stays active until the new one passes). |
| 8 | Hybrid retrieval in `knowledge/retrieval.py`: pgvector cosine + `ts_rank` full-text, merged by reciprocal rank fusion; mandatory `status='active'` + ACL filters. `Evidence` object (SDD Appendix A.1). Citation builder. Retrieval eval: recall@k, MRR. |
| 9 | LangGraph workflow (`agent/graph.py`): `classify_intent` (Haiku, structured output, finite enum) → router → `retrieve_context` → `evaluate_evidence` (sufficiency/conflict) → `generate_response` → `validate_citations`; branches to `clarify` / `abstain`. Prompts as versioned files in `agent/prompts/`. Wire into `ChatService`. |
| 10 | `scripts/run_evaluations.py`: retrieval metrics, deterministic citation validity, LLM-judge groundedness + manual spot-check of 15 cases, abstention correctness on unanswerable cases. Output a versioned JSON + Markdown report in `evals/reports/` recording model/prompt/workflow/corpus versions. Tune chunking/top-k once. |

**Exit criteria:** first eval report exists; citation validity ≈ 100% (deterministic); groundedness and abstention numbers recorded against BRD targets (≥ 90% groundedness, ≥ 95% citation correctness). This is the highest-risk week — if tuning drags, accept current numbers and log gaps.

---

## Week 3 — Controlled tools, escalation, security

BRs: BR-005, BR-006, BR-007, BR-008, BR-009, BR-010, BR-016 (partial)

| Day | Tasks |
|---|---|
| 11 | Tool framework: `ToolDefinition` (SDD §9.1: name, input/output schema, risk tier, permissions, timeout, retry, idempotency), `ToolRegistry` (allowlist only), `ToolResult` with statuses `succeeded / pending / rejected / failed / unknown`. Executor implementing SDD §9.2 steps 1–8, writing `tool_execution` + `audit_event` rows. |
| 12 | Fake order system (`integrations/crm/fake.py`) with seeded orders for 3 customers and failure injection. `get_order_status` tool: customer bound from context, ownership check, field allowlist. Graph route for `order_status` intent; live result always wins over documents. |
| 13 | Fake ticketing adapter. `create_support_ticket` with idempotency key and duplicate protection; ticket ID returned only after confirmation. `EscalationService` building the handoff payload (reason, summary, relevant messages, sources, attempted tools + results; minimized PII). `request_refund` as a gated tool: always `requires_human_approval` → creates ticket, never writes. |
| 14 | Workflow budgets (max steps, tool calls, elapsed time, tokens) enforced in the graph. PII redaction processor for logs. Untrusted-content framing for retrieved docs and user input in prompts. `GET /api/v1/tickets/{id}` with ownership check. |
| 15 | Security + safety test suite (`tests/security/`): another customer's order ID in message, injection in retrieved doc, injection asking for refund/tool misuse, duplicate ticket request, timeout-after-write → `unknown` language and no blind retry, unknown tool name from model rejected. Add tool-use cases to the eval dataset. |

**Exit criteria:** all BR-005–BR-010 tests green; zero cross-customer leaks; no write ever reported as complete without a confirmed result.

---

## Week 4 — Observability, hardening, delivery

BRs: BR-011, BR-012, BR-013, BR-017, BR-018

| Day | Tasks |
|---|---|
| 16 | OpenTelemetry tracing across API → ChatService → graph nodes → retrieval → tools; Jaeger in Compose. Span attributes: correlation ID, route, model/prompt/workflow versions, token usage, tool outcome (no message content). Basic metrics (latency, errors, escalations, tokens). |
| 17 | `POST /api/v1/conversations/{id}/feedback`, `GET /api/v1/conversations/{id}` and `/messages` (paginated, redacted). Rate limiting per customer (in-process or Postgres-backed). Request size limits. |
| 18 | Failure-injection tests for each SDD §11.3 degraded mode (LLM down, vector search down, CRM down, ticketing down, telemetry down) → safe error contract, no fabricated data. Small eval subset as a CI gate; full eval on demand. |
| 19 | Dockerfile (multi-stage, non-root). k6 or Locust run for a p95 latency baseline with `FakeLLM` and with real LLM. Runbooks in `docs/runbooks/`: LLM outage, ambiguous write reconciliation, suspected data exposure. Optional: deploy to one managed container platform. |
| 20 | **Buffer.** Final eval report; README; fill in the traceability table below; record known limitations and next steps. |

**Exit criteria:** end-to-end demo of knowledge answer, order lookup, ticket creation, escalation and refund-gating; traces visible in Jaeger; final eval report and traceability table complete.

---

## Traceability (fill in during Week 4)

| BR | Evidence (test file / eval report) | Status |
|---|---|---|
| BR-001 Conversation entry | | |
| BR-002 Conversation continuity | | |
| BR-003 Knowledge-grounded answers | | |
| BR-004 Source traceability | | |
| BR-005 Live business lookup | | |
| BR-006 Tool authorization | | |
| BR-007 Action verification | | |
| BR-008 Escalation | | |
| BR-009 Uncertainty handling | | |
| BR-010 Safety controls | | |
| BR-011 Observability | | |
| BR-012 Feedback | | |
| BR-013 Evaluation gate | | |
| BR-014 Operational recovery | Deferred — runbooks only | |
| BR-015 Configuration security | | |
| BR-016 Data minimization | Partial — redaction; retention documented only | |
| BR-017 Rate and cost controls | | |
| BR-018 Accessible failure behavior | | |

## Risks

| Risk | Mitigation |
|---|---|
| Retrieval tuning overruns Week 2 | Time-box to Day 10; accept and log gaps; revisit on Day 20 buffer |
| Flaky/expensive tests from real LLM calls | `FakeLLM` in unit/integration tests; real model only in eval runs |
| Python 3.14 wheel gaps in a dependency | Check on Day 1; fall back to 3.13 in `.python-version` if needed |
| Scope creep from the full SDD structure | Stick to the deferred list; new ideas go to a backlog section in README |
