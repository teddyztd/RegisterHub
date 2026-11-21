# Repeatable Local CLI Deployment Verification

## Problem

RegisterHub has working installation instructions and an offline demo, but a new operator must manually coordinate virtual-environment creation, dependency and browser installation, configuration, diagnostics, tests, and demo verification. The existing `main.py --run demo` command does not expose adapter success through its process exit code, so a zero exit status alone cannot prove deployment health. Verification can also pollute the normal account ledger if it uses the default output directory.

## Solution

Add a cross-platform `scripts/deploy_check.py` entry point that prepares or reuses the local `.venv`, installs dependencies and Playwright Chromium, preserves operator configuration, runs diagnostics and tests, and executes the built-in demo in an isolated temporary working directory. The checker succeeds only when every command succeeds and the isolated demo produces a non-empty credential ledger. Document the one-command workflow and its verification contract in the README.

## User Stories

- As a new operator, I can run one Python command from a clean checkout to prepare and verify a local CLI deployment.
- As an existing operator, I can rerun the checker without losing my `config.json`, proxy, mail, or browser preferences.
- As an operator repeating a check on a prepared machine, I can use `--skip-install` to avoid dependency and browser installation while retaining all verification gates.
- As a maintainer, I receive a non-zero exit status and a clear failing stage when setup, diagnostics, tests, or the offline demo fails.
- As a maintainer, I can verify demo credential output without modifying the normal `results/accounts.txt` ledger or retaining temporary credentials.

## Implementation Decisions

- Add `scripts/deploy_check.py`, executable with the system Python and with the project virtual-environment Python.
- When launched outside `.venv`, create `.venv` if needed and re-execute the checker with its interpreter. Avoid recursive re-execution once inside the environment.
- Unless `--skip-install` is supplied, run `python -m pip install -r requirements.txt` and `python -m playwright install chromium` using the selected virtual-environment interpreter.
- If root `config.json` is missing, derive it from `config.example.json` and set `browser.headless` to `true`; never overwrite an existing root configuration.
- Run `main.py doctor` and `pytest tests/` from the repository root and stop at the first failed blocking stage.
- Run `main.py --run demo` from a temporary working directory with an isolated configuration that forces headless mode and a temporary `output_dir`.
- Treat demo success as requiring both a successful subprocess and a non-empty `accounts.txt` containing credential data. Clean the temporary directory after the check.
- Keep the existing runner behavior of preferring Google Chrome and falling back to Playwright Chromium; surface the runner's browser messages rather than introducing a second browser-selection policy.
- Print concise stage progress and a final success summary; return non-zero on any failed stage.
- Add focused automated tests for configuration derivation, command failure propagation, isolated demo validation, and argument handling. Perform the final acceptance through the real CLI, including actual browser startup.
- Update `README.md` with full setup, `--skip-install`, output-isolation, and failure-behavior documentation. Keep `GLOSSARY.md` and `docs/adr/0001-local-cli-deployment.md` aligned with this terminology.

## Testing Decisions

- The highest-level seam is the real command `python scripts/deploy_check.py`, not a mocked helper.
- Unit/integration tests may mock subprocesses for fast failure-path coverage, but final acceptance must run the actual checker with real dependencies, diagnostics, pytest, and the offline browser demo.
- Acceptance requires a zero checker exit code, all existing and new tests passing, and a non-empty isolated demo ledger observed before cleanup.
- Run the checker again with `--skip-install` and confirm the normal root configuration is unchanged and no verification credentials are appended to the normal `results/accounts.txt`.
- No real third-party registration, external mailbox, proxy, or production credential is required.

## Out of Scope

- Server, container, hosted-service, or public-port deployment.
- New site adapters or real third-party account registration.
- Changes to the normal runner's account-ledger format or adapter exit-code API.
- Automatic concurrency, CAPTCHA services, proxy provisioning, or real mailbox setup.
- Rewriting an existing operator configuration or retaining temporary demo credentials.

## Further Notes

- GitHub Issues in `teddyztd/RegisterHub` is the issue tracker. This spec and derived tickets use the agreed labels and `Blocked by #n` links.
- The final `/code-review` fixed point is upstream clone HEAD `8a8d6f4128a7da18bd894c96f76a609637ae8f8a`.
- The verified local runtime baseline is Windows with Python 3.14.6, Playwright 1.65.2, and Google Chrome with Playwright Chromium installed as fallback.
