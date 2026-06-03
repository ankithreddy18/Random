import json
import logging
from datetime import datetime, timezone
from typing import Dict, List

import requests

log = logging.getLogger(__name__)


def fetch_jobs(cfg) -> List[Dict]:
    """Fetch remote job listings via the Decodo Scraper API."""
    log.info(f"Requesting jobs from Decodo (target: {cfg.job_source_url})")

    resp = requests.post(
        "https://scraper-api.decodo.com/v2/scrape",
        headers={
            "Authorization": f"Basic {cfg.decodo_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "url": cfg.job_source_url,
            "httpResponseBody": True,
            "headless": False,
        },
        timeout=45,
    )
    resp.raise_for_status()

    data = resp.json()
    body = data.get("body", data)
    if isinstance(body, str):
        body = json.loads(body)

    jobs = body if isinstance(body, list) else [body]

    # RemoteOK: index 0 is a legal-notice object, not a job — skip it
    if jobs and not jobs[0].get("id"):
        jobs = jobs[1:]

    normalized = [
        _normalize(j, i)
        for i, j in enumerate(jobs)
        if j.get("id") or j.get("title") or j.get("position")
    ]
    log.info(f"Parsed {len(normalized)} job listings")
    return normalized


def _normalize(job: Dict, index: int) -> Dict:
    salary = ""
    if job.get("salary"):
        salary = str(job["salary"])
    elif job.get("salary_min"):
        lo = f"${int(job['salary_min']):,}"
        hi = f"${int(job.get('salary_max', job['salary_min'])):,}"
        salary = f"{lo} – {hi}"

    tags = job.get("tags", [])
    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags or "")

    epoch = job.get("epoch")
    date_posted = (
        datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
        if epoch
        else str(job.get("date") or datetime.now(tz=timezone.utc).date())
    )

    description = str(
        job.get("description") or tags_str or ""
    )[:800]

    return {
        "job_id": str(job.get("id") or job.get("slug") or f"job-{index}"),
        "title": str(job.get("position") or job.get("title") or "Unknown Position"),
        "company": str(job.get("company") or job.get("company_name") or "Unknown Company"),
        "description": description,
        "url": str(job.get("url") or job.get("apply_url") or ""),
        "location": str(job.get("location") or "Remote"),
        "salary": salary,
        "tags": tags_str,
        "date_posted": date_posted,
    }
