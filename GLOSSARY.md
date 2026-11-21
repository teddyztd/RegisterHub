# RegisterHub

RegisterHub is a local account-lifecycle automation framework. This glossary fixes the language used for deployment and verification.

## Language

**Deployment**:
Preparing one local machine so the RegisterHub command-line application can run its offline demonstration and test suite.
_Avoid_: Server release, hosted service

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
