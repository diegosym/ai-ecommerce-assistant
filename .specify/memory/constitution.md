<!--
Sync Impact Report
==================
Version change: 2.1.0 → 2.1.1
Bump rationale: PATCH — targeted clarifications resolving independent audit
findings F-1 through F-6; no principle added, removed or redefined, no
existing requirement weakened, structure and governance model unchanged.

Modified content (audit finding → change):
- F-1 (P1, Principle IV): evaluation gates now require every new AI
  capability to establish and document its own initial baseline before
  integration, even when the repository already contains other AI
  capabilities and baselines; the distinction from regression evaluation
  against the approved baseline for subsequent changes is preserved.
- F-2 (P2, Governance): trivial-change criteria clarified — semantic-
  preserving spelling, grammar, formatting and wording corrections may
  qualify as no behavior change; changes altering user-facing meaning,
  instructions, contractual commitments, AI behavior or other functional
  outcomes do not qualify as trivial.
- F-3 (P2, Principle IV): evaluation-regression exception authority
  defined — explicitly documented and approved by the user or designated
  project maintainer before integration, recording the reason, scope and
  accepted risk.
- F-4 (P3, Principle VI): duplicate sensitive-action human-approval rule
  consolidated into one authoritative normative statement (bullet list);
  examples and all security requirements preserved.
- F-5 (P3, Principle I): "portfolio" wording generalized so the
  constitution remains applicable to independent AI application
  repositories.
- F-6 (P3, Development Workflow): documentation maintenance clarified —
  relevant documentation MUST be maintained and updated, or removed when
  obsolete; the "no documents nobody reads" constraint preserved.

Added sections: none.
Removed sections: none.
Follow-up TODOs: none. Audit findings F-7, F-8 and F-9 are intentionally
not addressed (excluded from this amendment).
-->

# AI Engineering Project Constitution

## Core Principles

### I. Product-Oriented Engineering

Every feature MUST solve a concrete, documented user or business problem,
and the specification MUST name that problem explicitly. Functional
applications take priority over isolated technology demonstrations: a
capability that cannot be exercised end-to-end by a user MUST NOT be
considered complete.

Rationale: product and user value comes from working applications, not
from demonstrations of technology in isolation.

### II. Specification-First Development

Requirements, acceptance criteria and technical design MUST be documented
and explicitly approved by the user before implementation begins, except
for trivial changes as defined in Governance (Proportional application).
Traceability MUST be maintained between specifications, tasks, code and
tests: every task and test maps to a specification element, and when
implementation diverges from the specification, the specification MUST be
amended and re-approved, or the divergence MUST be documented.

This principle is the authoritative location for the
approval-before-implementation rule; other sections reference it.

Rationale: documented, approved specs make work reviewable and let tests
verify intent instead of implementation details.

### III. Incremental Delivery

Features MUST be delivered as small increments that are each
independently testable and demonstrable. Unnecessary abstractions,
frameworks and infrastructure MUST be avoided, and premature optimization
MUST be avoided; complexity MUST only be added when a measured need
justifies it.

This principle is the authoritative location for avoiding unnecessary
frameworks, infrastructure and abstractions; Additional Constraints
references it.

Rationale: small increments keep feedback loops short, make regressions
easy to isolate, and keep every change reversible.

### IV. AI Quality by Design (NON-NEGOTIABLE)

Every AI capability MUST have measurable evaluation criteria appropriate
to its use case, defined before implementation. Evaluation MUST cover the
relevant dimensions for the use case: accuracy, relevance, groundedness,
retrieval quality, reliability and consistency. Eval results MUST be
recorded together with the dataset and configuration that produced them,
and a change MUST NOT ship if it regresses the established baseline.

Evaluation gates:

- Every new AI capability MUST establish and document its own initial
  evaluation baseline before integration, even when the repository
  already contains other AI capabilities and baselines.
- Subsequent relevant changes to that capability MUST be evaluated
  against its approved baseline.
- Applicable evaluations MUST run before integration.
- CI automation MUST be used when CI infrastructure is available and
  configured for the repository.
- A regression MUST block integration unless an explicit, documented
  exception is approved by the user or designated project maintainer
  before integration, recording the reason, scope, and accepted risk.
- Evaluation and test results MUST NOT be invented or claimed without
  evidence (authoritative rule in Principle V).

Evaluation dataset governance (applied proportionally to risk):

- Evaluation datasets MUST be versioned.
- Datasets MUST provide representative coverage of the relevant use
  cases.
- Evaluation and development data MUST be separated when appropriate.
- Evaluation data contamination MUST be protected against.
- Dataset updates MUST be documented.

Rationale: without predefined, measurable criteria AI behavior is
unverifiable and quality regressions ship unnoticed.

### V. Reproducibility and Observability

Datasets, configurations, model versions and experiment procedures MUST
be documented well enough for a reported result to be reproduced.
Latency, token consumption, errors and costs MUST be measured and
recorded for AI workloads.

Reproducibility MUST include versioning or recording of the relevant:

- model identifiers and versions,
- prompt templates,
- evaluation configurations,
- dataset versions.

For non-deterministic evaluations, repeated runs or variance analysis
MUST be used when necessary to support reliable conclusions.

Reported benchmark, evaluation and test results MUST come from recorded,
reproducible runs: results MUST NOT be fabricated and MUST NOT be claimed
without evidence. This principle is the authoritative location for the
no-fabrication rule; other sections reference it.

Rationale: undocumented or unmeasured results cannot be trusted,
compared, or defended to a user or reviewer.

### VI. Security and Responsible AI (NON-NEGOTIABLE)

Credentials and sensitive information MUST be protected and MUST NOT be
committed to the repository. Inputs MUST be validated; access follows
least privilege and authorization checks; prompt-injection defenses MUST
be applied at trust boundaries.

LLM and agent security MUST additionally:

- validate and sanitize model outputs before using them;
- validate tool-call arguments against schemas and authorization rules
  before execution, and MUST NOT trust LLM-generated tool arguments by
  default;
- apply least-privilege permissions to tools and agents;
- require human approval for sensitive or consequential actions before
  execution.

Sensitive actions include, at a minimum: payments and financial
transactions, irreversible deletions, external communications, and
permission changes.

Data privacy MUST additionally:

- minimize collection and exposure of personal information;
- define and follow appropriate retention and deletion practices;
- document data shared with external model providers.

Rationale: an AI application acts on user data and external systems, so
security failures here are irreversible and affect people outside the
repository.

## Additional Constraints

- Provider-independent architectures are preferred when justified;
  any provider-specific coupling MUST be justified by a documented
  trade-off.
- Unnecessary frameworks, infrastructure and abstractions MUST be
  avoided (authoritative rule in Principle III).
- Datasets MUST have documented provenance and authorization. Explicit
  user approval is REQUIRED before using private or production data
  (data privacy requirements in Principle VI).
- Reported benchmark and evaluation results MUST follow Principle V
  (no fabricated or unevidenced results).
- Documentation MUST be concise and useful — no documents that nobody
  reads or maintains.
- Architectural decisions and their trade-offs MUST be documented
  (decision records) when they are significant or hard to reverse.

## Development Workflow

- Follow the installed Spec Kit workflow for all feature work.
- Specification and approval requirements follow Principle II; trivial
  changes as defined in Governance MAY bypass the full lifecycle.
- Relevant automated tests and quality checks MUST be executed for every
  change, and their results reported honestly (no unevidenced claims,
  per Principle V).
- When architecture or behavior changes, relevant documentation MUST be
  maintained and updated, or removed when obsolete.
- AI functionality MUST be validated using evaluation methods appropriate
  to its use case (per Principle IV).
- Commits, pushes, deployments and destructive operations REQUIRE
  explicit user approval and MUST NOT be executed without it.

## Governance

This constitution supersedes all other practices for this repository.
Specifications, plans, code and reviews MUST comply with it; a conflict
between this constitution and any other document resolves in favor of
this constitution.

- **Proportional application**: these principles MUST be applied
  proportionally to feature complexity and risk. A change is trivial and
  MAY bypass the full specification and approval lifecycle only when it
  satisfies ALL of the following, judged by risk and impact rather than
  lines of code:
  - it does not change externally observable behavior;
  - it does not modify security boundaries or permissions;
  - it does not modify public contracts or data schemas;
  - it does not affect AI behavior, prompts, models or evaluation;
  - it is easily reversible.

  Semantic-preserving corrections — spelling, grammar, formatting, and
  wording that do not change intended meaning or functionality — MAY be
  treated as satisfying the first criterion. Corrections that alter
  user-facing meaning, instructions, contractual commitments, AI
  behavior, or other functional outcomes do NOT qualify as trivial.

  All other changes MUST follow the appropriate specification and
  approval process. The non-negotiable principles (IV, VI) always apply.
- **Amendment procedure**: amendments MUST be documented and justified
  (what changes, why, migration impact), approved by the maintainer, and
  applied to this file with a version bump and a Sync Impact Report.
- **Low-impact decisions**: low-impact and reversible implementation
  decisions MUST be resolved during implementation or review without
  unnecessary escalation or approval gates.
- **Escalation**: significant architectural, security, or irreversible
  decisions MUST be escalated to the user before being made.
- **Versioning policy**: semantic versioning — MAJOR for removing or
  redefining principles (backward-incompatible governance), MINOR for
  adding or materially expanding a principle or section, PATCH for
  clarifications, wording, and typo fixes.
- **Compliance review expectations**: every Spec Kit gate and code review
  MUST verify compliance with the applicable principles; violations are
  blocking. Deferred items are tracked as `TODO(FIELD)` markers in this
  file and MUST be resolved or explicitly accepted before the next MINOR
  or MAJOR bump.

**Version**: 2.1.1 | **Ratified**: 2026-11-25 | **Last Amended**: 2026-11-25
