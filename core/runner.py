"""
Standard Single-Thread Runner.
Manages browser lifecycle, logging, failure snapshot capture, and account ledger exports.
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Type, Optional
from playwright.sync_api import sync_playwright, Page

from core.adapter import BaseSiteAdapter
from core.stealth import apply_stealth_to_context, connect_fingerprint_browser


# ANSI Color formatting
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_CYAN = "\033[96m"
C_RESET = "\033[0m"


class StandardRunner:
    """Manages automation execution, failure snapshots, and ledger recording."""

    def __init__(self, config: Dict[str, Any], cdp_endpoint: Optional[str] = None):
        self.config = config
        self.headless = config.get("browser", {}).get("headless", False)
        self.enable_stealth = config.get("browser", {}).get("enable_stealth", True)
        self.use_chrome_channel = config.get("browser", {}).get("use_chrome_channel", True)
        self.proxy_server = config.get("browser", {}).get("proxy") or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        self.cdp_endpoint = cdp_endpoint or config.get("browser", {}).get("cdp_endpoint")
        self.output_dir = Path(config.get("output_dir", "./results"))
        self.snapshot_dir = self.output_dir / "snapshots"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.success_file = self.output_dir / "accounts.txt"
        self.failed_file = self.output_dir / "failed.txt"

    def log(self, level: str, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        lvl = level.lower()
        if lvl == "success":
            tag = f"{C_GREEN}[SUCCESS]{C_RESET}"
        elif lvl == "warn":
            tag = f"{C_YELLOW}[WARN]{C_RESET}"
        elif lvl == "error":
            tag = f"{C_RED}[ERROR]{C_RESET}"
        else:
            tag = f"{C_CYAN}[INFO]{C_RESET}"
        print(f"[{timestamp}] {tag} {msg}")

    def capture_snapshot(self, page: Page, name_prefix: str = "failure") -> Optional[Path]:
        """Capture high-resolution screenshot for blackbox post-mortem review."""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shot_path = self.snapshot_dir / f"{name_prefix}_{ts}.png"
            page.screenshot(path=str(shot_path), full_page=False)
            self.log("info", f"Visual snapshot preserved: {shot_path.resolve()}")
            return shot_path
        except Exception as e:
            self.log("warn", f"Could not capture snapshot: {e}")
            return None

    def save_success(self, account: Dict[str, Any]):
        line = f"{account.get('email', '')}----{account.get('password', '')}----{account.get('username', '')}\n"
        with open(self.success_file, "a", encoding="utf-8") as f:
            f.write(line)
        self.log("success", f"Credential saved to {self.success_file}")

    def save_failed(self, reason: str, account: Dict[str, Any], snapshot_path: Optional[Path] = None):
        snap_info = f" | Snapshot: {snapshot_path.name}" if snapshot_path else ""
        line = f"{datetime.now().isoformat()} | {reason} | {account}{snap_info}\n"
        with open(self.failed_file, "a", encoding="utf-8") as f:
            f.write(line)

    def _launch_browser(self, p):
        """Launch browser with robust maximization, stealth and genuine Chrome channel."""
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        
        launch_kwargs = {
            "headless": self.headless,
            "args": launch_args,
            "ignore_default_args": ["--enable-automation"]
        }

        if self.proxy_server:
            self.log("info", f"Using proxy server: {self.proxy_server}")
            launch_kwargs["proxy"] = {"server": self.proxy_server}

        # Try launching official Google Chrome first if available
        if self.use_chrome_channel:
            try:
                self.log("info", "Attempting to launch official Google Chrome (channel='chrome')...")
                return p.chromium.launch(channel="chrome", **launch_kwargs)
            except Exception as e:
                self.log("warn", f"Official Google Chrome not available ({e}), falling back to bundled Chromium.")

        return p.chromium.launch(**launch_kwargs)

    def execute_adapter(self, adapter_cls: Type[BaseSiteAdapter], count: int = 1) -> int:
        """Dispatch to the pure-HTTP protocol path or the classic browser path.

        Adapters declaring ``requires_browser = False`` (e.g. APIrf) run without
        Playwright ever being started; every other adapter keeps the original
        browser lifecycle untouched.
        """
        if getattr(adapter_cls, "requires_browser", True) is False:
            return self._execute_protocol_adapter(adapter_cls, count)
        return self._execute_browser_adapter(adapter_cls, count)

    # -- pure-HTTP protocol path (feature: apirf-http-registration) ---------

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Map a login to a filesystem-safe sidecar filename."""
        cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(name))
        return cleaned or "account"

    def _export_cookies(self, adapter) -> Path:
        """Write the standard cookie sidecar for a verified account.

        Format per cookie: name, value, domain, path, expires, httpOnly,
        secure, sameSite -- matching the playback contract in the ADR.
        """
        cookies = []
        session = getattr(adapter, "session", None)
        jar = getattr(session, "cookies", None)
        for c in list(jar or []):
            rest = getattr(c, "_rest", {}) or {}
            http_only = any(key.lower() == "httponly" for key in rest)
            same_site = next((v for key, v in rest.items() if key.lower() == "samesite"), None)
            cookies.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires,
                "httpOnly": http_only,
                "secure": bool(c.secure),
                "sameSite": same_site,
            })
        if not cookies:
            raise ValueError("Verified protocol account has no session cookies; refusing success ledger")
        username = self._safe_filename(adapter.account_data.get("username") or "account")
        cookie_dir = self.output_dir / "cookies"
        cookie_dir.mkdir(parents=True, exist_ok=True)
        path = cookie_dir / f"{username}.json"
        path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log("info", f"Cookie sidecar exported: {path}")
        return path

    def _save_pending_activation(self, adapter) -> Path:
        """Persist an incomplete activation for later resumption.

        Stored separately from accounts.txt / failed.txt under
        results/pending_activation/<login>.json with the failure stage,
        account credentials and mailbox recovery data.
        """
        pending = getattr(adapter, "pending_activation", None) or {
            "stage": "unknown",
            "account": dict(adapter.account_data),
            "mailbox": {},
        }
        record = dict(pending)
        record["recorded_at"] = datetime.now().isoformat()
        username = self._safe_filename(adapter.account_data.get("username") or "account")
        pending_dir = self.output_dir / "pending_activation"
        pending_dir.mkdir(parents=True, exist_ok=True)
        path = pending_dir / f"{username}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log("warn", f"Pending activation recorded: {path} (stage={record.get('stage')})")
        return path

    def _execute_protocol_adapter(self, adapter_cls, count: int) -> int:
        success_count = 0
        self.log("info", f"Starting protocol session (target count: {count}, no browser)...")

        for idx in range(1, count + 1):
            self.log("info", f"=== Processing protocol task [{idx}/{count}] ===")
            adapter = adapter_cls(None, None, self.config)
            task_start = time.time()
            try:
                ok = adapter.run()
                elapsed = round(time.time() - task_start, 2)
                if ok:
                    # Cookie sidecar first: a ledger line is only written once
                    # activation is verified AND its playback cookies exist.
                    self._export_cookies(adapter)
                    self.save_success(adapter.account_data)
                    success_count += 1
                    self.log("success", f"Protocol task [{idx}/{count}] succeeded in {elapsed}s.")
                else:
                    self._save_pending_activation(adapter)
                    self.log("warn", f"Protocol task [{idx}/{count}] incomplete after {elapsed}s.")
            except Exception as e:
                elapsed = round(time.time() - task_start, 2)
                self.log("error", f"Protocol task [{idx}/{count}] failed after {elapsed}s: {e}")
                self.save_failed(str(e), adapter.account_data)
                if getattr(e, "stop_run", False):
                    self.log("warn", "Blocking response detected; stopping the batch immediately (no retries).")
                    break

        self.log("info", f"Protocol session completed. Success: {success_count}/{count}")
        return success_count

    def _execute_browser_adapter(self, adapter_cls: Type[BaseSiteAdapter], count: int = 1) -> int:
        success_count = 0
        mode_desc = f"external CDP ({self.cdp_endpoint})" if self.cdp_endpoint else f"desktop browser (headless={self.headless})"
        self.log("info", f"Starting automation session (target count: {count}, mode: {mode_desc}, stealth: {self.enable_stealth})...")

        with sync_playwright() as p:
            if self.cdp_endpoint:
                self.log("info", f"Connecting to external fingerprint browser at {self.cdp_endpoint}...")
                browser = connect_fingerprint_browser(p, self.cdp_endpoint)
                context = browser.contexts[0] if browser.contexts else browser.new_context(viewport={"width": 1280, "height": 800})
            else:
                browser = self._launch_browser(p)
                context = browser.new_context(
                    no_viewport=True
                )

            if self.enable_stealth:
                apply_stealth_to_context(context)
                self.log("info", "Anti-fingerprint masking scripts injected into context.")
            
            for idx in range(1, count + 1):
                self.log("info", f"=== Processing task [{idx}/{count}] ===")
                page = context.new_page()
                adapter = adapter_cls(page, context, self.config)
                task_start = time.time()
                
                try:
                    ok = adapter.run()
                    elapsed = round(time.time() - task_start, 2)
                    if ok:
                        self.log("success", f"Task [{idx}/{count}] finished successfully in {elapsed}s!")
                        self.save_success(adapter.account_data)
                        success_count += 1
                        if not self.headless:
                            time.sleep(2)
                    else:
                        snap = self.capture_snapshot(page, f"task_{idx}_failed")
                        self.log("warn", f"Task [{idx}/{count}] failed after {elapsed}s.")
                        self.save_failed("Form submission returned False", adapter.account_data, snap)
                        if not self.headless:
                            self.log("info", "Keeping window visible for 5 seconds for review...")
                            time.sleep(5)
                except Exception as e:
                    elapsed = round(time.time() - task_start, 2)
                    snap = self.capture_snapshot(page, f"task_{idx}_exception")
                    self.log("error", f"Task [{idx}/{count}] encountered exception after {elapsed}s: {e}")
                    self.save_failed(str(e), adapter.account_data, snap)
                    if not self.headless:
                        self.log("info", "Keeping window visible for 6 seconds before closing...")
                        time.sleep(6)
                finally:
                    page.close()

            context.close()
            browser.close()

        self.log("info", f"Session completed. Success: {success_count}/{count}")
        return success_count
