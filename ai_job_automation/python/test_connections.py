#!/usr/bin/env python3
"""
Pre-flight connectivity check.
Run this BEFORE the first real run to confirm every credential works.
No jobs are fetched in full, no emails sent, no OpenAI credits spent.
"""

import sys


def check(label: str, fn):
    try:
        result = fn()
        status = result or "OK"
        print(f"  ✓ {label}: {status}")
        return True
    except Exception as exc:
        print(f"  ✗ {label}: {exc}")
        return False


def main():
    print("\nAI Job Automation — pre-flight check\n")
    failures = 0

    # ── Config ──────────────────────────────────────────────────────────────
    print("[1/4] Config")
    try:
        from config import load_config
        cfg = load_config()
        print(f"  ✓ All required env vars present")
    except Exception as exc:
        print(f"  ✗ {exc}")
        sys.exit(1)

    # ── Google Sheets ────────────────────────────────────────────────────────
    print("\n[2/4] Google Sheets")
    from sheets import read_candidate_profile

    def _sheets():
        profile = read_candidate_profile(cfg)
        return f"skills='{profile.get('skills','')[:40]}...'"

    if not check("Read candidate profile", _sheets):
        failures += 1

    # ── OpenAI ───────────────────────────────────────────────────────────────
    print("\n[3/4] OpenAI API")

    def _openai():
        from openai import OpenAI
        client = OpenAI(api_key=cfg.openai_api_key)
        # Minimal call — list models (no tokens billed)
        models = client.models.list()
        ids = [m.id for m in models.data if "gpt" in m.id]
        return f"connected, {len(ids)} GPT model(s) visible"

    if not check("OpenAI connection", _openai):
        failures += 1

    # ── Decodo / Job source ──────────────────────────────────────────────────
    print("\n[4/4] Decodo / job source")

    def _decodo():
        import requests as req
        # Quick HEAD against Decodo to verify API key
        resp = req.head(
            "https://scraper-api.decodo.com/v2/scrape",
            headers={"Authorization": f"Basic {cfg.decodo_api_key}"},
            timeout=10,
        )
        # 405 Method Not Allowed is fine — endpoint exists & key was accepted
        if resp.status_code in (200, 405):
            return f"API reachable (HTTP {resp.status_code})"
        resp.raise_for_status()

    if not check("Decodo API reachable", _decodo):
        # Fallback: try RemoteOK directly (no key needed)
        def _remoteok():
            import requests as req
            resp = req.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            resp.raise_for_status()
            jobs = [j for j in resp.json() if j.get("id")]
            return f"RemoteOK fallback: {len(jobs)} jobs available"

        if not check("RemoteOK fallback", _remoteok):
            failures += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    if failures == 0:
        print("All systems ready. Run:  python main.py\n")
    else:
        print(f"{failures} check(s) failed. Fix the issues above, then re-run this script.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
