SOFTWARE DESIGN DOCUMENT

# Customer Support Agent

Software Design Document Architecture, component contracts, data model,
security and operations

| Document status | Draft baseline for stakeholder review |
|---|---|
| Version | 1.0 |
| Prepared | 22 October 2026 |
| Architecture baseline | RAG + business tools \| LangGraph \| cloud-managed containers |

Purpose: establish a shared, reviewable baseline for product,
engineering, security, operations, and business stakeholders. Items
marked as assumptions or decisions required must be confirmed before
implementation commitments.

# Document control and design baseline

| Field | Value |
|---|---|
| Related business document | Customer Support Agent --- BRD v1.0 |
| Architecture style | Modular monolith with explicit module boundaries and adapter interfaces |
| Runtime | Python + FastAPI |
| Orchestration | LangGraph controlled state graph |
| Primary persistence | PostgreSQL; Redis optional for cache/rate limits |
| Knowledge retrieval | Vector store adapter; hybrid retrieval/reranking where justified |
| Deployment | Docker image on cloud-managed container platform; Kubernetes only if justified |
| Status | Detailed design baseline --- vendor/API decisions remain open |

# Contents

1. Purpose, scope and design principles
2. Architecture overview and boundaries
3. Repository structure and dependency rules
4. Request lifecycle and workflow state machine
5. Component designs and contracts
6. API design
7. Data model and persistence
8. Knowledge ingestion and retrieval design
9. Tool execution and action safety
10. Security and threat model
11. Reliability, concurrency and performance
12. Observability, evaluation and release gates
13. Deployment, configuration and operations
14. Testing strategy, traceability and open decisions

# 1. Purpose, scope and design principles

This document translates the BRD into a technical design that
engineering teams can implement and test. It defines component
responsibilities, interfaces, state transitions, persistence, security
boundaries, operational behavior and release controls. It is a design
baseline; vendor-specific details must be finalized through the decision
register before production implementation.

## 1.1 Core design principles

-   Deterministic control around probabilistic components: LLMs propose
    classifications or content, while application code enforces
    permissions, workflow limits and business invariants.

-   Modular monolith first: deploy one API/application unit initially,
    with separate workers for long-running ingestion when needed.

-   Ports and adapters: provider-specific implementations sit behind
    stable interfaces.

-   Authoritative data separation: knowledge sources answer policy
    questions; live systems of record answer transactional questions.

-   Fail closed for authorization and high-impact writes; degrade safely
    for optional capabilities.

-   Traceability: every request, retrieval, model call, tool call and
    outcome has a correlation/trace relationship.

-   Reproducibility: record prompt, model, retrieval configuration,
    corpus version and workflow version for evaluation and incident
    analysis.

# 2. Architecture overview and boundaries

```
Customer Channel
|
v
FastAPI API Layer
- authentication / request validation / rate limits
- correlation ID / normalized error response
|
v
Chat Application Service
|
v
LangGraph Support Workflow
classify -> route -> retrieve OR approved tool -> validate evidence
|                         | |
+---- clarify/escalate ---+---------------------+
|
v
Response Policy Layer
|
v
Persist + return response
Supporting adapters:
PostgreSQL | Vector Store | LLM Provider | CRM/Ticketing APIs
Redis (optional) | Background Queue/Worker | OpenTelemetry/Langfuse
```

The diagram is a logical view. Physical deployment may initially place
API, agent workflow and application services in one container image,
while database, vector store, model provider and external systems remain
separate dependencies.

## 2.1 Trust boundaries

| Boundary | Untrusted input / risk | Required control |
|---|---|---|
| Client → API | Forged IDs, oversized payloads, abuse. | Authentication, schema validation, size limits, rate limits. |
| User/content → LLM | Prompt injection, instruction confusion, data exfiltration. | Treat content as data; do not delegate authorization to prompts. |
| LLM → tool layer | Malformed arguments, overbroad actions, fabricated IDs. | Typed schemas, allowlist, policy checks, authenticated context binding. |
| Application → business API | Credential leakage, retries, inconsistent outcomes. | Scoped service credentials, timeout/retry policy, idempotency and result verification. |
| Application → persistence | Injection, cross-customer access, data over-retention. | Parameterized access, repository filters, access control and retention jobs. |
| Logs/traces → observability | PII or secrets copied into telemetry. | Redaction, field allowlists, access control and retention settings. |

# 3. Repository structure and dependency rules

```

customer-support-agent/
│
├── pyproject.toml
├── uv.lock
├── README.md
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
│
├── config/
│   ├── logging.yaml
│   └── model_config.yaml
│
├── src/
│   └── customer_support/
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── api/
│       │   ├── dependencies.py
│       │   ├── middleware.py
│       │   ├── error_handlers.py
│       │   └── v1/
│       │       ├── router.py
│       │       ├── chat.py
│       │       ├── conversations.py
│       │       ├── tickets.py
│       │       └── feedback.py
│       │
│       ├── core/
│       │   ├── settings.py
│       │   ├── security.py
│       │   ├── logging.py
│       │   ├── exceptions.py
│       │   └── constants.py
│       │
│       ├── domain/
│       │   ├── entities.py
│       │   ├── schemas.py
│       │   ├── enums.py
│       │   └── policies.py
│       │
│       ├── services/
│       │   ├── chat_service.py
│       │   ├── conversation_service.py
│       │   ├── ticket_service.py
│       │   └── escalation_service.py
│       │
│       ├── agent/
│       │   ├── orchestrator.py
│       │   ├── state.py
│       │   ├── routing.py
│       │   ├── graph.py
│       │   ├── nodes/
│       │   │   ├── classify_intent.py
│       │   │   ├── retrieve_context.py
│       │   │   ├── execute_tool.py
│       │   │   ├── generate_response.py
│       │   │   └── evaluate_response.py
│       │   ├── prompts/
│       │   │   ├── system.md
│       │   │   ├── intent_classifier.md
│       │   │   └── response_generator.md
│       │   └── policies/
│       │       ├── escalation.py
│       │       └── confidence.py
│       │
│       ├── knowledge/
│       │   ├── ingestion.py
│       │   ├── parsing.py
│       │   ├── chunking.py
│       │   ├── embeddings.py
│       │   ├── indexing.py
│       │   ├── retrieval.py
│       │   ├── reranking.py
│       │   └── citations.py
│       │
│       ├── tools/
│       │   ├── registry.py
│       │   ├── base.py
│       │   ├── customer_lookup.py
│       │   ├── order_lookup.py
│       │   ├── create_ticket.py
│       │   └── refund_request.py
│       │
│       ├── integrations/
│       │   ├── llm/
│       │   │   ├── base.py
│       │   │   └── provider.py
│       │   ├── vector_store/
│       │   │   └── provider.py
│       │   ├── crm/
│       │   │   └── client.py
│       │   └── ticketing/
│       │       └── client.py
│       │
│       ├── persistence/
│       │   ├── database.py
│       │   ├── models.py
│       │   ├── repositories/
│       │   │   ├── conversation.py
│       │   │   ├── message.py
│       │   │   └── ticket.py
│       │   └── migrations/
│       │
│       ├── memory/
│       │   ├── conversation_store.py
│       │   └── summarizer.py
│       │
│       ├── security/
│       │   ├── input_validation.py
│       │   ├── pii_redaction.py
│       │   ├── authorization.py
│       │   ├── guardrails.py
│       │   └── audit.py
│       │
│       ├── observability/
│       │   ├── tracing.py
│       │   ├── metrics.py
│       │   └── llm_logging.py
│       │
│       └── workers/
│           ├── ingestion_worker.py
│           └── background_tasks.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── agent/
│   ├── security/
│   ├── evaluation/
│   └── fixtures/
│
├── evals/
│   ├── datasets/
│   ├── retrieval/
│   ├── response_quality/
│   ├── tool_use/
│   └── regression/
│
├── scripts/
│   ├── ingest_documents.py
│   └── run_evaluations.py
│
└── deployment/
    ├── docker/
    ├── monitoring/
    └── migrations/

```

## 3.1 Dependency rules

-   API handlers call application services; they do not contain
    orchestration or business rules.

-   Application services depend on domain interfaces and repository/tool
    interfaces, not vendor SDKs directly.

-   Agent nodes call application capabilities through explicit
    interfaces; they do not open database sessions ad hoc.

-   Tool adapters validate inputs and authorization before invoking an
    external integration.

-   Domain entities and policies must not import FastAPI, LangGraph,
    vector database or provider SDKs.

-   Prompts are version-controlled artifacts, reviewed like code, and
    evaluated before release.

-   Background ingestion must not share unbounded resource pools with
    latency-sensitive chat requests.

# 4. Request lifecycle and workflow state machine

## 4.1 End-to-end request sequence

1.  API receives request; validates schema, authentication, payload
    size, rate limit and request idempotency where applicable.

2.  Chat service resolves the customer and conversation under
    authorization and loads bounded history or a summary.

3.  Workflow classifies intent into a finite, versioned taxonomy and
    validates the classifier output.

4.  Router chooses a supported path: knowledge retrieval, read-only
    business tool, approved action workflow, clarification, or human
    handoff.

5.  Retrieval/tool layer returns typed evidence including source IDs,
    timestamps, status and provenance.

6.  Response policy checks whether evidence is sufficient, conflicts
    exist, action result is verified and escalation is required.

7.  Response generator produces a customer-facing answer from evidence
    and policy constraints.

8.  Service persists message, citations, workflow outcome and minimal
    execution metadata in a transaction or well-defined sequence.

9.  API returns response and correlation identifiers; telemetry is
    emitted without leaking sensitive payloads.

## 4.2 State model

| State field | Type / example | Purpose |
|---|---|---|
| conversation_id | UUID/string | Stable conversation identity. |
| customer_id | Authenticated principal ID | Derived from trusted auth context; never accepted as authority from free text. |
| message | String | Current user message, subject to size and content controls. |
| intent | Enum | knowledge_question, order_status, ticket_request, action_request, unknown. |
| history_summary | Optional bounded string | Compressed context; not authoritative business state. |
| retrieved_evidence | List\[Evidence\] | Source ID/version, excerpt, score and access metadata. |
| tool_result | Optional typed result | Validated response status and approved fields. |
| needs_clarification | Boolean + reason | Missing details or ambiguity. |
| needs_human | Boolean + reason | Policy, risk, uncertainty or repeated failure. |
| response | String + citations | Final response candidate. |
| workflow_version | String | Version for audit/evaluation reproducibility. |

## 4.3 Routing rules

| Condition | Route | Guardrail |
|---|---|---|
| FAQ/policy/product guidance | Knowledge retrieval | Use authorized approved sources; abstain if evidence is insufficient. |
| Order/account status | Read-only business tool | Bind customer identity server-side and query authoritative system. |
| Ticket creation | Ticket tool | Validate required fields; prevent duplicates; return ticket ID only after confirmation. |
| Refund/cancel/account modification | Action-specific approval flow | Check policy, eligibility, confirmation and/or human approval before write. |
| Ambiguous request | Clarification | Ask only for required missing information; avoid collecting unnecessary PII. |
| Sensitive, unsupported, conflicting or repeated failure | Human escalation | Create complete handoff context and stop unsafe automated action. |

## 4.4 Workflow invariants

-   A conversation cannot access another customer's records solely
    because an ID appears in a message or model output.

-   A tool call cannot exceed the current allowlist, schema, policy and
    authorization context.

-   The workflow has configurable maximum model/tool iterations, maximum
    elapsed time and token/cost budgets.

-   A write action's final status is based on the system of record, not
    the LLM's interpretation.

-   If a write result is ambiguous after a timeout, the state is
    unknown/pending until reconciled; do not blindly repeat.

-   Retrieved documents are evidence, not instructions that can override
    system policy or application authorization.

# 5. Component designs and contracts

## 5.1 API layer

| Component | Responsibilities |
|---|---|
| Chat API | Accept user message; enforce auth and request validation; call ChatService. |
| Conversation API | Return authorized conversation history and status with pagination and redaction. |
| Ticket API | Expose ticket state and handoff operations subject to role permissions. |
| Feedback API | Record optional feedback with rate limits and privacy controls. |
| Health API | Provide liveness/readiness checks without exposing secrets or dependency internals. |

## 5.2 ChatService

-   Own the use-case transaction boundary: load authorized context,
    invoke workflow, persist outcome and shape response.

-   Enforce request budgets and workflow timeouts.

-   Attach a correlation ID and immutable execution identifiers.

-   Convert internal exceptions into stable domain errors; never expose
    stack traces to customers.

-   Keep HTTP concerns out of agent nodes and external SDK concerns out
    of business rules.

## 5.3 Agent orchestrator

-   Build and compile the LangGraph workflow at application startup.

-   Use typed state and explicit conditional edges; avoid arbitrary
    dynamic tool names from model output.

-   Separate classification, retrieval, tool execution, response
    drafting and policy validation.

-   Support checkpoints only where required for durable resume or
    human-in-the-loop workflows; define checkpoint retention and access
    control.

-   Record model name/version, prompt version, workflow version,
    retrieval settings and tool outcomes in trace metadata.

## 5.4 Knowledge service

-   Ingestion: discover source, parse, normalize, chunk, attach
    metadata, embed, index and record status/version.

-   Retrieval: enforce source/customer/role filters before or during
    search; combine sparse/dense retrieval if evaluation supports it.

-   Reranking: use only when measured improvement justifies added
    latency/cost.

-   Citation builder: map retrieved chunks to stable source IDs, title,
    version and page/section when available.

-   Freshness controls: detect changed/deleted source versions and
    prevent obsolete content from remaining active indefinitely.

-   Conflict handling: flag contradictory policy documents and route to
    a content owner or abstain when precedence is not deterministic.

## 5.5 Tool registry and adapters

-   Each tool declares name, description, input schema, risk tier,
    required permissions, timeout, retry policy, idempotency behavior
    and result schema.

-   Only explicitly registered tools can be called. No arbitrary Python
    execution, raw SQL or unrestricted HTTP request tool is exposed.

-   Tool handlers derive customer identity from trusted request context
    and re-check authorization at execution time.

-   External responses are validated and normalized; secrets, internal
    errors and unauthorized fields are not passed to the LLM.

-   Write operations emit an audit event with actor, action, resource,
    outcome and correlation ID.

## 5.6 Integration adapters

-   LLM adapter: normalize structured output, timeouts, rate-limit
    errors, token usage and provider exceptions.

-   Vector adapter: expose upsert, delete/version, filtered search and
    health operations without leaking provider-specific response
    objects.

-   CRM/ticketing adapters: isolate authentication, API schemas,
    pagination, rate limits, retries and external ID mapping.

-   Use contract tests with recorded or sandbox responses; avoid making
    unit tests depend on live third-party services.

# 6. API design

The following REST endpoints are a proposed versioned contract. Final
authentication mechanism, public exposure and channel-specific semantics
require approval.

| Method / path | Purpose | Notes |
|---|---|---|
| POST /api/v1/chat | Submit message and receive answer | Requires authenticated principal or approved anonymous policy; supports idempotency where appropriate. |
| GET /api/v1/conversations/{id} | Fetch conversation summary/history | Authorization and pagination required. |
| GET /api/v1/conversations/{id}/messages | Fetch messages | Paginated; redacted fields by default. |
| POST /api/v1/conversations/{id}/feedback | Submit feedback | Optional; validated enum/rating and size-limited comment. |
| GET /api/v1/tickets/{id} | Fetch ticket status | Must verify ticket access. |
| POST /api/v1/tickets | Create support ticket | May be internal-only or tool-mediated; idempotency and validation required. |
| GET /health/live | Process liveness | No dependency detail. |
| GET /health/ready | Readiness | Check critical dependencies according to startup policy. |

## 6.1 Example chat request

```
POST /api/v1/chat
Authorization: Bearer <token>
Idempotency-Key: <client-generated-key>

{
"conversation_id": "optional-existing-id",
"message": "Where is my order?",
"channel": "web"
}
```

## 6.2 Example chat response

```
{
"conversation_id": "conv_...",
"message_id": "msg_...",
"status": "completed",
"response": "Your order is currently in transit.",
"citations": [],
"handoff": null,
"correlation_id": "req_..."
}
```

The sample is illustrative. Do not expose internal chain-of-thought or
hidden reasoning. Return only customer-safe response text, appropriate
citations, user-relevant status and stable identifiers.

## 6.3 Error contract

```
{
"error": {
"code": "DEPENDENCY_UNAVAILABLE",
"message": "I couldn't retrieve that information right now.",
"retryable": true,
"correlation_id": "req_..."
}
}
```

-   Use consistent HTTP status codes and stable machine-readable error
    codes.

-   Never include credentials, internal stack traces, raw provider
    exceptions or sensitive data in public errors.

-   Distinguish validation errors, authentication/authorization
    failures, rate limiting, dependency failures and unknown write
    outcomes.

# 7. Data model and persistence

## 7.1 Logical entities

| Entity | Core fields | Notes / constraints |
|---|---|---|
| Customer mapping | id, external_subject, status, created_at | Avoid duplicating unnecessary profile/PII fields; external_subject uniqueness depends on identity provider. |
| Conversation | id, customer_id, status, channel, created_at, updated_at, assigned_owner | Customer-scoped authorization; explicit status lifecycle. |
| Message | id, conversation_id, role, content_ref/content, created_at, metadata | Define retention, redaction and attachment handling; avoid storing secrets. |
| Source document | id, source_uri, title, version, owner, status, checksum, updated_at | Versioned; status can be draft/approved/retired/failed. |
| Knowledge chunk | id, document_id, document_version, chunk_index, text_ref, metadata | Vector index must carry stable IDs and filterable ACL/version metadata. |
| Tool execution | id, conversation_id, tool_name, input_digest, status, started_at, finished_at, correlation_id | Store minimal payload; sensitive input may be hashed/redacted. |
| Ticket | id, external_ticket_id, conversation_id, status, priority, assigned_to | External system may be source of truth for ticket lifecycle. |
| Feedback | id, conversation_id, rating, comment, created_at | Optional, moderated and retention controlled. |
| Audit event | id, actor_id, action, resource_type, resource_id, outcome, timestamp, correlation_id | Append-only permissions preferred; exclude raw secrets. |
| Evaluation run | id, dataset_version, model_version, prompt_version, workflow_version, metrics, created_at | Supports release comparison and regression review. |

## 7.2 Persistence rules

-   Use Alembic migrations for schema changes; migrations are reviewed
    and tested against representative data.

-   Use database transactions for related local writes; define behavior
    where external API calls cannot participate in the transaction.

-   Use repository methods that require an explicit authorized scope for
    customer-owned records.

-   Add indexes for conversation/customer/time lookups, message
    ordering, ticket status and idempotency keys as supported by query
    patterns.

-   Define deletion/retention workflows across primary database, vector
    index, logs, evaluation copies and backups; communicate backup
    deletion limits.

-   Do not rely on Redis as the only store for durable conversation or
    business state.

# 8. Knowledge ingestion and retrieval design

## 8.1 Ingestion pipeline

```
Discover source
-> validate type/size/permissions
-> parse and normalize
-> remove boilerplate / detect malformed extraction
-> chunk with source structure preserved
-> attach source ID, version, ACL, section/page, timestamps
-> embed
-> upsert into index
-> verify index count / sample retrieval
-> mark version active only after successful validation
```

## 8.2 Ingestion requirements

-   Make jobs idempotent using source ID, version/checksum and chunk
    identifiers.

-   Record per-document status, error details, duration, chunk count and
    embedding/index version.

-   Do not publish partially ingested versions; retain previous approved
    version until new version passes validation.

-   Handle source deletion and permission changes by
    deactivating/deleting corresponding index entries.

-   Use a separate worker/queue for heavy parsing and embedding; apply
    concurrency limits and retry budgets.

-   Preserve document title, section, page and URL/URI so citations can
    be rendered consistently.

## 8.3 Retrieval pipeline

1.  Normalize the query and identify intent; preserve important product
    names, IDs and exact terms.

2.  Apply mandatory authorization and document-status filters.

3.  Retrieve candidate passages using the selected search strategy
    (dense, sparse or hybrid).

4.  Optionally rerank candidates; choose top passages using measured
    quality/latency trade-offs.

5.  Check score/coverage thresholds and conflicting evidence; do not
    treat similarity score alone as calibrated confidence.

6.  Build an evidence package containing excerpts, stable source IDs,
    versions, titles and page/section metadata.

7.  Generate an answer constrained to evidence; validate citation
    references before returning.

## 8.4 Citation and abstention behavior

-   A citation must point to a real indexed source version and support
    the nearby claim.

-   Never fabricate a URL, page number, policy clause or source title.

-   If evidence is weak, missing or contradictory, ask a targeted
    clarification, explain the limitation or escalate.

-   Use live tools for volatile transactional facts; use documents for
    policy/process guidance.

-   Log retrieval configuration and source IDs for evaluation, subject
    to privacy and retention controls.

# 9. Tool execution and action safety

## 9.1 Tool contract

```
ToolDefinition:
name: stable allowlisted identifier
input_schema: strict typed schema
required_permissions: policy permissions
risk_tier: read_only | low_risk_write | high_impact_write
timeout_seconds: bounded value
retry_policy: bounded and operation-aware
idempotency: required where supported
output_schema: strict typed result
audit_policy: required fields and redaction rules
```

## 9.2 Execution sequence

1.  Validate requested tool name against registry.

2.  Validate arguments against schema and business constraints.

3.  Resolve authenticated actor/customer from trusted context; ignore
    model-supplied identity as an authority.

4.  Authorize actor, resource and operation; re-check current state for
    state-changing actions.

5.  Apply risk policy: allow, request customer confirmation, require
    human approval, or deny.

6.  Execute with scoped credentials, timeout, operation-aware retries
    and idempotency protection.

7.  Validate external response; reconcile ambiguous outcomes where
    possible.

8.  Persist audit metadata and return a minimal, typed result to the
    agent.

## 9.3 Initial tool catalogue

| Tool | Risk tier | Controls |
|---|---|---|
| search_support_knowledge | Read-only | Source ACL filters, approved content only, citation metadata. |
| get_order_status | Read-only | Customer/order relationship verified server-side; field allowlist. |
| get_customer_profile | Read-only / sensitive | Strong authentication and minimum field disclosure. |
| create_support_ticket | Write | Required-field validation, duplicate protection, ticket ID verification. |
| request_refund | High-impact write / approval flow | Eligibility checks, explicit confirmation, possible human approval, authoritative result verification. |
| change_account_details | High-impact write / approval flow | Step-up authentication where appropriate, field-specific policy and audit. |

Risk tiers and permitted operations must be approved by business and
security owners. A tool appearing in the catalogue does not mean it is
enabled in the first release.

# 10. Security and threat model

## 10.1 Threats and controls

| Threat | Design controls | Verification |
|---|---|---|
| Prompt injection in user or retrieved content | Untrusted-content boundaries, no prompt-based authorization, narrow tool schemas, output checks. | Adversarial red-team cases and regression tests. |
| Cross-customer data exposure | Trusted principal context, scoped repositories, tenant filters, object-level authorization. | Negative tests with forged IDs and cross-customer fixtures. |
| Unauthorized write action | Risk-tiered tool policy, explicit confirmation/approval, independent business validation. | Policy unit tests, integration tests and audit review. |
| PII/secret leakage | Data minimization, structured logging allowlist, redaction, secret manager. | Log scanning and synthetic sensitive-data tests. |
| Replay/duplicate write | Idempotency keys, operation state, external reconciliation. | Duplicate request and timeout-after-commit tests. |
| Compromised dependency | Pinned dependencies, image scanning, scoped credentials, egress controls where feasible. | CI security scans and periodic review. |
| Abuse / denial of service | Rate limits, request limits, concurrency controls, quotas and backpressure. | Load/abuse tests and alert validation. |
| Malicious or stale documents | Source approval, ACL metadata, versioning, ingestion validation and retirement. | Corpus poisoning, deletion and freshness tests. |

## 10.2 Security implementation requirements

-   Store secrets in the platform secret manager; .env is for local
    development only and must not be committed.

-   Use TLS in transit and managed encryption at rest; confirm key
    ownership and rotation requirements with the platform team.

-   Use separate identities and credentials for local, test, staging and
    production environments.

-   Apply least-privilege IAM and restrict network egress to required
    dependencies where practical.

-   Do not expose internal reasoning traces, raw prompts containing
    sensitive context, or raw tool payloads to customers.

-   Define a security incident runbook for data exposure,
    prompt-injection abuse and unauthorized action attempts.

# 11. Reliability, concurrency and performance

## 11.1 Timeouts and retries

-   Set separate timeouts for API requests, LLM calls, retrieval,
    CRM/ticketing calls and background jobs.

-   Use bounded exponential backoff with jitter for transient errors
    only; honor provider rate-limit guidance.

-   Do not automatically retry non-idempotent writes unless the
    integration provides idempotency or the outcome is reconciled.

-   Use circuit breakers or temporary dependency suppression when
    repeated failures would amplify load.

-   Set a maximum number of workflow steps, model calls, tool calls,
    elapsed time and tokens per request.

## 11.2 Concurrency and resource isolation

-   Use async I/O for network-bound API and integration operations where
    the client libraries support it safely.

-   Avoid blocking CPU-heavy parsing/embedding work in the interactive
    API event loop.

-   Use bounded connection pools for PostgreSQL, Redis and external
    APIs.

-   Apply queue backpressure and worker concurrency limits for
    ingestion.

-   Scale stateless API replicas horizontally; store durable
    conversation state in shared persistence/checkpoint storage.

-   Load-test realistic concurrent requests and long-tail dependency
    latency before selecting replica counts or autoscaling thresholds.

## 11.3 Degraded modes

| Dependency failure | Behavior |
|---|---|
| LLM provider | Return safe temporary error or approved fallback; never fabricate a confident answer. |
| Vector store | Use a validated fallback only if configured; otherwise clarify/escalate or return a safe unavailable response. |
| CRM/order API | Explain that live status is unavailable; do not infer it from old messages or documents. |
| Ticketing API | Record handoff intent only if durable and policy-approved; clearly state whether ticket creation is confirmed. |
| Redis | Continue only if rate limiting/cache/session semantics remain safe; otherwise apply defined fail-closed/fail-open policy. |
| Telemetry backend | Buffer or drop noncritical telemetry within limits; application request path must not hang on observability. |

# 12. Observability, evaluation and release gates

## 12.1 Telemetry

-   Use OpenTelemetry-compatible traces across API, ChatService, graph
    nodes, retrieval and tool adapters.

-   Include correlation ID, conversation ID (opaque),
    workflow/prompt/model versions, route, latency, token usage, status
    and error class.

-   Capture retrieval source IDs and tool names/outcomes where policy
    permits; redact content and sensitive identifiers.

-   Track request volume, p50/p95 latency, error/timeout rates, tool
    success, escalation, token/cost usage and queue depth.

-   Define dashboards, alert thresholds, on-call owner, severity mapping
    and runbook links before production launch.

## 12.2 Evaluation pipeline

1.  Maintain versioned datasets for knowledge questions, ambiguous
    cases, live-tool cases, policy boundaries, injection attempts and
    failure conditions.

2.  Run unit/integration tests on each change; run the relevant offline
    evaluation suite on prompt, model, retrieval or graph changes.

3.  Compare metrics against an approved baseline and flag regressions;
    critical security failures block release regardless of aggregate
    score.

4.  Use human review for groundedness, citation support, escalation
    appropriateness and high-impact action behavior.

5.  Sample production conversations under approved privacy controls and
    feed reviewed failures into regression datasets.

6.  Record evaluation report, dataset version, model/prompt/workflow
    versions and approval outcome for every release.

## 12.3 Release gates

| Gate | Required evidence |
|---|---|
| Code quality | Formatting/linting, type checks where adopted, dependency and secret scans. |
| Automated tests | Unit, integration, API, migration and contract tests pass. |
| Security | Authorization, injection, data isolation and action-policy tests pass; no unresolved critical/high finding without approved exception. |
| Evaluation | Approved correctness, groundedness, citation and escalation thresholds met; no critical regression. |
| Performance | Load and failure-injection results meet approved latency/throughput/error targets. |
| Operations | Dashboards, alerts, runbooks, backups, restore/rollback and on-call ownership verified. |
| Business acceptance | Support/Product owner signs off on representative journeys and handoff quality. |

# 13. Deployment, configuration and operations

## 13.1 Deployment topology

Container platform

-   API / application replicas

-   ingestion worker replicas (separate scaling policy)

-   scheduled maintenance/evaluation jobs (as required)

Managed dependencies

-   PostgreSQL

-   optional Redis

-   vector database

-   LLM provider endpoint

-   CRM / ticketing APIs

-   telemetry and log backend

-   secret manager / identity provider

## 13.2 Environment strategy

| Environment | Purpose | Rules |
|---|---|---|
| Local | Developer feedback and mocked integrations. | Synthetic data; no production secrets; Docker Compose where useful. |
| CI/test | Repeatable automated tests. | Ephemeral or isolated database/index; mock or sandbox external systems. |
| Staging | Production-like verification. | Separate credentials, representative configuration, synthetic or approved masked data. |
| Production | Customer traffic. | Least privilege, approved secrets, monitoring, rollback, change approval and restricted access. |

## 13.3 Configuration contract

```
APP_ENV=local|test|staging|production
LOG_LEVEL=INFO
DATABASE_URL=<secret-managed>
REDIS_URL=<optional-secret-managed>
LLM_PROVIDER=<configured-adapter>
LLM_MODEL=<approved-model>
LLM_TIMEOUT_SECONDS=...
VECTOR_STORE_PROVIDER=<configured-adapter>
VECTOR_INDEX_NAME=<environment-specific>
MAX_AGENT_STEPS=...
MAX_TOOL_CALLS=...
MAX_REQUEST_SECONDS=...
RATE_LIMIT_PER_MINUTE=...
OTEL_EXPORTER_ENDPOINT=<environment-specific>
```

The values above are illustrative names, not final settings. Validate
all settings at startup, fail fast for missing required configuration,
and never print secret values.

## 13.4 CI/CD and rollback

-   Build immutable versioned images; pin dependencies and record image
    digest.

-   Run tests, lint/type checks, migrations validation, dependency
    scans, secret scans and evaluation gates before promotion.

-   Promote the same tested image through environments with
    environment-specific configuration.

-   Apply backward-compatible expand/migrate/contract database changes
    where rolling deployment requires it.

-   Use staged/canary rollout when supported; monitor error, latency,
    safety and quality indicators.

-   Maintain a documented rollback path for application image,
    prompt/workflow version and retrieval/index version.

-   Do not automatically roll back data migrations that are not safely
    reversible; document recovery steps.

## 13.5 Operational runbooks

-   LLM provider outage or rate limiting.

-   Vector search quality drop or index corruption.

-   CRM/ticketing outage and ambiguous write result reconciliation.

-   Suspected customer data exposure or unauthorized tool execution.

-   High latency, runaway token use or traffic spike.

-   Failed ingestion, stale documents or source permission changes.

-   Database restore, region/service recovery and deployment rollback.

# 14. Testing strategy, traceability and open decisions

## 14.1 Test layers

| Layer | Coverage examples | Execution |
|---|---|---|
| Unit | Routing, policies, schema validation, citation validation, retry decisions, redaction. | Every commit. |
| Integration | Repositories, vector adapter, LLM adapter, CRM/ticketing sandbox, migrations. | CI and pre-release. |
| API/contract | Request/response schemas, auth, error shape, idempotency, pagination. | Every commit. |
| Agent workflow | Intent routes, missing evidence, conflicting evidence, tool error, human handoff. | Every workflow/prompt change. |
| Security | Prompt injection, cross-customer access, tool misuse, PII leakage, abuse limits. | CI plus scheduled security review. |
| Evaluation | Correctness, groundedness, citations, tool selection, escalation. | Every relevant model/config change. |
| Performance | Concurrent requests, long-tail latency, queue saturation, provider throttling. | Pre-pilot and before capacity changes. |
| Resilience | Dependency outage, timeout after write, duplicate requests, telemetry failure. | Pre-production and periodically. |
| Acceptance | End-to-end customer journeys with Support/Product. | Pilot and release sign-off. |

## 14.2 BRD-to-design traceability

| BRD requirement | Primary design location | Evidence |
|---|---|---|
| BR-001 / BR-002 | API, ChatService, Conversation repository | API tests and persistence integration tests. |
| BR-003 / BR-004 / BR-009 | Knowledge service, citations, response policy | Golden-set evaluation and citation review. |
| BR-005 / BR-006 / BR-007 | Tool registry, authorization, adapters, result verification | Tool contract tests, negative authorization tests and write reconciliation tests. |
| BR-008 | EscalationService, ticket adapter, workflow route | Handoff acceptance tests. |
| BR-010 / BR-016 | Security modules, logging/redaction, retention jobs | Threat tests, log scans and deletion tests. |
| BR-011 / BR-017 | Observability, rate limiting, budgets | Dashboard/alert validation and load tests. |
| BR-013 | Evaluation runner and CI/release gates | Versioned evaluation report per release. |
| BR-014 / BR-018 | Deployment, runbooks, degraded modes | Restore drill and failure-injection results. |

## 14.3 Open architecture decisions

| ID | Decision | Options / evaluation criteria | Owner |
|---|---|---|---|
| ADR-001 | LLM provider/model | Quality, latency, cost, data terms, structured output, regional availability. | Architecture + Security |
| ADR-002 | Vector store | Existing Pinecone, pgvector or another managed store; evaluate ACL filters, ops and retrieval quality. | Architecture |
| ADR-003 | Identity | Existing OIDC/OAuth provider, customer session model and service-to-service auth. | Security + Product |
| ADR-004 | Ticketing/CRM integration | Vendor APIs, sandbox, webhook behavior, rate limits, idempotency and ownership. | Business system owner |
| ADR-005 | Human handoff | Ticket creation vs live transfer; agent console and ownership state. | Support + Product |
| ADR-006 | Retention and residency | Messages, traces, embeddings, backups, evaluation samples and deletion semantics. | Privacy/Legal + Platform |
| ADR-007 | State/checkpointing | PostgreSQL-backed conversation state and whether durable LangGraph checkpointing is required. | Architecture |
| ADR-008 | Deployment platform | Managed containers initially; Kubernetes only if operational requirements justify it. | Platform/SRE |
| ADR-009 | Service-level targets | Availability, latency, throughput, RPO/RTO and cost ceiling. | Sponsor + Operations |

# Appendix A --- Illustrative interface contracts

## A.1 Evidence object

```
Evidence:
source_id: str
source_version: str
title: str
excerpt: str
section_or_page: optional[str]
source_uri: optional[str]
retrieval_score: optional[float]
access_scope: internal metadata; never trusted from model output
```

## A.2 Tool result object

```
ToolResult:
status: succeeded | pending | rejected | failed | unknown
operation_id: optional[str]
data: validated allowlisted fields
user_safe_message: optional[str]
retryable: bool
correlation_id: str
```

## A.3 Conversation lifecycle

-   open: new conversation accepts messages.

-   active: interaction is in progress.

-   pending_human: assigned or queued for human review; automated write
    actions are restricted according to policy.

-   resolved: support outcome recorded; reopen behavior is
    policy-defined.

-   closed: terminal state under retention policy; any reopening creates
    an explicit audited transition.

# Appendix B --- Definition of ready for production

-   Business requirements, action boundaries and measurable service
    levels approved.

-   All critical integrations have documented contracts, credentials,
    sandbox tests and operational owners.

-   Authentication, authorization, customer isolation, secret handling
    and retention tests pass.

-   Golden evaluation set is versioned and release gates are automated
    or formally documented.

-   Observability dashboards, alerts, runbooks and on-call ownership are
    operational.

-   Backup/restore and rollback procedures have been exercised.

-   Pilot feedback and known limitations are documented; Support/Product
    approves go-live.

-   No unresolved critical security or safety issue remains; any
    accepted residual risk has a named approver and expiry/review date.