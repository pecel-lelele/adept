"""Where live job openings come from. Every source is an official, public feed that an employer
or job board publishes for others to read and display. No site that forbids automated access is
used: JobStreet's terms (clause 7(d)) ban scraping, LinkedIn and Indeed offer no public jobs API,
EY's robots.txt disallows its feed path and SmartRecruiters' API host disallows crawlers.
Broad Malaysian job-board coverage comes from the keyed aggregator APIs at the bottom
(Careerjet, Jooble), switched on with a free publisher key.

To add an employer, find the job-board platform behind its careers page (the "Apply" link
usually shows it) and add one line here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Board:
    source: str  # connector name in sources.py
    board: str  # the platform's identifier for the employer or feed
    employer: str  # display name; "" = take it from each posting (job boards)
    host: str = ""  # Workday / Jibe host
    site: str = ""  # Workday career-site name
    query: str = ""  # search text, where the platform needs one


# Employer career sites (applicant tracking systems with a public job-board API).
EMPLOYERS: tuple[Board, ...] = (
    Board("greenhouse", "agoda", "Agoda"),
    Board("greenhouse", "xendit", "Xendit"),
    Board("greenhouse", "okx", "OKX"),
    Board("greenhouse", "bybit", "Bybit"),
    Board("greenhouse", "binance", "Binance"),
    Board("greenhouse", "mongodb", "MongoDB"),
    Board("greenhouse", "adyen", "Adyen"),
    Board("lever", "ninjavan", "Ninja Van"),
    Board("lever", "lalamove", "Lalamove"),
    Board("lever", "dlocal", "dLocal"),
    Board("ashby", "airwallex", "Airwallex"),
    Board("ashby", "mindvalley", "Mindvalley"),
    Board("ashby", "snowflake", "Snowflake"),
    # SmartRecruiters (Bosch, Experian, foodpanda, Continental, SGS, Accor all list Malaysian
    # openings there) is not used: api.smartrecruiters.com/robots.txt disallows every crawler
    # except LinkedIn's. The connector stays for employers that grant API access.
    Board("workday", "intel", "Intel", host="intel.wd1.myworkdayjobs.com", site="External"),
    Board("jibe", "amd", "AMD", host="careers.amd.com"),
    Board(
        "workday", "pwc", "PwC", host="pwc.wd3.myworkdayjobs.com", site="Global_Experienced_Careers"
    ),
    Board("workday", "micron", "Micron", host="micron.wd1.myworkdayjobs.com", site="External"),
    Board("workday", "nxp", "NXP Semiconductors", host="nxp.wd3.myworkdayjobs.com", site="Careers"),
    Board(
        "workday",
        "motorolasolutions",
        "Motorola Solutions",
        host="motorolasolutions.wd5.myworkdayjobs.com",
        site="Careers",
    ),
    Board("workday", "citi", "Citi", host="citi.wd5.myworkdayjobs.com", site="2"),
    Board("workday", "aia", "AIA", host="aia.wd3.myworkdayjobs.com", site="External"),
    Board(
        "workday", "manulife", "Manulife", host="manulife.wd3.myworkdayjobs.com", site="MFCJH_Jobs"
    ),
    Board("workday", "jabil", "Jabil", host="jabil.wd5.myworkdayjobs.com", site="Jabil_Careers"),
    Board(
        "workday", "flextronics", "Flex", host="flextronics.wd1.myworkdayjobs.com", site="Careers"
    ),
    Board("workday", "hp", "HP", host="hp.wd5.myworkdayjobs.com", site="ExternalCareerSite"),
    Board("workday", "sanofi", "Sanofi", host="sanofi.wd3.myworkdayjobs.com", site="SanofiCareers"),
    Board("workday", "gsk", "GSK", host="gsk.wd5.myworkdayjobs.com", site="GSKCareers"),
    Board(
        "workday",
        "astrazeneca",
        "AstraZeneca",
        host="astrazeneca.wd3.myworkdayjobs.com",
        site="Careers",
    ),
    Board(
        "workday",
        "bdx",
        "BD (Becton Dickinson)",
        host="bdx.wd1.myworkdayjobs.com",
        site="EXTERNAL_CAREER_SITE_MALAYSIA",
    ),
    Board(
        "workday",
        "bakerhughes",
        "Baker Hughes",
        host="bakerhughes.wd5.myworkdayjobs.com",
        site="BakerHughes",
    ),
    Board(
        "workday",
        "dxctechnology",
        "DXC Technology",
        host="dxctechnology.wd1.myworkdayjobs.com",
        site="DXCJobs",
    ),
    Board("workday", "spgi", "S&P Global", host="spgi.wd5.myworkdayjobs.com", site="SPGI_Careers"),
    Board("workday", "lseg", "LSEG", host="lseg.wd3.myworkdayjobs.com", site="Careers"),
    Board("workday", "abbott", "Abbott", host="abbott.wd5.myworkdayjobs.com", site="abbottcareers"),
    Board(
        "workday",
        "agilent",
        "Agilent",
        host="agilent.wd5.myworkdayjobs.com",
        site="Agilent_Careers",
    ),
    Board(
        "workday", "amat", "Applied Materials", host="amat.wd1.myworkdayjobs.com", site="External"
    ),
    Board(
        "workday",
        "mastercard",
        "Mastercard",
        host="mastercard.wd1.myworkdayjobs.com",
        site="CorporateCareers",
    ),
    Board("workday", "shell", "Shell", host="shell.wd3.myworkdayjobs.com", site="ShellCareers"),
    Board("workday", "pg", "Procter & Gamble", host="pg.wd5.myworkdayjobs.com", site="1000"),
    Board("workday", "kla", "KLA", host="kla.wd1.myworkdayjobs.com", site="Search"),
    Board("workday", "3m", "3M", host="3m.wd1.myworkdayjobs.com", site="Search"),
    Board(
        "workday",
        "broadcom",
        "Broadcom",
        host="broadcom.wd1.myworkdayjobs.com",
        site="External_Career",
    ),
    Board("workday", "equinix", "Equinix", host="equinix.wd1.myworkdayjobs.com", site="External"),
    Board("workday", "workday", "Workday", host="workday.wd5.myworkdayjobs.com", site="Workday"),
    Board("workday", "fico", "FICO", host="fico.wd1.myworkdayjobs.com", site="External"),
)

# Search terms for remote-job boards: one per family of Adept target roles, so the feed stays
# relevant and small (the boards hold tens of thousands of unrelated listings).
REMOTE_QUERIES: tuple[str, ...] = (
    "data analyst",
    "data engineer",
    "machine learning",
    "automation",
    "cloud engineer",
    "security analyst",
    "product manager",
    "ux designer",
    "digital marketing",
    "business analyst",
    "customer success",
    "compliance",
    "sustainability",
    "supply chain",
)

# Remote-job boards with public APIs (attribution and an unchanged apply link required).
REMOTE: tuple[Board, ...] = (
    Board("himalayas", "himalayas", ""),
    Board("jobicy", "jobicy", ""),
    Board("remoteok", "remoteok", ""),
    Board("remotive", "remotive", ""),
)

# Keyed job-board aggregators. Each runs only when its key is in the environment; without one
# it is skipped and logged. Keys come from a free publisher account and are never committed.
KEYED: tuple[Board, ...] = (
    Board("careerjet", "careerjet-my", ""),  # CAREERJET_API_KEY
    Board("jooble", "jooble-my", ""),  # JOOBLE_API_KEY
    Board("web3career", "web3career", ""),  # WEB3_CAREER_TOKEN (remote Web3 roles)
)

ALL: tuple[Board, ...] = EMPLOYERS + REMOTE + KEYED
