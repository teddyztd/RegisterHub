# RegisterHub

RegisterHub is a local account-lifecycle automation framework. This glossary fixes the language used for deployment and verification.

## Language

**Deployment**:
Preparing one local machine so the RegisterHub command-line application can run its offline demonstration and test suite.
_Avoid_: Server release, hosted service

**Deployment Checker**:
The `scripts/deploy_check.py` entry point that prepares or reuses `.venv`, optionally installs dependencies and Playwright Chromium, preserves or derives configuration, and gates deployment on diagnostics, tests, and the isolated Demo. `--skip-install` omits only installation, not the verification gates.
_Avoid_: Demo-only success check, server deployment pipeline

**Verification Run**:
A single, isolated execution that checks the environment, tests, and offline demonstration without changing normal account-ledger data.
_Avoid_: Production registration, live signup

**Demo**:
The built-in offline site adapter used to prove that browser automation and credential-ledger writing work end to end.
_Avoid_: Real site, production account

**Account Ledger**:
The local record of credentials produced by a successful adapter run; verification-run credentials are temporary check artifacts, not durable accounts.
_Avoid_: Database, remote credential store

**Browser Preference**:
The policy of using installed Google Chrome first and falling back to Playwright Chromium when Chrome is unavailable.
_Avoid_: Chrome requirement, Chromium-only mode

**APIrf Guest**:
A temporary APIrf session created by the guest endpoint. It is not a successfully registered account until login, password, and email are bound and the email is confirmed.
_Avoid_: Registered account, verified account

**APIrf Registration**:
The complete guest creation, credential binding, email confirmation, and authenticated identity-verification flow for one account. Only an identity response with `email_verified=true` and `is_guest=false` is successful.
_Avoid_: Email sent, guest session created

**Pending Activation**:
An account whose guest and binding steps may have succeeded but whose email confirmation or identity verification is incomplete. Recovery data is retained separately from the successful Account Ledger.
_Avoid_: Successful account, disposable failed attempt

**Mailbox Route**:
The APIrf mailbox policy: 215.im is the only provider, because APIrf never delivers confirmation mail to public disposable domains. A missing 215.im key fails the run before any APIrf request. The route must not switch to another address after submission.
_Avoid_: Arbitrary mailbox retry, public temporary-mail fallback, fabricated local address

**Cookie Sidecar**:
The per-account standard Cookie JSON array written under `results/cookies/` from the same HTTP session used for registration and identity verification.
_Avoid_: Browser storage state, account-ledger delimiter payload

**Rejection Diagnostics**:
The sanitized record emitted when mailbox polling receives a message that contains no supported confirmation link: provider, safe message metadata, and per-link rejection reasons (scheme, host, token-free path). Tokens, credentials, cookie values and message bodies are never included.
_Avoid_: Raw email body, error dump, credential echo

**Preflight**:
The read-only readiness check run before an APIrf live run (`python main.py preflight`): console UTF-8 encoding, the 215.im credential through a read-only inbox-listing probe, and the APIrf network path through an unauthenticated read-only endpoint. Every third-party request is a GET enforced by a session guard; a blocking failure exits non-zero. No guest, upgrade or registration is ever invoked.
_Avoid_: Dry-run registration, trial account creation, environment doctor
