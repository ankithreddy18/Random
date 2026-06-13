import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

log = logging.getLogger(__name__)


def send_summary_email(cfg, matched_jobs: List[Dict]):
    today = datetime.now().strftime("%A, %B %-d, %Y")
    count = len(matched_jobs)
    subject = f"\U0001f3af {count} Job Match{'es' if count != 1 else ''} Found – {today}"

    html = _build_html(matched_jobs, count, today)
    plain = _build_plain(matched_jobs, count, today)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.gmail_sender
    msg["To"] = cfg.gmail_recipient
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))  # HTML is preferred when supported

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(cfg.gmail_sender, cfg.gmail_app_password)
        server.sendmail(cfg.gmail_sender, cfg.gmail_recipient, msg.as_string())

    log.info(f"Email sent to {cfg.gmail_recipient} — {count} match(es)")


# ── HTML ──────────────────────────────────────────────────────────────────────

_CSS = """
body{font-family:Arial,sans-serif;max-width:650px;margin:0 auto;background:#f4f4f4;color:#333}
.wrap{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.1)}
.hdr{background:linear-gradient(135deg,#667eea,#764ba2);padding:28px 25px}
.hdr h1{color:#fff;margin:0;font-size:22px}
.hdr p{color:rgba(255,255,255,.85);margin:6px 0 0;font-size:14px}
.body{padding:20px 25px}
.card{border:1px solid #e8e8e8;border-radius:10px;padding:18px;margin-bottom:14px;background:#fafafa}
.title{font-size:17px;font-weight:bold;margin:0 0 4px;color:#222}
.meta{color:#666;font-size:13px;margin:0 0 12px}
.badges{margin-bottom:10px}
.badge{display:inline-block;padding:3px 11px;border-radius:20px;font-size:12px;font-weight:bold;margin-right:6px}
.score{background:#e8f5e9;color:#2e7d32}
.salary{background:#e3f2fd;color:#1565c0}
.loc{background:#fce4ec;color:#880e4f}
.note{background:#f0f4ff;border-left:3px solid #667eea;border-radius:0 6px 6px 0;padding:10px 12px;font-size:13px;color:#444;margin:10px 0}
.hi{font-size:12px;color:#777;margin:0 0 12px}
.btn{display:inline-block;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff!important;padding:9px 22px;border-radius:25px;text-decoration:none;font-size:13px;font-weight:bold}
.ftr{text-align:center;padding:18px 25px;background:#f9f9f9;color:#999;font-size:11px;border-top:1px solid #eee}
.empty{text-align:center;padding:40px;color:#999}
"""


def _build_html(jobs: List[Dict], count: int, today: str) -> str:
    if jobs:
        cards = "\n".join(_card_html(j) for j in jobs)
    else:
        cards = "<div class='empty'><p>No jobs matched your profile today. Check back tomorrow!</p></div>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>{_CSS}</style></head>
<body><div class="wrap">
  <div class="hdr">
    <h1>&#127919; AI Job Matches</h1>
    <p>{count} matching job{'s' if count != 1 else ''} found for you &bull; {today}</p>
  </div>
  <div class="body">{cards}</div>
  <div class="ftr">
    Powered by AI Job Automation &bull; OpenAI + Decodo + Google Sheets<br>
    Runs daily at 8:00 AM &bull; Adjust FIT_SCORE_THRESHOLD in .env to tune sensitivity
  </div>
</div></body></html>"""


def _card_html(j: Dict) -> str:
    salary_badge = (
        f"<span class='badge salary'>&#128176; {j['salary']}</span>"
        if j.get("salary")
        else ""
    )
    return f"""
<div class="card">
  <h3 class="title">{j['title']}</h3>
  <p class="meta">{j['company']} &bull; {j.get('location', 'Remote')}</p>
  <div class="badges">
    <span class="badge score">&#11088; {j['fit_score']}/100 Match</span>
    {salary_badge}
    <span class="badge loc">&#128205; {j.get('location', 'Remote')}</span>
  </div>
  <div class="note">{j.get('reasoning', '')}</div>
  <p class="hi">&#10024; {j.get('match_highlights', '')}</p>
  <a href="{j.get('url', '#')}" class="btn">Apply Now &rarr;</a>
</div>"""


# ── Plain text fallback ───────────────────────────────────────────────────────

def _build_plain(jobs: List[Dict], count: int, today: str) -> str:
    lines = [
        f"AI Job Matches — {today}",
        f"{count} job{'s' if count != 1 else ''} matched your profile today.",
        "",
    ]
    if not jobs:
        lines.append("No jobs matched today. Check back tomorrow!")
    else:
        for j in jobs:
            lines += [
                f"[{j['fit_score']}/100] {j['title']} — {j['company']}",
                f"  Location : {j.get('location', 'Remote')}",
                f"  Salary   : {j.get('salary') or 'Not listed'}",
                f"  Match    : {j.get('reasoning', '')}",
                f"  URL      : {j.get('url', '')}",
                "",
            ]
    lines += [
        "---",
        "Powered by AI Job Automation.",
        "Adjust FIT_SCORE_THRESHOLD in .env to change sensitivity.",
    ]
    return "\n".join(lines)
