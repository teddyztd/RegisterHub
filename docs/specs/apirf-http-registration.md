# APIrf HTTP registration and verified credential delivery

## Problem

RegisterHub has no APIrf adapter. A successful APIrf registration is not merely a guest session or a submitted email form: the account must bind login, password, and email, confirm the mailbox link, and pass authenticated identity verification. The user also needs the login and session Cookie JSON, which the current account ledger does not preserve.

## Solution

Add an automatically discovered `apirf` adapter that uses one `requests.Session` for guest creation, credential binding, the official email-confirmation request, and `/api/auth/me`. Add an explicit no-browser protocol path to the runner. Use 215.im as the primary mailbox provider, with mail.tm, tempmail.io, and guerrillamail as creation-time fallbacks. Preserve successful credentials in the existing ledger and write a standard Cookie JSON array per account. Preserve incomplete accounts separately as pending activation.

Feature slug: `apirf-http-registration`.
Integration branch: `feat/apirf-http-registration`.
Tracker: GitHub Issues in `teddyztd/RegisterHub`.

## User Stories

- As a local operator, I can run `python main.py --run apirf --count 1` to create and verify one real APIrf account without launching a browser.
- As an operator, I receive the account login, password, email, and a reusable Cookie JSON file only after verified activation.
- As an operator, I can distinguish pending activation from success and retain recovery information when mail confirmation times out.
- As a maintainer, I can test provider fallback, protocol sequencing, safe link extraction, identity gating, and Cookie export without live network calls.

## Implementation Decisions

- The observed endpoint sequence is `POST /api/auth/guest`, `POST /api/auth/guest/upgrade`, the emailed `GET /api/auth/email/confirm/<token>`, then `GET /api/auth/me`. Do not hardcode the recorded account, mailbox, Cookie, or confirmation token.
- Success requires an authenticated identity response with `email_verified=true` and `is_guest=false`. Mail sent, HTTP 200 alone, guest creation, or a non-empty response is not success.
- The same Session must carry cookies through confirmation and identity verification. Export `name`, `value`, `domain`, `path`, `expires`, `httpOnly`, `secure`, and `sameSite` where available to `results/cookies/<login>.json`.
- Keep the existing `email----password----username` ledger compatible. Preserve the APIrf login in the username field or an equivalent documented mapping; do not insert JSON into delimiter-separated records.
- Pending activation records live separately under the results directory and may include the bound credentials, mailbox recovery data, and failure stage. They are local sensitive artifacts and must not be committed.
- Mailbox order is 215.im, mail.tm, tempmail.io, guerrillamail. Failover is allowed before an address is submitted to APIrf; after submission, polling remains bound to that mailbox.
- The 215.im API key is read from local `config.json` or the environment, never committed or logged. Public-provider behavior follows the reference design but must not fabricate a local email address.
- Extract confirmation links from message text/HTML and accept only the intended APIrf HTTPS host and confirmation path. Ignore welcome, footer, tracking, and unrelated links.
- The protocol adapter path avoids Playwright startup. Existing browser adapters and their behavior remain unchanged.
- The first live acceptance run creates exactly one account. Captcha, access denial, 403, 429, or other rate limiting stops the run with a clear error; no bypass or automatic retry storm.
- Bulk creation and pressure testing are separate, later decisions requiring explicit approval after the single-account run.

## Testing Decisions

- Highest-level acceptance seam: the real CLI command `python main.py --run apirf --count 1`, with one live account, verified `/api/auth/me` state, a ledger credential record, and a non-empty valid Cookie JSON sidecar.
- Unit tests use fake Session/mailbox implementations to verify request order, payloads without fixed secrets, Session reuse, response validation, and stop-on-failure behavior.
- Mailbox tests cover provider-order fallback before submission, no provider switching after submission, message polling, and strict APIrf confirmation-link extraction.
- Runner/export tests cover the no-browser path, compatible ledger output, pending-activation separation, and complete Cookie sidecar serialization using temporary directories.
- Discovery and existing regression tests must continue to pass. The existing `scripts/deploy_check.py --skip-install` must remain green.
- Live acceptance is not replaced by mocks and must not create multiple accounts. The live test stops immediately on captcha or rate limiting.

## Out of Scope

- Creating an APIrf API key after registration; the recorded account had no user keys and the user did not request key creation.
- Multi-account pressure testing, captcha bypass, proxy rotation, or evading IP limits.
- Changing unrelated site adapters or the established account-ledger format.
- Committing credentials, cookies, mailbox tokens, recorded activation links, or local configuration.
- Hosted deployment, a web service, or a scheduler.

## Further Notes

- Recording evidence: local recorder run `rec_22_09-45-43`; it contains secrets and is evidence only, never repository content.
- Public reference: `waw666waw666/deepgram-register` mailbox backend design. Its known local-address fallback and overly broad URL extraction must not be copied.
- Public 215.im documentation: https://vip.215.im/docs. Actual quota and provider acceptance are established only by the authorized single live run.
- Domain language: `GLOSSARY.md`. Architectural rationale: `docs/adr/0002-apirf-http-registration.md`.
