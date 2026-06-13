#!/usr/bin/env python3
"""
AI Job Automation — daily entry point.

Run manually : python main.py
Schedule     : bash cron_setup.sh   (sets up daily 8 AM cron)
Docker       : docker compose up
"""

import logging
import sys

from config import load_config
from emailer import send_summary_email
from fetcher import fetch_jobs
from scorer import score_jobs
from sheets import read_candidate_profile, save_matched_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("job_automation.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def run():
    log.info("═══ AI Job Automation started ═══")

    cfg = load_config()

    # ── Step 1: Load candidate profile ──────────────────────────────────────
    log.info("Step 1/6 — Loading candidate profile from Google Sheets...")
    profile = read_candidate_profile(cfg)
    log.info(f"Profile: skills='{profile.get('skills','')[:60]}...'")

    # ── Step 2: Fetch job listings ──────────────────────────────────────────
    log.info("Step 2/6 — Fetching job listings via Decodo...")
    raw_jobs = fetch_jobs(cfg)
    log.info(f"Fetched {len(raw_jobs)} listings")

    if not raw_jobs:
        log.warning("No jobs returned from Decodo. Exiting early.")
        return

    # ── Step 3: Score with AI ───────────────────────────────────────────────
    batch = raw_jobs[: cfg.max_jobs_per_run]
    log.info(f"Step 3/6 — Scoring {len(batch)} jobs with {cfg.openai_model}...")
    scored_jobs = score_jobs(cfg, batch, profile)

    # ── Step 4: Filter by fit score ─────────────────────────────────────────
    matched = [j for j in scored_jobs if j["fit_score"] > cfg.fit_score_threshold]
    log.info(
        f"Step 4/6 — Filter: {len(matched)}/{len(scored_jobs)} jobs passed "
        f"fit_score > {cfg.fit_score_threshold}"
    )

    # ── Step 5: Save to Google Sheets ───────────────────────────────────────
    log.info("Step 5/6 — Saving matched jobs to Google Sheets...")
    saved = save_matched_jobs(cfg, matched) if matched else 0
    log.info(f"Saved {saved} new job(s)")

    # ── Step 6: Send daily email ─────────────────────────────────────────────
    log.info("Step 6/6 — Sending daily summary email...")
    send_summary_email(cfg, matched)

    log.info(f"═══ Done — {len(matched)} match(es) found, email sent ═══")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        log.exception(f"Fatal error: {exc}")
        sys.exit(1)
