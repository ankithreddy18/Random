from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ── Color palette ──────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1a2e4a")
SLATE  = colors.HexColor("#2c4a6e")
ACCENT = colors.HexColor("#2d6a9f")
LIGHT  = colors.HexColor("#f0f4f8")
MID    = colors.HexColor("#6b7c93")
BLACK  = colors.black
WHITE  = colors.white

# ══════════════════════════════════════════════════════════════════════════════
# RESUME PDF
# ══════════════════════════════════════════════════════════════════════════════
def build_resume(path):
    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        leftMargin=0.55*inch, rightMargin=0.55*inch,
        topMargin=0.45*inch,  bottomMargin=0.45*inch,
    )

    # ── Styles ─────────────────────────────────────────────────────────────────
    name_style = ParagraphStyle("name",
        fontName="Helvetica-Bold", fontSize=20, textColor=NAVY,
        leading=24, alignment=TA_CENTER, spaceAfter=2)

    contact_style = ParagraphStyle("contact",
        fontName="Helvetica", fontSize=8.5, textColor=MID,
        leading=12, alignment=TA_CENTER, spaceAfter=6)

    section_style = ParagraphStyle("section",
        fontName="Helvetica-Bold", fontSize=9.5, textColor=WHITE,
        leading=13, spaceBefore=8, spaceAfter=4,
        leftIndent=4, rightIndent=4)

    body_style = ParagraphStyle("body",
        fontName="Helvetica", fontSize=8.5, textColor=BLACK,
        leading=12.5, spaceAfter=1.5, leftIndent=0)

    bold_body = ParagraphStyle("boldbody",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=BLACK,
        leading=12.5, spaceAfter=1)

    bullet_style = ParagraphStyle("bullet",
        fontName="Helvetica", fontSize=8.2, textColor=BLACK,
        leading=12, spaceAfter=1.5,
        leftIndent=12, firstLineIndent=-8)

    italic_style = ParagraphStyle("italic",
        fontName="Helvetica-Oblique", fontSize=8.2, textColor=MID,
        leading=11, spaceAfter=2)

    job_header_style = ParagraphStyle("jobheader",
        fontName="Helvetica-Bold", fontSize=8.8, textColor=SLATE,
        leading=12, spaceAfter=0, spaceBefore=5)

    right_style = ParagraphStyle("right",
        fontName="Helvetica-Oblique", fontSize=8.2, textColor=MID,
        leading=12, alignment=TA_RIGHT)

    skills_label = ParagraphStyle("skillslabel",
        fontName="Helvetica-Bold", fontSize=8.3, textColor=NAVY, leading=12)

    skills_value = ParagraphStyle("skillsvalue",
        fontName="Helvetica", fontSize=8.3, textColor=BLACK, leading=12, spaceAfter=2)

    def section_bar(title):
        data = [[Paragraph(title, section_style)]]
        t = Table(data, colWidths=[doc.width])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), NAVY),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))
        return t

    def job_row(left, right):
        data = [[Paragraph(left, job_header_style), Paragraph(right, right_style)]]
        t = Table(data, colWidths=[doc.width*0.65, doc.width*0.35])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))
        return t

    def skill_row(label, value):
        data = [[Paragraph(f"{label}:", skills_label), Paragraph(value, skills_value)]]
        t = Table(data, colWidths=[1.05*inch, doc.width - 1.05*inch])
        t.setStyle(TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",    (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))
        return t

    def bullet(text):
        return Paragraph(f"• {text}", bullet_style)

    story = []

    # ── Header ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("ANKITH REDDY KASANI", name_style))
    story.append(Paragraph(
        "New York, NY  ·  +1 (839) 201-2827  ·  akasani@nyit.edu  ·  "
        "linkedin.com/in/ankithkasani  ·  github.com/ankithkasani",
        contact_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=5))

    # ── Summary ────────────────────────────────────────────────────────────────
    story.append(section_bar("PROFESSIONAL SUMMARY"))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "Associate Software Engineer with 1.5 years of enterprise Java development at Ernst &amp; Young and a strong "
        "computer science foundation (MS Computer Science, NYIT, GPA 3.8/4.0). Proven full software development "
        "lifecycle ownership — requirements analysis, system design, Java/Python/TypeScript coding, unit testing, "
        "code review, and production deployment — with zero critical defects across 15+ production releases. "
        "Hands-on expertise in Java, Python, JavaScript, TypeScript, and React, grounded in rigorous CS fundamentals "
        "including Operating Systems, Distributed Systems, and Algorithms. Collaborative communicator who thrives in "
        "structured Agile engineering environments and consistently delivers production-quality software.",
        body_style))

    # ── Skills ─────────────────────────────────────────────────────────────────
    story.append(section_bar("TECHNICAL SKILLS"))
    story.append(Spacer(1, 3))
    story.append(skill_row("Languages",
        "Java, Python, JavaScript, TypeScript, SQL, C++, Bash/Shell"))
    story.append(skill_row("Frontend",
        "React.js, TypeScript, JavaScript, Next.js, WebSockets, Redux, REST API Integration, HTML5, CSS3"))
    story.append(skill_row("Backend & APIs",
        "Spring Boot, Node.js, RESTful APIs, Microservices, OAuth2, JWT, Multi-threading, Object-Oriented Design"))
    story.append(skill_row("Databases",
        "PostgreSQL, MySQL, SQL Server, DynamoDB, Firebase"))
    story.append(skill_row("Cloud & DevOps",
        "AWS (EC2, Lambda, S3, Cognito, CloudWatch, IAM, RDS), GCP, Azure, Docker, GitHub Actions, CI/CD"))
    story.append(skill_row("Tools & Practices",
        "Git/GitHub, IntelliJ IDEA, VS Code, Agile/Scrum, Jira, Unit Testing, Code Review, TDD, System Design"))

    # ── Experience ─────────────────────────────────────────────────────────────
    story.append(section_bar("PROFESSIONAL EXPERIENCE"))
    story.append(Spacer(1, 3))

    story.append(job_row("Ernst &amp; Young (EY) — Global Delivery Services", "Bangalore, India"))
    story.append(job_row("<b>Associate Software Engineer</b>", "Sep 2022 – Aug 2023"))
    story.append(bullet(
        "Architected and delivered <b>15+ enterprise Java applications</b> for global financial services clients — "
        "owning full SDLC from requirements analysis and system design through Java coding, unit testing, structured "
        "code review, and production deployment, achieving <b>zero critical defects</b> at go-live across all releases."))
    story.append(bullet(
        "Built and optimized SQL stored procedures and ETL data pipelines supporting high-volume transaction "
        "processing and real-time analytics across multi-region relational databases, reducing manual operational "
        "latency by <b>70%</b>."))
    story.append(bullet(
        "Operated and monitored a distributed fleet of <b>50+ production systems</b> at <b>99.2% uptime</b>; performed "
        "performance profiling, incident triage, and root-cause analysis; authored technical documentation and "
        "maintained a comprehensive knowledge base for all application issues and resolutions."))
    story.append(bullet(
        "Drove cross-functional collaboration across engineering, operations, and finance stakeholder teams in "
        "<b>Agile/Scrum</b> sprints; led structured code reviews enforcing object-oriented design principles, "
        "security standards, and software engineering best practices across all releases."))

    story.append(Spacer(1, 4))
    story.append(job_row("Ernst &amp; Young (EY) — Global Delivery Services", "Bangalore, India"))
    story.append(job_row("<b>Software Engineering Intern</b>", "Jan 2022 – May 2022"))
    story.append(bullet(
        "Built an end-to-end <b>Python</b> machine learning pipeline (TensorFlow, CNN+LSTM) achieving 85% benchmark "
        "accuracy; automated data ingestion and preprocessing reducing processing time by <b>40%</b>; documented "
        "model architecture and presented findings to senior engineering leadership."))

    # ── Projects ───────────────────────────────────────────────────────────────
    story.append(section_bar("PROJECTS"))
    story.append(Spacer(1, 3))

    def project_header(name, stack, year):
        left = f"<b>{name}</b>  <font color='#6b7c93' size='8'>| {stack}</font>"
        return job_row(left, year)

    story.append(project_header(
        "Code Storm — Real-Time Collaborative Platform",
        "React, TypeScript, Node.js, WebSockets, REST APIs", "2024"))
    story.append(bullet(
        "Designed and built a full-stack enterprise platform with <b>React/TypeScript</b> frontend and Node.js "
        "backend featuring sub-second WebSocket synchronization for concurrent sessions, REST API integrations, "
        "AI-driven features, and comprehensive end-to-end testing prior to each release."))

    story.append(Spacer(1, 3))
    story.append(project_header(
        "CryptoSight AI — Full-Stack Cloud Application",
        "Next.js, Python, TypeScript, AWS, GitHub Actions", "2024"))
    story.append(bullet(
        "Architected a production full-stack web application with a serverless <b>Python</b> backend (AWS Lambda), "
        "real-time data ingestion pipelines, JWT authentication via AWS Cognito, and CI/CD deployment via "
        "GitHub Actions on EC2."))

    story.append(Spacer(1, 3))
    story.append(project_header(
        "MT5 Algorithmic Trading System",
        "Python, Statistical Modeling", "2024"))
    story.append(bullet(
        "Engineered a fully autonomous <b>Python</b> execution system with multi-tier signal processing, "
        "statistical regime classification, position sizing logic, circuit breakers, and a complete audit "
        "trail — live in production across multi-asset instruments."))

    # ── Education ──────────────────────────────────────────────────────────────
    story.append(section_bar("EDUCATION"))
    story.append(Spacer(1, 3))

    story.append(job_row(
        "<b>New York Institute of Technology (NYIT)</b>, New York, NY",
        "Expected May 2026"))
    story.append(Paragraph(
        "MS, Computer Science — GPA <b>3.8/4.0</b>", bold_body))
    story.append(Paragraph(
        "Relevant Coursework: Operating Systems, Distributed Systems, Data Structures &amp; Algorithms, "
        "Software Engineering, Cloud Computing, Database Management, Big Data Analytics",
        italic_style))

    story.append(Spacer(1, 4))
    story.append(job_row("<b>Christ University</b>, Bangalore, India", "May 2022"))
    story.append(Paragraph("BS, Computer Science", body_style))

    # ── Certifications ─────────────────────────────────────────────────────────
    story.append(section_bar("CERTIFICATIONS"))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "AWS Certified Cloud Practitioner  ·  Google Cloud Associate Cloud Engineer  ·  "
        "Microsoft Azure Fundamentals (AZ-900)  ·  Machine Learning Specialization – Andrew Ng  ·  "
        "Deep Learning Specialization – Andrew Ng",
        body_style))

    doc.build(story)
    print(f"✓ Resume saved → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# COVER LETTER PDF
# ══════════════════════════════════════════════════════════════════════════════
def build_cover_letter(path):
    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        leftMargin=0.9*inch, rightMargin=0.9*inch,
        topMargin=0.7*inch,  bottomMargin=0.7*inch,
    )

    name_style = ParagraphStyle("clname",
        fontName="Helvetica-Bold", fontSize=18, textColor=NAVY,
        leading=22, alignment=TA_LEFT, spaceAfter=2)

    contact_style = ParagraphStyle("clcontact",
        fontName="Helvetica", fontSize=8.5, textColor=MID,
        leading=13, spaceAfter=10)

    date_style = ParagraphStyle("cldate",
        fontName="Helvetica-Oblique", fontSize=9, textColor=MID,
        leading=13, spaceAfter=4)

    addressee_style = ParagraphStyle("claddress",
        fontName="Helvetica", fontSize=9.5, textColor=BLACK,
        leading=14, spaceAfter=14)

    salutation_style = ParagraphStyle("clsal",
        fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,
        leading=14, spaceAfter=8)

    intro_style = ParagraphStyle("clintro",
        fontName="Helvetica", fontSize=10, textColor=BLACK,
        leading=16, spaceAfter=10)

    q_label_style = ParagraphStyle("qlabel",
        fontName="Helvetica-Bold", fontSize=10, textColor=SLATE,
        leading=14, spaceAfter=2, spaceBefore=8)

    q_body_style = ParagraphStyle("qbody",
        fontName="Helvetica", fontSize=9.5, textColor=BLACK,
        leading=15, spaceAfter=2, leftIndent=14)

    closing_style = ParagraphStyle("clclose",
        fontName="Helvetica", fontSize=10, textColor=BLACK,
        leading=16, spaceAfter=10, spaceBefore=10)

    sig_style = ParagraphStyle("clsig",
        fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,
        leading=14, spaceAfter=2)

    sig_detail_style = ParagraphStyle("clsigdetail",
        fontName="Helvetica", fontSize=8.5, textColor=MID,
        leading=12)

    story = []

    # ── Letterhead ─────────────────────────────────────────────────────────────
    story.append(Paragraph("ANKITH REDDY KASANI", name_style))
    story.append(Paragraph(
        "New York, NY  ·  +1 (839) 201-2827  ·  akasani@nyit.edu  ·  "
        "linkedin.com/in/ankithkasani  ·  github.com/ankithkasani",
        contact_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=14))

    # ── Date & addressee ───────────────────────────────────────────────────────
    story.append(Paragraph("May 2026", date_style))
    story.append(Paragraph(
        "Veeva Systems — Engineering Development Program<br/>"
        "Hiring Team, Raleigh, NC",
        addressee_style))

    # ── Salutation ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Dear Veeva Engineering Team,", salutation_style))

    # ── Intro ──────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "I'm Ankith Reddy Kasani — an MS Computer Science candidate at NYIT (GPA 3.8/4.0) with 1.5 years of "
        "enterprise Java development at Ernst &amp; Young. I'm genuinely excited about the Engineering Development "
        "Program, and per your process, here are the questions that matter most to me:",
        intro_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT, spaceAfter=4))

    # ── Questions ──────────────────────────────────────────────────────────────
    questions = [
        (
            "1. How does EDP structure the transition from onboarding to owning production code?",
            "I care about learning fast and delivering real value. I want to understand how quickly EDP engineers "
            "are trusted with production-level Java work, and what the mentorship structure looks like in those "
            "first months."
        ),
        (
            "2. What does \"delivering value early\" look like in practice for an EDP engineer's first 90 days?",
            "Your program is designed for rapid growth. I'd love to know what a successful first project typically "
            "looks like — is it a feature, a bug-fix cycle, a tooling improvement? What signal tells you an EDP "
            "engineer is thriving?"
        ),
        (
            "3. How do EDP engineers develop domain knowledge in Life Sciences?",
            "Veeva builds industry-specific cloud software, and I believe great engineers understand the domain "
            "they're building for. Are there structured ways for new engineers to learn the Life Sciences context "
            "behind the products they contribute to?"
        ),
        (
            "4. How does Veeva's status as a Public Benefit Corporation influence day-to-day engineering decisions?",
            "I'm drawn to Veeva specifically because of the PBC mission. I'd like to understand whether that "
            "\"do the right thing\" value shows up in technical choices — architecture decisions, data practices, "
            "how tradeoffs are handled — or whether it primarily lives at the business level."
        ),
        (
            "5. How does the Raleigh engineering office collaborate with other Veeva engineering locations?",
            "I want to understand the day-to-day reality of being part of a globally distributed engineering org "
            "while being in-office in Raleigh — how connected are local teams to product decisions and the broader "
            "engineering culture?"
        ),
    ]

    for q_label, q_body in questions:
        story.append(Paragraph(q_label, q_label_style))
        story.append(Paragraph(q_body, q_body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT, spaceAfter=4))

    # ── Closing ────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "Thank you for designing a hiring process that is fast, direct, and respectful of candidates' time — "
        "it reflects the values you describe on your website. I would be glad to bring the same discipline "
        "and integrity to your engineering team.",
        closing_style))

    story.append(Paragraph("Sincerely,", ParagraphStyle("simply",
        fontName="Helvetica", fontSize=10, textColor=BLACK, leading=14, spaceAfter=6)))
    story.append(Paragraph("Ankith Reddy Kasani", sig_style))
    story.append(Paragraph(
        "akasani@nyit.edu  ·  +1 (839) 201-2827  ·  github.com/ankithkasani",
        sig_detail_style))

    doc.build(story)
    print(f"✓ Cover letter saved → {path}")


if __name__ == "__main__":
    build_resume("/home/user/Random/Kasani_Ankith_Resume_Veeva_EDP.pdf")
    build_cover_letter("/home/user/Random/Kasani_Ankith_CoverLetter_Veeva_EDP.pdf")
