import logging
from typing import Dict, List, Set

from google.oauth2 import service_account
from googleapiclient.discovery import build

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_PROFILE_SHEET = "Candidate Profile"
_OUTPUT_SHEET = "Job Output Sheet"
_OUTPUT_COLS = [
    "job_id", "title", "company", "url", "salary", "location",
    "tags", "fit_score", "reasoning", "match_highlights", "date_posted", "saved_at",
]


def _service(cfg):
    creds = service_account.Credentials.from_service_account_file(
        cfg.google_service_account_file, scopes=_SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_candidate_profile(cfg) -> Dict:
    svc = _service(cfg)
    result = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=cfg.google_sheet_id, range=f"{_PROFILE_SHEET}!A1:Z2")
        .execute()
    )

    values = result.get("values", [])
    if len(values) < 2:
        raise ValueError(
            f"Sheet '{_PROFILE_SHEET}' must have a header row and at least one data row.\n"
            "Upload candidate_profile.csv to get started."
        )

    headers = [h.strip().lower() for h in values[0]]
    row = values[1]
    profile = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
    log.debug(f"Loaded profile: {profile}")
    return profile


def save_matched_jobs(cfg, jobs: List[Dict]) -> int:
    svc = _service(cfg)
    sid = cfg.google_sheet_id

    _ensure_header(svc, sid)
    existing_ids = _existing_job_ids(svc, sid)

    new_rows = [
        [str(job.get(col, "")) for col in _OUTPUT_COLS]
        for job in jobs
        if job["job_id"] not in existing_ids
    ]

    if not new_rows:
        log.info("No new jobs to save — all already present in output sheet.")
        return 0

    svc.spreadsheets().values().append(
        spreadsheetId=sid,
        range=f"{_OUTPUT_SHEET}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()

    log.info(f"Saved {len(new_rows)} new job(s) to '{_OUTPUT_SHEET}'.")
    return len(new_rows)


def _ensure_header(svc, sheet_id: str):
    result = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"{_OUTPUT_SHEET}!A1:L1")
        .execute()
    )
    if not result.get("values"):
        svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{_OUTPUT_SHEET}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [_OUTPUT_COLS]},
        ).execute()
        log.info(f"Created header row in '{_OUTPUT_SHEET}'.")


def _existing_job_ids(svc, sheet_id: str) -> Set[str]:
    result = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"{_OUTPUT_SHEET}!A2:A")
        .execute()
    )
    return {row[0] for row in result.get("values", []) if row}
