import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    google_service_account_file: str
    google_sheet_id: str
    openai_api_key: str
    decodo_api_key: str
    job_source_url: str
    gmail_sender: str
    gmail_app_password: str
    gmail_recipient: str
    fit_score_threshold: int
    max_jobs_per_run: int
    openai_model: str


def load_config() -> Config:
    required = [
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "GOOGLE_SHEET_ID",
        "OPENAI_API_KEY",
        "DECODO_API_KEY",
        "GMAIL_SENDER",
        "GMAIL_APP_PASSWORD",
        "GMAIL_RECIPIENT",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in all values."
        )

    return Config(
        google_service_account_file=os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"],
        google_sheet_id=os.environ["GOOGLE_SHEET_ID"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        decodo_api_key=os.environ["DECODO_API_KEY"],
        job_source_url=os.getenv("JOB_SOURCE_URL", "https://remoteok.com/api"),
        gmail_sender=os.environ["GMAIL_SENDER"],
        gmail_app_password=os.environ["GMAIL_APP_PASSWORD"],
        gmail_recipient=os.environ["GMAIL_RECIPIENT"],
        fit_score_threshold=int(os.getenv("FIT_SCORE_THRESHOLD", "40")),
        max_jobs_per_run=int(os.getenv("MAX_JOBS_PER_RUN", "30")),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
