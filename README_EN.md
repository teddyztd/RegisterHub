<h1 align="center">RegisterHub</h1>

<p align="center">
  <b>Industrial-Grade Universal Account Registration & Lifecycle Testing Engine</b><br>
  <i>A deterministic, stealth automation framework for universal account registration and agentic workflows.</i>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-22272e.svg?style=flat-square" alt="License"></a>
  <a href="DISCLAIMER.md"><img src="https://img.shields.io/badge/Disclaimer-Legal%20Terms-red.svg?style=flat-square" alt="Disclaimer"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776ab.svg?style=flat-square&logo=python&logoColor=white" alt="Python Version"></a>
  <a href="https://playwright.dev/"><img src="https://img.shields.io/badge/Playwright-Engine-2EAD33.svg?style=flat-square&logo=playwright&logoColor=white" alt="Playwright"></a>
  <a href="https://opencv.org/"><img src="https://img.shields.io/badge/OpenCV-CV%20Engine-5C3EE8.svg?style=flat-square&logo=opencv&logoColor=white" alt="OpenCV"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/Tests-Passing-brightgreen.svg?style=flat-square" alt="Tests"></a>
  <a href="https://bitwarden.com/"><img src="https://img.shields.io/badge/Export-Bitwarden%2FCSV-175DDC.svg?style=flat-square&logo=bitwarden&logoColor=white" alt="Bitwarden Export"></a>
</p>

<p align="center">
  <a href="./README.md">简体中文</a> | <a href="./README_EN.md">English</a>
</p>

---

## Overview

RegisterHub is an engineering-first automation framework designed to eliminate the fragility of traditional browser automation. Built on top of Playwright, OpenCV-based computer vision solvers, and Chrome DevTools Protocol (CDP), RegisterHub provides deterministic execution across modern single-page applications (SPAs), reactive state managers, and controlled DOM interfaces.

### Engineering Core Pillars

- **Runtime Environment Parity**: Eliminates synthetic automation signatures via native Chrome runtime integration, strict prototype preservation (`[native code]`), and clean JavaScript execution context.
- **Algorithmic Vision Solver**: Built-in computer vision pipeline featuring dual-pass Canny edge detection and human-kinetic Bezier curve trajectory generation, executing offline with zero cloud API dependencies.
- **CDP Bridge Architecture**: Native integration with enterprise fingerprint browsers (AdsPower, BitBrowser) and local Chrome instances, allowing seamless reuse of clean residential IPs and persistent user sessions.
- **Agentic Automation Protocol**: Natively integrated with `AGENTS.md`, enabling autonomous AI agents (Cursor, Claude Code, Windsurf, Gemini CLI) to probe DOM targets, generate adapters, and execute end-to-end verification.

---

## Architecture

```text
RegisterHub/
├── core/
│   ├── adapter.py         # Abstract base adapter (BaseSiteAdapter) & lifecycle hooks
│   ├── pilot.py           # Human-like keystroke dynamics & resilient interaction helpers
│   ├── stealth.py         # Native Chrome consistency & CDP bridge engine
│   ├── inspector.py       # Heuristic DOM form inspector (FormInspector)
│   ├── solver.py          # OpenCV puzzle gap detector & Bezier trajectory planner
│   ├── identity.py        # High-entropy synthetic persona & credential generator
│   ├── mail_client.py     # Adaptive polling mailbox synchronization client
│   ├── runner.py          # Deterministic task execution, snapshot logger & ledger writer
│   ├── scaffold.py        # Automated adapter scaffolding & code generation engine
│   └── exporter.py        # Bitwarden, 1Password, CSV & JSON credential exporter
├── sites/                 # Production & reference adapters
│   ├── _template.py       # Standard adapter implementation template
│   ├── demo_site.py       # Self-contained offline Base64 reference target
│   ├── quanticdata.py     # Slider puzzle & Bezier drag verification adapter
│   ├── deepgram.py        # Deepgram $200 USD allowance & key harvesting adapter
│   ├── amd.py             # AMD AI Developer Program onboarding adapter
│   ├── coarena.py         # Post-Google OAuth pure protocol registration & API key minting
│   ├── milionseek.py      # 100milionseek 100M tokens/day key harvester & Turnstile solver
│   └── automation_exercise.py # Multi-step wizard workflow adapter
├── tests/                 # Unit & regression test suite
├── config.json            # Global runtime configuration
├── pytest.ini             # Test runner isolation rules
├── main.py                # Unified CLI entry point
├── run.bat                # Windows interactive execution bootstrap (CRLF)
└── requirements.txt       # Core dependency manifest
```

---

## Showcase Adapters

RegisterHub includes reference implementations covering diverse architectural paradigms:

| Adapter Key | Target Environment | Technical Characteristics | Primary Evaluation Target |
| :--- | :--- | :--- | :--- |
| `demo` | Embedded Base64 Target | Zero-configuration offline pipeline | Rapid 3s runtime environment verification |
| `quanticdata` | Quantic Data Service | OpenCV edge detection + Bezier kinematics | Local slider puzzle resolution & reactive inputs |
| `deepgram` | Deepgram Voice AI | Google reCAPTCHA v2 active penetration | $200 USD free credit allowance & API key extraction |
| `amd` | AMD AI Developer Program | Akamai telemetry parity + OneTrust clearance | Big Tech AI developer registration & token acquisition |
| `coarena` | Coarena AI Platform | **Post-Google OAuth Protocol Registration & Key Minting** | Demonstrates OAuth session capture, pure REST terms acceptance & instant API key minting |
| `milionseek` | 100milionseek Platform | **100M Tokens/day Free Compute** + Turnstile Clearance | Instant on-page key generation (no mail verification needed) + referral cascade pool |
| `automation_exercise` | Standard Benchmark Portal | Multi-stage registration wizard | Complex dropdown cascading & checkbox grids |
| `apirf` | [APIrf](https://apirf.ru) | Pure-HTTP session + strict activation-link extraction | Single-account registration, email activation, and identity verification |

---

## Standalone Showcase Ecosystem

> **Standalone Decoupling & Reciprocal Funnel Notice**:  
> For developers interested in automating a **single specific service**, we have decoupled our primary production workflows into **100% self-contained standalone GitHub repositories**.  
> Each independent repository includes its own Windows `run.bat` launcher, dedicated `main.py` entry point, and embedded runtime engine without requiring the full framework. You can also run them within this unified engine via `python main.py --run <site>`:

| Standalone Project | Key Features & Free Benefits | Repository Direct Link |
| :--- | :--- | :--- |
| **[Deepgram Register](https://github.com/waw666waw666/deepgram-register)** | Official **$200 USD Free Credit Allowance** + reCAPTCHA v2 Penetration + Pure REST Protocol Key Extraction | [GitHub Repo](https://github.com/waw666waw666/deepgram-register) |
| **[100MilionSeek Register](https://github.com/waw666waw666/100milionseek-register)** | **100M Tokens/day Free Allowance** + Turnstile Clearance + Instant Card Key Harvester + Referral Pool | [GitHub Repo](https://github.com/waw666waw666/100milionseek-register) |
| **[AMD AI Dev Register](https://github.com/waw666waw666/amd-register)** | Official AMD AI Developer Program + Akamai Telemetry Parity + OneTrust Modal Penetration | [GitHub Repo](https://github.com/waw666waw666/amd-register) |
| **[Coarena Register](https://github.com/waw666waw666/coarena-register)** | **Post-OAuth Pure REST Protocol Key Minting** + Session Capture + Terms Acceptance & Quota Validation | [GitHub Repo](https://github.com/waw666waw666/coarena-register) |

---

## Quickstart

### 1. One-Command Deployment and Verification (Recommended)

Local deployment prepares a Python environment for the RegisterHub CLI; it does not publish a server or open a listening port. With Python 3.10+ installed, run one command from a clean checkout:

```bash
git clone https://github.com/waw666waw666/RegisterHub.git
cd RegisterHub
python scripts/deploy_check.py
```

The checker creates or reuses the project `.venv`, re-executes with that interpreter, and runs these gates in order:

| Stage | Behavior |
| :--- | :--- |
| `install` | Installs `requirements.txt` dependencies and the Playwright Chromium fallback browser |
| `config` | Preserves an existing `config.json`; only when it is missing, derives one from `config.example.json` with `browser.headless=true` |
| `doctor` | Runs `main.py doctor` to check dependencies, configuration, and browser health |
| `pytest` | Runs the complete `pytest tests/` suite |
| `demo` | Runs `main.py --run demo` in an isolated temporary working directory and requires non-empty credential data in its temporary `results/accounts.txt` |

- **Browser preference**: The runner uses installed Google Chrome first and falls back to Playwright Chromium when Chrome is unavailable, so Chrome is not a hard requirement.
- **Failure behavior**: The checker stops at the first failed blocking stage, prints its name, and exits non-zero. A zero demo subprocess exit code is insufficient; an empty isolated ledger also fails verification.
- **Data isolation**: The demo forces headless mode and a temporary `output_dir`. Its directory and credentials are removed after verification. The normal `results/accounts.txt` and existing proxy, mailbox, and browser preferences are not modified.

### 2. Prepared Machines: Skip Installation

Avoid reinstalling dependencies and browser binaries on a prepared machine:

```bash
python scripts/deploy_check.py --skip-install
```

`--skip-install` skips **only** dependency and Playwright Chromium installation. Configuration preservation or derivation, `doctor`, the full test suite, the isolated demo, and the non-empty ledger gate still run. An unprepared environment fails at the corresponding later stage rather than reporting false success.

### 3. Manual Steps (Optional)

To run diagnostics, tests, or the offline demo separately, use the prepared project virtual environment:

```bash
python main.py doctor
python -m pytest tests/
python main.py --run demo
```

A manual demo writes credentials atomically to the normal `results/accounts.txt`. It exercises only the offline adapter flow and **is not a complete deployment verification**; the one-command checker also gates diagnostics, tests, and a non-empty isolated ledger.

### 4. AI Agent Collaborative Development (Cursor / Claude Code / Windsurf / Gemini)

RegisterHub is engineered from the ground up for seamless co-development with autonomous AI programming agents. The workspace root includes strictly audited [AGENTS.md](AGENTS.md) and [SETUP_FOR_AI.md](SETUP_FOR_AI.md) agent contracts.

**Prerequisite**: Open the **`RegisterHub`** project folder as the root active workspace in your AI IDE (Cursor, Windsurf, VS Code with Claude Code, or Gemini CLI).

Once loaded into the workspace, you can instruct your AI using either of the two approaches:

#### Method 1: Direct Prompting (Fast & Lightweight)
Drop the target URL directly into your AI chat:
```text
Follow the workspace conventions and AGENTS.md to generate an automated registration adapter for: https://example.com/signup
```
The AI reads the root rules, probes DOM elements, scaffolds the adapter, and runs baseline tests automatically.

#### Method 2: Provide Human-Walkthrough Steps (Strongly Recommended & Highest Success Rate)
For modern multi-step SPAs, onboarding wizards, or sites with interactive challenges, **the most reliable approach is to manually register one account yourself first in your regular browser**.  
Provide your recorded walkthrough—including URLs, clicked buttons, form inputs, OTP steps, and UI screenshots—directly to the AI:
```text
Please follow RegisterHub standards and AGENTS.md to build an automated adapter matching my verified manual workflow:
Target URL: https://example.com/signup

My manual walkthrough (screenshots attached):
1. Navigate to signup page, fill in email and password, and click "Create Account";
2. A Cloudflare Turnstile box appears; click the checkbox to clear;
3. Check inbox for the 6-digit OTP code and input it into the verification field;
4. Lands on the dashboard, navigate to "API Keys" in the top-right menu, and click "Create New Key";
5. Copy the displayed sk-xxxx key.

Please assemble sites/example_site.py according to this exact walkthrough and run a local verification test!
```
The AI will precisely map and automate your verified human interaction chain, eliminating guesswork and ensuring production-grade reliability on the first attempt!

### 5. APIrf Pure-HTTP Single-Account Registration

The `apirf` adapter targets only **https://apirf.ru**. One HTTP session handles guest creation, account binding, email confirmation, login, and identity verification without launching a browser.

Set `apirf.mail.im215_api_key` in the local `config.json`, or use the `APIRF_215_API_KEY` environment variable instead. Never commit a real key. PowerShell example:

```powershell
$env:APIRF_215_API_KEY = "<your-215.im-api-key>"
python main.py --run apirf --count 1
```

`config.example.json` contains an empty key and these defaults:

| Setting | Default | Purpose |
| :--- | :--- | :--- |
| `apirf.mail.im215_api_key` | Empty string | 215.im key; `APIRF_215_API_KEY` is the environment alternative |
| `apirf.mail.http_timeout_secs` | `20` | Timeout in seconds for each APIrf or mailbox HTTP request |
| `apirf.mail.confirmation_timeout_secs` | `300` | Overall timeout in seconds while waiting for the confirmation email |

The target origin is fixed at `https://apirf.ru`; the APIrf mailbox route is fixed at `215.im` only. Neither can be replaced by configuration.

APIrf never delivers confirmation mail to public disposable domains such as `mail.tm`, `tempmail.io`, or `guerrillamail`, so those providers are not usable fallbacks for this site. Without a 215.im key the adapter fails at construction time -- before any APIrf HTTP request -- and records a clear reason in `failed.txt` instead of creating a mailbox and waiting out the confirmation timeout. After an address is submitted to APIrf, the same mailbox remains pinned for polling; the run does not switch addresses and retry.

Artifacts are written under `output_dir` (default `./results`):

| Artifact | When and what is written |
| :--- | :--- |
| `results/accounts.txt` | Appends `email----password----login` only after strict verification |
| `results/cookies/<login>.json` | Exports the non-empty session cookies before the success ledger, with `name`, `value`, `domain`, `path`, `expires`, `httpOnly`, `secure`, and `sameSite` |
| `results/pending_activation/<login>.json` | Stores recovery data with stage `confirmation` or `identity` when activation is incomplete; no success ledger or cookie artifact is written |

**Strict success gate:** the confirmation link must use the official confirmation path on `https://apirf.ru`; the session then logs in on the same HTTP session, and the `user` object from `GET /api/auth/me` must contain the literal values `email_verified: true` and `is_guest: false`, with a non-empty session cookie jar. The login response itself is not used as proof of success. A captcha, access-denied response, HTTP 403/429, or rate-limit signal stops the run immediately without a retry storm.

**Only the single-account acceptance run above is authorized by default. Bulk account-lifecycle testing and pressure testing are not authorized by default and require separate explicit approval.** Accounts, cookies, and pending-activation records under `results/` are sensitive local artifacts and must not be committed.

---

## Email Verification & Mailbox Strategies

Target platforms maintain diverse risk-control rules for signup mailboxes. RegisterHub provides three flexible tiers:

1. **Zero-Email-Verification Targets (Instant Minting)**:
   - Showcase Target: `100milionseek`
   - Requires **no verification emails or confirmation links whatsoever**. Enter any standard email format, resolve Turnstile, and the API key is minted directly on the page within 10 seconds.

2. **Session Capture Targets (OAuth Handoff)**:
   - Showcase Target: `coarena`
   - Leverages genuine Chrome solely for Google OAuth token acquisition; subsequent terms consent, key minting, and quota validation are executed 100% via background REST protocol.

3. **High-Value / Strict Risk Targets (e.g. Deepgram $200 USD Allowance, AMD)**:
   - **Default Mode (Public Disposable Email, Automated)**:
     With `use_disposable_mail: true`, the engine automatically polls tri-channel public APIs (mail.tm, etc.) for 6-digit codes.
   - **Custom Mailbox Mode (Recommended, 100% Success Guarantee)**:
     Platforms like Deepgram and AMD dynamically blacklist public temporary email domains. **We strongly recommend supplying your own Outlook, Hotmail, Gmail, or custom domain address** in `config.json` (`"email": "your_email@outlook.com"`). The script automatically completes form submission and reCAPTCHA penetration, prompts for the 6-digit code in the terminal, and guarantees minting of your **$200 USD API key**!
   - **Enterprise MailHub Hub (Advanced)**:
     Easily integrates with self-hosted MailHub Docker containers, Cloudflare Catch-all Email Routing, or IMAP protocols for multi-worker headless automation.

---

## Command Line Interface (CLI)

### Adapter Discovery
List all registered site adapters and their technical descriptors:
```bash
python main.py --list
```

### Automated Adapter Scaffolding
Inspect a target registration page and generate a typed adapter skeleton pre-populated with discovered input selectors:
```bash
# Analyze target DOM and scaffold adapter skeleton
python main.py --scaffold target_service --url https://target-service.com/signup

# Execute scaffolded adapter
python main.py --run target_service
```

### External CDP Session Attach
Attach to an already running external browser instance (AdsPower, BitBrowser, or Chrome with `--remote-debugging-port`):
```bash
python main.py --run demo --cdp http://127.0.0.1:9222
```

### Credential Vault Export
Export verified account records into standardized credential management formats:
```bash
# Bitwarden / 1Password compatible JSON
python main.py export --export bitwarden

# Standard CSV format
python main.py export --export csv

# Raw JSON format
python main.py export --export json
```

---

## AI Agent Integration (`AGENTS.md`)

RegisterHub is architected for seamless collaboration with autonomous programming agents. The root `AGENTS.md` enforces strict engineering disciplines:

- **Single Concurrency Default**: Enforces deterministic single-threaded execution by default to prevent desktop disruption and IP exhaustion; prompts for concurrency scaling only after sustained success.
- **Stage-Gate Assertions**: Prohibits arbitrary timeout delays; mandates strict validation of URL mutations, DOM response states, and token persistence.
- **Zero-Interference Process Lifecycle**: Manages child process trees explicitly via POSIX/Windows hooks, ensuring external user processes and personal browser sessions remain completely untouched.

---

## Verification & Testing

Execute the test suite to validate core heuristics, OpenCV solvers, and code scaffolding:

```bash
pytest tests/
```

---

## Disclaimer & Legal Notice

1. **License**: This project is licensed under the [Apache License 2.0](LICENSE).
2. **Legal Disclaimer**: RegisterHub is strictly intended for **authorized security audits, regression test automation, and web standards research**.
   - **Accessing, downloading, or running this code constitutes unconditional agreement to be bound by the full Legal Disclaimer**;
   - Mass registration abuse, credential stuffing, scraping protected assets, or circumventing commercial defenses is strictly prohibited;
   - Users assume all legal risks and responsibilities. The authors accept zero liability for any damages or violations arising from misuse.

> **Full Legal Disclaimer**: [DISCLAIMER.md](DISCLAIMER.md) · [简体中文免责声明](DISCLAIMER.zh.md)

---

## Community & Support

Join our developer community for technical discussions, custom adapter requests, and browser automation best practices:

- **Discord Community**: [Join Discord](https://discord.gg/USnVJ9YQX)
- **QQ Group**: 1130324020
