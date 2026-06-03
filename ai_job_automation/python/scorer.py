import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List

from openai import OpenAI

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert job matching assistant. Analyze how well a job listing matches "
    "a candidate profile.\n"
    "Return ONLY a valid JSON object with exactly these three fields:\n"
    "- fit_score: integer 0-100 (0 = no match, 100 = perfect match)\n"
    "- reasoning: string, 1-2 sentence explanation (max 200 characters)\n"
    "- match_highlights: array of exactly 3 strings, each one key matching "
    "or mismatching point"
)


def score_jobs(cfg, jobs: List[Dict], profile: Dict) -> List[Dict]:
    client = OpenAI(api_key=cfg.openai_api_key)
    results = []

    for i, job in enumerate(jobs, 1):
        log.info(f"  [{i}/{len(jobs)}] Scoring: {job['title']} @ {job['company']}")
        try:
            scored = _score_one(client, cfg.openai_model, job, profile)
            results.append({**job, **scored, "scored_at": _now_iso()})
        except Exception as exc:
            log.warning(f"  Scoring failed for {job['job_id']}: {exc}")
            results.append(
                {
                    **job,
                    "fit_score": 0,
                    "reasoning": "Scoring unavailable",
                    "match_highlights": "N/A",
                    "scored_at": _now_iso(),
                }
            )

        # Small pause every 10 calls to respect rate limits
        if i % 10 == 0:
            time.sleep(1)

    return results


def _score_one(client: OpenAI, model: str, job: Dict, profile: Dict) -> Dict:
    user_msg = "\n".join(
        [
            "JOB LISTING:",
            f"Title: {job['title']}",
            f"Company: {job['company']}",
            f"Location: {job['location']}",
            f"Salary: {job['salary'] or 'Not specified'}",
            f"Required Skills/Tags: {job['tags']}",
            f"Description: {job['description'][:600]}",
            "",
            "CANDIDATE PROFILE:",
            f"Skills: {profile.get('skills', '')}",
            f"Expected Salary: {profile.get('salary_expectation', '')}",
            f"Preferred Industries: {profile.get('preferred_industries', '')}",
            "",
            "Return JSON only with fit_score (0-100), reasoning (string), "
            "and match_highlights (array of 3 strings).",
        ]
    )

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=400,
        temperature=0.2,
    )

    raw = json.loads(response.choices[0].message.content)

    highlights = raw.get("match_highlights", [])
    if isinstance(highlights, list):
        highlights_str = " | ".join(str(h) for h in highlights[:3])
    else:
        highlights_str = str(highlights)

    return {
        "fit_score": max(0, min(100, int(raw.get("fit_score", 0)))),
        "reasoning": str(raw.get("reasoning", ""))[:200],
        "match_highlights": highlights_str,
    }


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
