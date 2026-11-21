# Domain context

RegisterHub uses a **single-context** domain model: the CLI, core services, site adapters, and tests share one vocabulary and one architecture-decision history.

## Vocabulary

Read and maintain `GLOSSARY.md` when introducing, renaming, or deprecating domain terms. Prefer existing terms in code and documentation before adding synonyms.

## Architecture decisions

Record consequential architecture choices as ADRs under `docs/adr/`, numbered sequentially (`0001-title.md`). An ADR captures context, decision, consequences, and status. Update or supersede an existing ADR rather than creating contradictory parallel decisions.

## Change boundary

Site-specific behavior belongs in the relevant `sites/` adapter; reusable runtime behavior belongs in `core/`; command-line behavior belongs in `main.py`. Tests must exercise the highest practical public seam and use the repository's offline demo for deployment verification.
