"""
RegisterHub CLI Main Entrypoint.
The Modern Headless Account & Form Automation Framework.

Import policy: heavyweight modules that pull in Playwright are imported lazily,
inside the functions that actually need a browser. This keeps dependency-free
commands -- most importantly `doctor` -- runnable on a machine where Playwright
has not been installed yet. A diagnostic tool that crashes before it can report
what is missing is useless.
"""
import sys
import json
import argparse
from pathlib import Path


def load_config() -> dict:
    cfg_path = Path("config.json")
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"browser": {"headless": False}, "output_dir": "./results"}


def run_doctor():
    """Run the environment diagnostic suite.

    Delegates to core.doctor, which performs real executable verification
    (browser launch, OpenCV native call, filesystem write, network probe)
    rather than merely confirming that modules import.
    """
    from core.doctor import run_doctor as _doctor
    cfg = load_config()
    output_dir = cfg.get("output_dir", "./results")
    return _doctor(output_dir=output_dir)


def run_preflight():
    """Run the read-only APIrf live-run preflight.

    Delegates to core.preflight, which issues only GET requests. Nothing here
    may create, upgrade or register an account.
    """
    from core.preflight import run_preflight as _preflight
    return _preflight(load_config())


def inspect_url(target_url: str, cdp_endpoint: str = None):
    from playwright.sync_api import sync_playwright
    from core.stealth import apply_stealth_to_context, connect_fingerprint_browser
    from core.inspector import FormInspector
    from core.identity import generate_identity
    from core.pilot import human_type, smart_agree_tos
    import os
    print(f"[*] Navigating to {target_url} for heuristic form inspection...")
    
    cfg = load_config()
    proxy_server = cfg.get("browser", {}).get("proxy") or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    
    with sync_playwright() as p:
        if cdp_endpoint:
            print(f"[*] Connecting to fingerprint browser at {cdp_endpoint}...")
            browser = connect_fingerprint_browser(p, cdp_endpoint)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
        else:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            launch_kwargs = {
                "headless": False,
                "args": launch_args,
                "ignore_default_args": ["--enable-automation"]
            }
            if proxy_server:
                launch_kwargs["proxy"] = {"server": proxy_server}
                
            try:
                browser = p.chromium.launch(channel="chrome", **launch_kwargs)
            except Exception:
                browser = p.chromium.launch(**launch_kwargs)

            # Let official Google Chrome use its native User-Agent and Client Hints to guarantee tri-consistency
            context = browser.new_context(
                no_viewport=True
            )

        apply_stealth_to_context(context)
        page = context.new_page()
        try:
            page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            inspector = FormInspector(page)
            fields = inspector.detect_inputs()
            
            print("\n[+] Heuristic Detection Results:")
            for k, v in fields.items():
                status = v if v else "Not found / Not visible"
                print(f"    - {k:18s}: {status}")

            if any(fields.values()):
                print("\n[*] Generating synthetic multi-field identity and testing autofill...")
                ident = generate_identity()
                if fields["email"]:
                    print(f"    -> Typing Email: {ident['email']}")
                    human_type(page, fields["email"], ident["email"])
                if fields["password"]:
                    print(f"    -> Typing Password: {ident['password']}")
                    human_type(page, fields["password"], ident["password"])
                if fields["confirm_password"]:
                    print(f"    -> Typing Confirm Password: {ident['password']}")
                    human_type(page, fields["confirm_password"], ident["password"])
                if fields["username"]:
                    print(f"    -> Typing Username: {ident['username']}")
                    human_type(page, fields["username"], ident["username"])
                if fields["fullname"]:
                    print(f"    -> Typing Fullname: {ident['full_name']}")
                    human_type(page, fields["fullname"], ident["full_name"])

                # Auto agree terms if checkbox found
                smart_agree_tos(page)
                
                print("\n[+] Form autofill finished with humanized typing rhythms.")
                print("[*] Browser will remain open for 10 seconds for visual inspection.")
                page.wait_for_timeout(10000)
            else:
                print("[-] Could not detect standard input selectors heuristically.")
        except Exception as e:
            print(f"[-] Inspection error: {e}")
        finally:
            browser.close()


def run_scaffold(site_name: str, target_url: str = None):
    from core.scaffold import scaffold_site
    print(f"[*] Scaffolding new adapter for '{site_name}'...")
    detected = {}
    if target_url:
        print(f"[*] Pre-inspecting '{target_url}' to extract input selectors...")
        try:
            from playwright.sync_api import sync_playwright
            from core.stealth import apply_stealth_to_context
            from core.inspector import FormInspector
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": True,
                    "args": ["--disable-blink-features=AutomationControlled", "--no-first-run"],
                    "ignore_default_args": ["--enable-automation"]
                }
                try:
                    browser = p.chromium.launch(channel="chrome", **launch_kwargs)
                except Exception:
                    browser = p.chromium.launch(**launch_kwargs)
                context = browser.new_context()
                apply_stealth_to_context(context)
                page = context.new_page()
                page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
                inspector = FormInspector(page)
                detected = inspector.detect_inputs()
                context.close()
                browser.close()
            print("[+] Form fields successfully detected and pre-assembled into scaffold!")
        except Exception as e:
            print(f"[!] Warning: Pre-inspection timed out or failed ({e}), generating standard template instead.")

    out_path = scaffold_site(site_name, target_url, detected)
    print(f"\n[+] Production scaffold successfully created at: {out_path.resolve()}")
    print(f"[*] You can now test and run it immediately:")
    print(f"    python main.py --run {site_name.lower()}\n")


def main():
    parser = argparse.ArgumentParser(description="RegisterHub Automation Engine")
    parser.add_argument("--run", type=str, default=None, help="Target site adapter name (e.g. demo, quanticdata, deepgram)")
    parser.add_argument("--list", action="store_true", help="List all available site adapters")
    parser.add_argument("--scaffold", type=str, default=None, help="Scaffold a new site adapter template (e.g. twitter, github)")
    parser.add_argument("--count", type=int, default=1, help="Number of accounts to generate")
    parser.add_argument("--url", type=str, default=None, help="Inspect URL or target URL for scaffolding")
    parser.add_argument("--cdp", type=str, default=None, help="Connect to an external Fingerprint/Anti-Detect browser CDP (e.g. http://127.0.0.1:9222)")
    parser.add_argument("--export", type=str, default=None, choices=["csv", "json", "bitwarden"], help="Export accounts to csv, json or bitwarden format")
    parser.add_argument("command", nargs="?", default=None, help="Subcommand like 'doctor' or 'export'")

    args = parser.parse_args()

    if args.command == "doctor":
        # Exit non-zero when blocking issues are found, so CI and wrapper
        # scripts can gate on the real environment state.
        ok = run_doctor()
        if not ok:
            sys.exit(1)
        return

    if args.command == "preflight":
        # Read-only readiness report. Exit non-zero on blocking failures so a
        # wrapper script can refuse to start a live run, and so an unknown
        # subcommand typo cannot silently fall through to the demo adapter.
        if not run_preflight():
            sys.exit(1)
        return

    if args.command == "list" or args.list:
        from sites import discover_adapters
        adapters = discover_adapters()
        print("=" * 65)
        print("  RegisterHub - Discovered Site Adapters")
        print("=" * 65)
        for name, cls in sorted(adapters.items()):
            try:
                url_attr = getattr(cls, "target_url", None)
                if callable(url_attr):
                    url = url_attr(None)
                elif isinstance(url_attr, property):
                    url = url_attr.fget(None)
                else:
                    url = str(url_attr) if url_attr else "N/A"
            except Exception:
                url = "N/A"
            display_url = url if len(url) <= 60 else (url[:45] + "... [embedded html]")
            print(f"  * {name:<22} -> {display_url}")
        print("=" * 65)
        print(f"  Total: {len(adapters)} adapters ready to run with 'python main.py --run <name>'")
        print("=" * 65)
        return

    if args.command == "export" or args.export:
        from core.exporter import run_export
        fmt = args.export or "csv"
        try:
            exported_path = run_export(fmt=fmt)
            print(f"[+] Accounts successfully exported to [{fmt.upper()}]: {exported_path.resolve()}")
        except Exception as e:
            print(f"[-] Export error: {e}")
        return

    if args.scaffold:
        run_scaffold(args.scaffold, target_url=args.url)
        return

    if args.url and not args.run:
        inspect_url(args.url, cdp_endpoint=args.cdp)
        return

    cfg = load_config()
    from core.runner import StandardRunner
    runner = StandardRunner(cfg, cdp_endpoint=args.cdp)

    from sites import discover_adapters
    adapters = discover_adapters()
    target_name = args.run or (args.command if args.command and args.command.lower() in adapters else None) or "demo"
    adapter_name = target_name.lower()
    
    if adapter_name in adapters:
        runner.execute_adapter(adapters[adapter_name], count=args.count)
    else:
        available = ", ".join(sorted(adapters.keys()))
        print(f"[-] Unknown adapter '{adapter_name}'. Available discovered adapters: {available}")


if __name__ == "__main__":
    main()
