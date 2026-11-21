# Deploy RegisterHub as a verified local CLI

RegisterHub is a command-line automation framework rather than a hosted service, so deployment targets a local Python environment and offline verification instead of a server or listening port. A repeatable checker will own setup and verification, isolate demonstration credentials from the normal account ledger, and prefer Google Chrome while allowing Playwright Chromium as a fallback; these choices avoid real third-party registrations and make a clean-machine result reproducible without making Chrome installation a hard requirement.
