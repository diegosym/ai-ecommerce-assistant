# ADR 0004: Keep conversation state ephemeral and client-held

## Status

Accepted (2026-11-25).

## Context

Requirements mandate reset on reload/new conversation and prohibit cross-visit memory. Server sessions or cookie/localStorage persistence would add retention, lifecycle, and privacy concerns.

## Decision

Keep bounded `ConversationState` in browser memory and send it with each interaction. Validate every field server-side, apply same-slot replacement and stable ordinal rules, and never persist conversation history. New conversation/reload replaces the entire state and ID.

## Consequences

- Reset semantics are simple and testable; no session database or cookies are needed.
- Every request carries bounded state and the server remains stateless.
- Telemetry retains only operational metadata and an ephemeral aggregation ID, not raw conversation content.
- Multi-device/history restoration is intentionally unsupported.
