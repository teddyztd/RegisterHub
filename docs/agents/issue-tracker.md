# Issue tracker

- Provider: GitHub Issues
- Repository: `teddyztd/RegisterHub`
- Original upstream: `waw666waw666/RegisterHub`

## Specifications

Create one issue per approved specification. Apply the `spec` and `ready-for-agent` labels. The issue body is the authoritative spec used by implementation and review.

## Implementation tickets

Create one issue per vertical ticket. Apply the `ticket` and `ready-for-agent` labels. Put `Blocked by: #<issue>` in the body for every blocking dependency; omit that line when the ticket is ready immediately. Close a ticket only after its acceptance criteria are verified and its changes are merged into the integration branch.

## Local mapping

Keep the feature slug and integration branch name in the spec issue. Record the integration branch and final verification in the relevant issues so the GitHub state remains sufficient to resume work.
