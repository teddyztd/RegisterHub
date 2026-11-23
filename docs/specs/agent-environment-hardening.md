# Agent Environment Hardening

## Problem Statement

RegisterHub now has meaningful automated tests and a repeatable deployment check, but those checks are not enforced by CI or a local Git hook. The session also exposed operational gaps: removing a worktree can destroy ignored live credentials, mailbox polling can wait for minutes without explaining why a received message was rejected, and real-run scripts can start with missing credentials, incompatible console encoding, or an unusable proxy exit.

## Solution

Add a small set of deterministic agent-environment guardrails. Every push and pull request runs the existing tests; an opt-in Git hook runs them before commit. A safe worktree cleanup command protects or archives ignored live artifacts. Mailbox polling reports sanitized rejection diagnostics. A read-only preflight checks real-run prerequisites without creating an account.

## User Stories

1. As a maintainer, I want tests to run on every push and pull request so regressions cannot merge silently.
2. As a contributor, I want an optional repository-provided pre-commit hook so the same quick test gate runs locally.
3. As a maintainer, I want CI and local checks to use the existing pytest suite so there is one source of truth.
4. As an operator, I want worktree cleanup to detect ignored accounts, cookies, and pending-activation records before deletion.
5. As an operator, I want to archive those artifacts to an explicit destination before removing a worktree.
6. As an operator, I want cleanup to refuse deletion while unarchived live artifacts remain.
7. As an operator, I want cleanup to support a non-mutating check mode.
8. As a developer, I want mailbox polling to report provider, message count, and safe rejection reasons.
9. As a developer, I want unsupported confirmation links to name the rejected scheme, host, or path without exposing tokens.
10. As a developer, I want credentials, cookie values, message bodies, and confirmation tokens kept out of diagnostics.
11. As an operator, I want preflight to check UTF-8 settings before a real run.
12. As an operator, I want preflight to check 215.im credentials through a read-only API.
13. As an operator, I want preflight to check the selected APIrf network path through a read-only endpoint.
14. As an operator, I want preflight to return nonzero on blocking failures and never create an APIrf account.
15. As a maintainer, I want each guardrail tested through its existing pytest or real CLI seam.

## Implementation Decisions

- Add one CI workflow for pushes and pull requests on the main branch.
- Add a repository-provided Git hook and document the one-time opt-in command; do not change the user's global Git configuration automatically.
- Add a safe worktree cleanup CLI with check mode, explicit archive destination, and refusal when live artifacts would be lost.
- Treat ignored accounts, cookie sidecars, and pending-activation records as protected artifacts; offline demo output alone does not require archiving.
- Add sanitized structured mailbox diagnostics at the existing polling boundary; redact credentials and tokens by design.
- Add a preflight CLI that performs only read-only third-party calls and never invokes registration.
- Keep APIrf single-account execution and existing adapter behavior unchanged.
- Use standard-library Python and existing project dependencies; do not add a new application framework.

## Testing Decisions

- Test external behavior: process exit codes, emitted diagnostics, filesystem protection, and read-only HTTP interactions.
- Prefer the existing pytest suite and real CLI entry points over implementation-specific assertions.
- Use temporary Git repositories and local fake HTTP sessions for deterministic tests.
- Include negative cases: unarchived artifacts, secret-free diagnostics, malformed links, missing key, bad encoding, and unavailable network path.
- The full existing suite must remain green.

## Out of Scope

- P2/P3 retro candidates, including broad coding-standards refactoring and AGENTS.md restructuring.
- Automatic Clash node switching or pressure-test orchestration.
- Changes to APIrf registration, activation, or credential acceptance rules.
- Creating accounts during preflight or cleanup verification.

## Further Notes

This spec implements only the P0 and P1 candidates approved after `/retro`. Secrets and live account artifacts remain local and ignored by Git.
