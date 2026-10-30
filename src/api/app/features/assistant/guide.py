# ruff: noqa: E501  (EN/BM/ZH answer templates read best as one line each)
"""Adi's guide: routes a question to answer blocks and renders them from checked facts.

Every answer Adi shows is one of these server-authored blocks. A configured model may only
choose among them; without a model, or when its choice is invalid, the routing here decides.
Blocks use [[kind:id]] tags, resolved to official labels by the service.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from app.contracts.assistant import Locale
from app.core.security.sanitize import find_injection
from app.features.assistant.context import Context

# Keywords per intent in English, Malay and Chinese (lower-case; Chinese matched as substrings).
# A multi-word phrase (or a Chinese phrase of three or more characters) counts as a strong hit;
# a single word as a weak one. Ambiguous single words ("pay", "source", "what if", "confidence")
# are deliberately absent: they only count inside the phrase patterns in `PATTERNS`.
INTENTS: dict[str, tuple[str, ...]] = {
    # The safety intents are detected by `_decision_request`, `find_injection` and the
    # possessive check in `intent`; they are listed here only to keep the answer-block order.
    "decision": (),
    "other_person": ("colleague", "coworker", "someone else", "rakan sekerja", "同事", "别人的"),
    "injection": ("hidden instructions", "system prompt", "ignore previous instructions"),
    "sources": (
        "sources",
        "where does this data",
        "data come from",
        "course real",
        "listing real",
        "dari mana data",
        "sumber data",
        "数据来源",
        "数据来自",
    ),
    "scenario": (
        "scenario",
        "scenarios",
        "moves faster",
        "fast scenario",
        "faster ai",
        "ai pace",
        "ai bergerak",
        "lebih laju",
        "senario",
        "情景",
        "更快",
    ),
    "forecast_accuracy": (
        "how accurate",
        "how confident",
        "how reliable",
        "forecast accuracy",
        "ketepatan",
        "准确",
        "置信",
    ),
    "sdg_explain": (
        "what is sdg",
        "apa itu sdg",
        "sdg是什么",
        "sdgs",
        "sdg",
        "plan connect",
        "sdg definitions",
    ),
    "action_not_supported": (
        "delete a course",
        "remove this step",
        "edit my plan",
        "delete this step",
        "remove a course",
        "apply to jobs for me",
        "apply for jobs for me",
        "apply for me",
        "padam kursus",
        "ubah pelan",
        "删除课程",
        "修改计划",
    ),
    "match_detail": (
        "second role",
        "ranked third",
        "ranked second",
        "role ranked",
        "ranked lower",
        "peranan kedua",
        "第二",
        "第三",
    ),
    "no_data": (
        "salary",
        "salaries",
        "jobs in",
        "jobs near",
        "near me",
        "pay range",
        "job location",
        "gaji",
        "薪资",
        "工资",
        "薪水",
    ),
    "trend_declining": (
        "declining",
        "disappear",
        "disappearing",
        "obsolete",
        "losing demand",
        "lose my job",
        "replaced by ai",
        "kurang diperlukan",
        "menurun",
        "hilang",
        "消失",
        "下降",
        "淘汰",
        "被取代",
    ),
    "score_improvement": (
        "improve my match",
        "raise my score",
        "improve my score",
        "tingkatkan skor",
        "提高匹配分数",
    ),
    "score_breakdown": (
        "why is my score",
        "why did i get this score",
        "fit score work",
        "match score work",
        "score calculated",
        "match score",
        "kenapa skor",
        "skor dikira",
        "为什么我的匹配分数",
        "为什么我的分数",
        "分数怎么算",
        "分数如何计算",
    ),
    "profile": (
        "don't have a cv",
        "dont have a cv",
        "do not have a cv",
        "without a cv",
        "no cv",
        "upload my cv",
        "upload a cv",
        "add my skills",
        "update my skills",
        "edit my skills",
        "tiada cv",
        "tak ada cv",
        "muat naik cv",
        "没有简历",
        "上传简历",
    ),
    "privacy": (
        "privacy",
        "employer see",
        "hr see",
        "manager see",
        "who can see",
        "what can hr",
        "majikan nampak",
        "siapa boleh lihat",
        "雇主能看到",
        "谁能看到",
        "stored",
        "store my",
        "my data",
        "personal data",
        "pdpa",
        "delete",
        "privasi",
        "simpan",
        "disimpan",
        "padam",
        "隐私",
        "保存",
        "删除",
        "个人数据",
    ),
    "plan_progress": (
        "progress",
        "finished",
        "completed",
        "completion status",
        "kemajuan",
        "selesai",
        "进度",
        "已完成",
        "完成了",
    ),
    "plan_duration": (
        "how long",
        "duration",
        "weeks",
        "hours",
        "tempoh",
        "berapa lama",
        "minggu",
        "多久",
        "时长",
        "几周",
        "多少小时",
    ),
    "plan_cost": (
        "cost",
        "costs",
        "price",
        "prices",
        "how much",
        "kos",
        "harga",
        "费用",
        "价格",
        "多少钱",
    ),
    "how": (
        "how does",
        "how do",
        "what is adept",
        "how it works",
        "method",
        "methods",
        "bagaimana",
        "apa itu",
        "如何",
        "怎么",
        "是什么",
    ),
    "sdg": (
        "sdg",
        "goal",
        "goals",
        "impact",
        "sustainable",
        "sustainability",
        "matlamat",
        "kelestarian",
        "可持续",
        "目标",
    ),
    "cost": (
        "cost",
        "free",
        "price",
        "prices",
        "costs",
        "hrd",
        "claim",
        "claims",
        "budget",
        "budgets",
        "kos",
        "percuma",
        "harga",
        "tuntut",
        "费用",
        "免费",
        "价格",
        "补贴",
    ),
    "trend": (
        "trend",
        "trends",
        "rising",
        "declining",
        "radar",
        "future",
        "demand",
        "ai pace",
        "tren",
        "meningkat",
        "permintaan",
        "趋势",
        "上升",
        "雷达",
        "未来",
    ),
    "team": (
        "team",
        "member",
        "members",
        "gap",
        "gaps",
        "heatmap",
        "pasukan",
        "ahli",
        "jurang",
        "团队",
        "成员",
        "差距",
    ),
    "learn": (
        "learn",
        "learning",
        "course",
        "courses",
        "skill",
        "skills",
        "plan",
        "plans",
        "study",
        "gap",
        "practice",
        "practise",
        "build confidence",
        "get better at",
        "belajar",
        "kursus",
        "kemahiran",
        "pelan",
        "学习",
        "课程",
        "技能",
        "计划",
    ),
    "roles": (
        "hiring",
        "companies",
        "employers",
        "vacancies",
        "openings",
        "mengambil pekerja",
        "jawatan kosong",
        "招聘",
        "role",
        "roles",
        "job",
        "jobs",
        "match",
        "matches",
        "matched",
        "matching",
        "career",
        "careers",
        "fit",
        "score",
        "scores",
        "why",
        "peranan",
        "kerja",
        "kerjaya",
        "padanan",
        "skor",
        "kenapa",
        "职位",
        "工作",
        "匹配",
        "分数",
        "为什么",
    ),
    "next": ("next", "start", "what should", "begin", "seterusnya", "mula", "下一步", "开始"),
}

PERSONAL_PLAN_INTENTS = frozenset({"plan_progress", "plan_duration", "plan_cost"})
SAFETY_INTENTS = frozenset({"decision", "other_person", "injection"})
FACT_INTENTS = (
    frozenset(
        {
            "sources",
            "scenario",
            "forecast_accuracy",
            "sdg_explain",
            "action_not_supported",
            "match_detail",
            "no_data",
            "score_improvement",
            "score_breakdown",
            "trend_declining",
            "profile",
        }
    )
    | PERSONAL_PLAN_INTENTS
)
PLAN_WORDS = ("plan", "plans", "pelan", "rancangan", "计划")

# Phrase and co-occurrence rules for words that are ambiguous on their own. Each match is a
# strong hit for its intent. "Open source course" is course advice, not a citation request;
# "what if" is a scenario question only when it is about AI pace.
PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "sources": (
        re.compile(r"\b(?:your|the|data|stored|which|what|cite|show)\s+sources\b"),
        re.compile(r"\bdata\s+sources?\b"),
        re.compile(
            r"(?<!open )\bsources?\s+(?:of|for|behind)\s+(?:this|these|the|your)\s+"
            r"(?:data|trends?|figures?|numbers?|forecasts?|snapshot|estimates?)\b"
        ),
        re.compile(r"\bwhere\s+(?:does|do|did)\s+(?:the|this|these|your)\s+\w+\s+come\s+from\b"),
    ),
    "scenario": (
        re.compile(
            r"\bwhat\s+if\s+(?:the\s+)?(?:ai|automation|adoption)\b.*"
            r"\b(?:fast|faster|slow|slower|quick|quicker|speeds?|accelerat\w*|moves?)\b"
        ),
        re.compile(r"\bkalau\s+ai\b"),
    ),
    "forecast_accuracy": (
        re.compile(
            r"\b(?:confidence|confident)\s+(?:in|of|about)\s+(?:the|your|this|these|that)\s+"
            r"(?:forecasts?|predictions?|trends?|estimates?|projections?)\b"
        ),
        re.compile(
            r"\b(?:forecasts?|predictions?|projections?)\s+(?:are\s+|is\s+)?"
            r"(?:accurate|reliable|correct|right|trustworthy)\b"
        ),
        re.compile(r"\btrust\s+(?:the|your|these|this)\s+(?:forecasts?|predictions?)\b"),
    ),
    "no_data": (
        re.compile(r"\bhow\s+much\s+(?:does|do|will|would|can)\b.*\b(?:pay|earn|make)\b"),
        re.compile(r"\bwhat\s+(?:does|do|will)\b.*\bpay\b(?!\s+for)"),
        re.compile(r"\b(?:which|what)\s+(?:city|cities|state|states|location|locations)\b"),
        re.compile(r"\blocation\s+of\s+(?:the\s+)?jobs?\b"),
        re.compile(r"\b(?:kerja|pekerjaan)\s+di\s+[a-z]"),
        re.compile(r"(?:哪个城市|工作地点|职位地点)"),
    ),
    "trend_declining": (
        re.compile(r"\b(?:at\s+risk|risk\s+of|be\s+replaced|being\s+replaced|replaced\s+by)\b"),
        re.compile(r"\b(?:let\s+go|laid\s+off|lose\s+(?:my|our)\s+jobs?)\b.*\b(?:ai|automation)\b"),
    ),
    # Funding: who pays for courses. "Will my employer pay..." also hits course advice.
    "cost": (re.compile(r"\bpay\s+for\b"),),
    # "How much of my plan have I finished?" asks about progress, not price.
    "plan_progress": (re.compile(r"\bhow\s+much\s+of\s+(?:my|the|this)\b"),),
    # Weekly study time stated without the word "plan" still asks about the plan's duration.
    "plan_duration": (
        re.compile(r"\b\d+\s*(?:hours?|hrs?|h)\s+(?:a|per|each|every)\s+week\b"),
        re.compile(r"\b\d+\s*jam\s+(?:seminggu|setiap\s+minggu)\b"),
        re.compile(r"每周[^，。？]{0,4}?\d+\s*(?:个)?小时"),
    ),
}
# Intents whose phrase patterns satisfy the "about my saved plan" requirement on their own.
PLAN_PATTERN_INTENTS = frozenset({"plan_duration"})
# Two answer blocks are shown when the runner-up intent scores at least this share of the top.
NEAR_TIE = 0.8

# People decisions: a request to decide about a person, never an ordinary career question.
# "Which roles are hiring?", "Will this course get me promoted?" and "admission requirements"
# are learner questions; "Should I hire Ali?" and "Who should I let go?" are decisions.
_EN_DECIDE = (
    r"(?:hire|fire|sack|promote|demote|admit|reject|dismiss|terminate|shortlist"
    r"|let\s+(?:\w+\s+)?go|lay\s+(?:\w+\s+)?off)"
)
_EN_DECIDED = (
    r"(?:hired|fired|sacked|promoted|demoted|admitted|rejected|dismissed|let\s+go|laid\s+off)"
)
_EN_PERSON = (
    r"(?:him|her|them|this\s+person|that\s+person|someone|somebody|anyone|anybody"
    r"|(?:this|that|the|a|my|our)\s+(?:candidate|applicant|employee|worker|student|member|person)"
    r"|candidates|applicants|employees|staff|members|people|workers|students|interns|__person__)"
)
_DECISION_EN = (
    re.compile(
        r"\b(?:who|whom|which\s+(?:one|candidate|applicant|employee|member|person|worker|student)s?)"
        r"\b.*\b(?:should|shall|do|to|can|must|would|could|will)\b.*\b" + _EN_DECIDE + r"\b"
    ),
    re.compile(
        r"\b(?:who|whom|which\s+(?:candidate|applicant|employee|member|person|worker|student)s?)"
        r"\b.*\b(?:should|to|must|will)\s+(?:be|get)\s+" + _EN_DECIDED + r"\b"
    ),
    re.compile(
        # Explicit decision questions must not depend on a person's name being capitalised.
        r"\b(?:should|shall|must|can|could|would)\s+(?:i|we|you|adi|adept)\s+(?:\w+\s+)?"
        + _EN_DECIDE
        + r"\b"
    ),
    re.compile(
        r"\b(?:i|we|you|me|us|adi|adept)\b.*\b"
        + _EN_DECIDE
        + r"(?:\s+or\s+"
        + _EN_DECIDE
        + r")?\s+"
        + _EN_PERSON
        + r"\b"
    ),
)
_MS_DECIDE = (
    r"(?:pecat|memecat|buang\s+kerja|berhentikan|memberhentikan|ambil\s+bekerja|upah|mengupah"
    r"|naikkan\s+pangkat|lantik|melantik|(?:ambil|terima|tolak)\s+(?:dia|calon|pemohon|pekerja|staf|__person__))"
)
_DECISION_MS = (
    re.compile(
        r"\b(?:patut|patutkah|perlu|perlukah|wajar|wajarkah|boleh|bolehkah|harus|haruskah)\s+"
        r"(?:saya|kami|kita|anda|adi|adept)\s+(?:\w+\s+)?" + _MS_DECIDE + r"\b"
    ),
    re.compile(r"\bsiapa\b.*\b" + _MS_DECIDE + r"\b"),
)
_ZH_DECIDE = r"(?:录用|雇用|聘用|解雇|开除|辞退|裁掉|晋升|提拔|录取)"
_DECISION_ZH = (
    re.compile(r"谁.*" + _ZH_DECIDE + "|" + _ZH_DECIDE + r".*谁"),
    re.compile(
        r"(?:该|应该|应不应该|要不要|是否|帮我决定)[^，。？！?]{0,4}?"
        + _ZH_DECIDE
        + r"[^，。？！?]{0,8}?(?:吗|他|她|候选人|员工|这个人|__person__)"
    ),
)
# Capitalised words that are not people's names when they appear mid-sentence.
_NOT_NAMES = frozenset(
    {"i", "adept", "adi", "ai", "hr", "hrd", "corp", "sdg", "sdgs", "un", "cv", "sql", "python"}
)
# Manager questions that pair a people-decision topic with a person are decisions too.
_MANAGER_DECISION = re.compile(
    r"\b(?:hire|hiring|fire|firing|promot\w*|admi(?:t|ssion)\w*|let\s+go|lay\s*off|layoffs?"
    r"|dismiss\w*|terminat\w*|sack\w*)\b"
)
_MANAGER_PERSON = re.compile(_EN_PERSON + r"|\bteam\s+members?\b|\bmy\s+team\b")
_DECISION_TYPOS = ("promote", "dismiss", "terminate", "shortlist", "demote", "reject")
# "Ali's match score", "Sarah's CV": another person's data.
_POSSESSIVE = re.compile(
    r"\b([a-z][a-z-]*)[’']s\s+(?:(?:match|fit|skill|skills|career|learning|saved|own|latest"
    r"|current|top|personal|test|trend)\s+){0,2}"
    r"(?:cv|resume|skills?|scores?|profile|plans?|matches|progress|gaps?|results?|data|roles?)\b"
)
_NOT_PEOPLE = frozenset(
    {
        "profile",
        "plan",
        "course",
        "role",
        "job",
        "company",
        "organisation",
        "organization",
        "team",
        "adept",
        "adi",
        "today",
        "employer",
        "industry",
        "malaysia",
        "it",
        "that",
        "what",
        "who",
        "there",
        "here",
        "he",
        "she",
        "let",
        "where",
    }
)
_MALAY_CUES = frozenset(
    {
        "saya",
        "anda",
        "apa",
        "apakah",
        "bagaimana",
        "macam",
        "mana",
        "kenapa",
        "mengapa",
        "adakah",
        "bolehkah",
        "berapa",
        "yang",
        "dengan",
        "untuk",
        "tidak",
        "tak",
        "nak",
        "ini",
        "itu",
        "kemahiran",
        "kerjaya",
        "pelan",
        "kursus",
        "pekerjaan",
        "peranan",
        "skor",
        "sumber",
        "dari",
        "daripada",
        "akan",
        "boleh",
        "jika",
        "kalau",
    }
)
_ENGLISH_CUES = frozenset(
    {"the", "is", "are", "my", "what", "how", "why", "which", "do", "does", "you", "should"}
)

T: dict[str, dict[str, str]] = {
    "en": {
        "decision": "Adept supports your judgement, it never makes hiring, firing, promotion, or admission decisions.",
        "other_person": "I can discuss only your own data in this conversation. I cannot reveal another person's CV, skills, scores or private plans.",
        "injection": "I cannot follow requests to override the rules or reveal hidden instructions. I can help explain your Adept results.",
        "action_not_supported": "Chat cannot edit or delete courses or plan steps. Review your plan on [[page:/app/pathway]], or choose a different target using [[page:/app/pathway/compare]].",
        "no_data": "I do not have verified salary figures or location-specific job results in this conversation. I will not guess. Browse [[page:/app/jobs]] and check the employer's posting.",
        "forecast_accuracy": "These forecasts are scenario estimates from dated research attention and labour projections, not calibrated probabilities or guarantees. Adept has no verified predictive-accuracy figure for your outcome. Sparse coverage, old observation windows and fixture fallback can limit the results. Check the source dates on [[page:/app/radar]].",
        "sources": "Snapshot {date}. Stored sources: {sources}. Courses in your plan: {courses}. Course links open provider pages; check employer postings for jobs. Chat cannot confirm current availability or prices.",
        "sources_fallback": "Showing the last good snapshot from {date} (fallback data: the latest trend data could not be loaded). ",
        "unavailable_busy": "I'm still working on your previous question. Please wait for that answer, then ask again.",
        "unavailable_overloaded": "Adi is answering many questions right now. Please try again in a moment.",
        "unavailable_timeout": "I could not load your results in time. Please try again shortly. See [[page:/about]].",
        "unavailable_catalogue": "I could not check every reference in this answer against the catalogue, so I will not show it. Please try again. See [[page:/about]].",
        "sources_unavailable": "I could not load source records for this answer. Check [[page:/about]]; I will not invent a citation.",
        "scenario": "Estimated scores under {before} → {after}, using the same profile and dated snapshot: {rows}. Ranks are relative and may stay unchanged. This compares scenarios; it does not change your selected scenario. Use the AI pace toggle on [[page:/app/matches]].",
        "scenario_unavailable": "I could not load a comparable second scenario for your profile. Both scenarios are estimates, not guarantees. Use the AI pace toggle on [[page:/app/radar]] to compare available data.",
        "pace_moderate": "Moderate",
        "pace_fast": "Fast",
        "sdg_explain": "The UN Sustainable Development Goals link learning and work to public targets. Official target wording from Adept's SDG catalogue: {targets}. Plan links are enabling hypotheses, not measured UN-target progress. See [[page:/app/sdg]].",
        "sdg_unavailable": "That SDG definition is not available in my catalogue context. I will not invent it; check [[page:/app/sdg]].",
        "rank_unavailable": "That rank is not available in your current results. Check [[page:/app/matches]]; I will not invent a role.",
        "rank_context": "This is rank {rank}. The leading role is [[role:{role}]] at {score} estimated points. Rankings use the weighted components; tied scores use catalogue ID order.",
        "trend_declining": "Declining skills in this snapshot: {skills}. Declining roles: {roles}. These are estimates from research attention and labour projections, not a prediction that a job will disappear. See [[page:/app/radar]].",
        "score_math": "Estimated fit for [[role:{role}]] (weight × component = points): {parts}. Total = {total} points out of 100.",
        "skill_overlap": "skill overlap",
        "trend_outlook": "trend outlook",
        "interest_fit": "interest fit",
        "neutral": " (not provided, neutral value)",
        "profile": "No CV? No problem: on [[page:/app/onboarding]] you can pick your skills and levels by hand, or upload a CV (PDF, Word or text). The file is read in memory and not stored, and you confirm every skill before it is saved. Update them later on [[page:/app/profile]].",
        "improvement": "Close [[skill:{skill}]] for an estimated +{gain} score points. {course}.",
        "no_closing_course": "No catalogue course closes this gap yet",
        "hello": "Hi, I'm Adi! I can explain your matched roles, what to learn next, how skills "
        "are trending, course costs and HRD Corp claims, and how your path links to the UN SDGs.",
        "no_profile": "First, tell me your skills: it takes two minutes on [[page:/app/onboarding]]. "
        "Then I can rank future roles for you and show the gap.",
        "visitor_next": "Try the free CV preview on the home page, or [[page:/auth/signup]] to see "
        "your matched roles, skills gap and a learning plan.",
        "top": "Your strongest match is [[role:{role}]] with an estimated fit of {score}.",
        "others": "Next: {roles}.",
        "gap": "To close the gap, focus on {skills}.",
        "no_gap": "You already meet its required skills; your plan can deepen them.",
        "why": "It is an estimate, not a guarantee.",
        "plan": "Your saved plan for [[role:{role}]] starts with [[skill:{skill}]] through "
        "[[course:{course}]]. Track it on [[page:/app/progress]].",
        "no_plan": "Pick a role and save a plan on [[page:/app/pathway]]; I'll then walk you "
        "through it step by step.",
        "trend": "In the latest snapshot these skills are rising: {skills}. Trends are estimates "
        "from research attention and labour projections; see [[page:/app/radar]].",
        "my_trend": "Your own skills: {skills}.",
        "cost": "Every course shows hours, its dated list price and HRD Corp claimability. "
        "Eligibility does not guarantee funding: confirm certificate fees, taxes and employer "
        "approval before buying. Browse [[page:/app/courses]].",
        "plan_progress": "For your saved plan toward [[role:{role}]], {share} of tracked learning hours are recorded complete; {courses} courses are recorded complete and {closed} of {total} skill gaps are closed. Course completion does not guarantee all role skills are met. See [[page:/app/progress]].",
        "plan_duration": "Your saved plan toward [[role:{role}]] estimates {weeks} weeks at {weekly} hours per week, with {hours} study hours in total. These are learning estimates, not a completion guarantee. See [[page:/app/pathway]].",
        "plan_cost": "Your saved plan toward [[role:{role}]] records an estimated list price of RM {listed} and learner cost of RM {learner} under its saved funding assumptions. Confirm certificate fees, taxes, current prices and employer approval before purchase. See [[page:/app/pathway]].",
        "progress_unavailable": "I could not load your saved plan's progress. Please retry or check [[page:/app/progress]]; I cannot assume zero completion.",
        "totals_unavailable": "I could not load the totals for your saved plan. Please retry or check [[page:/app/pathway]]; I cannot estimate missing figures.",
        "sdg": "Each role and skill links to UN SDG targets with a cited reason.{badges} See "
        "[[page:/app/sdg]].",
        "privacy": "Your CV file is read in memory and not stored; you confirm the extracted skills before they are saved. When AI services are enabled, sanitised chat text and candidate answers may be processed by RunPod or Google Gemini, and optional skill matching sends short contact-redacted skill phrases to Gemini, never the CV file. You can download or delete your data from My skills (or team Settings). Details: [[page:/privacy]]; AI models in use: [[page:/about]].",
        "how": "Adept takes you from today's skills to future roles: skill profile → Future "
        "Skills Radar → matched roles with a skills gap → an ordered learning plan linked to the "
        "UN SDGs. Every estimate shows its source and date. [[page:/about]]",
        "team": "Your team: {members} members, {complete} with a complete profile.{gap}",
        "team_gap": " The largest average gap is for [[role:{role}]] ({gap}).",
        "team_plan": " The team plan targets [[role:{role}]]: see [[page:/org/plan]].",
        "team_none": "Share your join code from [[page:/org/members]] so your people can add "
        "their skills; then I can show the gaps.",
        "plan_done": "You have completed every course in your saved plan toward [[role:{role}]]. {gaps} Compare other roles on [[page:/app/pathway/compare]] or check your skills on [[page:/app/progress]].",
        "plan_done_gaps": "{open} required skill(s) still need practice or courses the catalogue does not yet cover.",
        "plan_done_closed": "Its listed skill gaps are closed.",
        "work_pending": "In {org}, the programme “{title}” toward [[role:{role}]] is waiting for your answer. Review the learning agreement on [[page:/work/plan]]: accept it, or ask for a change.",
        "work_active": "In {org}, your programme “{title}” builds toward [[role:{role}]] by {date}, with {hours} hours a week of paid learning time and up to RM {budget} from your employer. {share} of its course hours are recorded complete.",
        "work_next": " Next: [[course:{course}]]. Track it on [[page:/work/progress]].",
        "work_done": " Every course is recorded complete; HR reviews the evidence on [[page:/work/progress]].",
        "work_none": "{org} has not sent you a programme yet. When it does, you will review the agreement on [[page:/work/plan]]. Your personal plans stay in your personal workspace.",
        "work_roles": "Career exploration is private and lives in your personal workspace: switch to Personal to see your matched roles. Here in {org} I only cover its programmes.",
        "privacy_work": "{org} sees your programme progress, the evidence you submit or share here{skills}. Your personal plans, matches and conversations with me stay private. Change sharing on [[page:/work/skills]].",
        "privacy_shared": ", and the skill levels you chose to share",
        "privacy_not_shared": "; you are not sharing your skill levels",
        "programmes": " Programmes: {count} sent; {accepted} accepted, {pending} waiting, {changes} asked for changes, {declined} declined. See [[page:/org/programmes]].",
        "programmes_none": " No programme sent yet: start from a business objective on [[page:/org/programmes/new]].",
        "team_shared": " {shared} of them share their skill levels.",
    },
    "ms": {
        "decision": "Adept menyokong pertimbangan anda; ia tidak membuat keputusan pengambilan, pemecatan, kenaikan pangkat atau kemasukan.",
        "other_person": "Saya hanya boleh membincangkan data anda sendiri dalam perbualan ini. Saya tidak boleh mendedahkan CV, kemahiran, skor atau pelan peribadi orang lain.",
        "injection": "Saya tidak boleh mengikut permintaan untuk mengetepikan peraturan atau mendedahkan arahan tersembunyi. Saya boleh membantu menerangkan hasil Adept anda.",
        "action_not_supported": "Sembang tidak boleh mengedit atau memadam kursus atau langkah pelan. Semak pelan di [[page:/app/pathway]], atau pilih sasaran lain melalui [[page:/app/pathway/compare]].",
        "no_data": "Saya tiada angka gaji yang disahkan atau hasil pekerjaan mengikut lokasi dalam perbualan ini. Saya tidak akan meneka. Lihat [[page:/app/jobs]] dan semak iklan majikan.",
        "forecast_accuracy": "Unjuran ini ialah anggaran senario berdasarkan perhatian penyelidikan bertarikh dan unjuran tenaga kerja, bukan kebarangkalian terkalibrasi atau jaminan. Adept tiada ukuran ketepatan ramalan yang disahkan untuk hasil anda. Liputan terhad, tempoh pemerhatian lama dan data sandaran boleh mengehadkan hasil. Semak tarikh sumber di [[page:/app/radar]].",
        "sources": "Petikan {date}. Sumber tersimpan: {sources}. Kursus dalam pelan anda: {courses}. Pautan kursus membuka halaman penyedia; semak iklan majikan bagi pekerjaan. Sembang tidak dapat mengesahkan ketersediaan atau harga semasa.",
        "sources_fallback": "Memaparkan petikan baik terakhir bertarikh {date} (data sandaran: data trend terkini tidak dapat dimuatkan). ",
        "unavailable_busy": "Saya masih menjawab soalan anda sebelum ini. Tunggu jawapan itu, kemudian tanya lagi.",
        "unavailable_overloaded": "Adi sedang menjawab banyak soalan. Cuba lagi sebentar.",
        "unavailable_timeout": "Saya tidak dapat memuatkan hasil anda tepat pada masanya. Cuba lagi sebentar. Lihat [[page:/about]].",
        "unavailable_catalogue": "Saya tidak dapat menyemak setiap rujukan dalam jawapan ini dengan katalog, jadi saya tidak akan memaparkannya. Cuba lagi. Lihat [[page:/about]].",
        "sources_unavailable": "Saya tidak dapat memuatkan rekod sumber untuk jawapan ini. Semak [[page:/about]]; saya tidak akan mereka-reka rujukan.",
        "scenario": "Anggaran skor {before} → {after}, menggunakan profil dan petikan bertarikh yang sama: {rows}. Kedudukan adalah relatif dan mungkin kekal. Ini perbandingan senario, bukan perubahan pilihan anda. Gunakan suis kadar AI di [[page:/app/matches]].",
        "scenario_unavailable": "Saya tidak dapat memuatkan senario kedua yang setanding untuk profil anda. Kedua-duanya anggaran, bukan jaminan. Gunakan suis kadar AI di [[page:/app/radar]] untuk membandingkan data tersedia.",
        "pace_moderate": "Sederhana",
        "pace_fast": "Pantas",
        "sdg_explain": "Matlamat Pembangunan Mampan PBB mengaitkan pembelajaran dan pekerjaan dengan sasaran awam. Takrif sasaran rasmi daripada katalog SDG Adept: {targets}. Pautan pelan ialah hipotesis sokongan, bukan kemajuan terukur sasaran PBB. Lihat [[page:/app/sdg]].",
        "sdg_unavailable": "Takrif SDG itu tiada dalam konteks katalog saya. Saya tidak akan mereka-rekanya; semak [[page:/app/sdg]].",
        "rank_unavailable": "Kedudukan itu tiada dalam hasil semasa anda. Semak [[page:/app/matches]]; saya tidak akan mereka-reka peranan.",
        "rank_context": "Ini kedudukan {rank}. Peranan teratas ialah [[role:{role}]] dengan anggaran {score} mata. Kedudukan menggunakan komponen berwajaran; skor seri disusun mengikut ID katalog.",
        "trend_declining": "Kemahiran yang menurun dalam petikan ini: {skills}. Peranan yang menurun: {roles}. Ini anggaran berdasarkan perhatian penyelidikan dan unjuran tenaga kerja, bukan ramalan bahawa kerja akan hilang. Lihat [[page:/app/radar]].",
        "score_math": "Anggaran padanan untuk [[role:{role}]] (wajaran × komponen = mata): {parts}. Jumlah = {total} mata daripada 100.",
        "skill_overlap": "pertindihan kemahiran",
        "trend_outlook": "prospek trend",
        "interest_fit": "kesesuaian minat",
        "neutral": " (tidak diberi, nilai neutral)",
        "profile": "Tiada CV? Tidak mengapa: di [[page:/app/onboarding]] anda boleh memilih kemahiran dan tahap sendiri, atau muat naik CV (PDF, Word atau teks). Fail dibaca dalam memori dan tidak disimpan, dan anda mengesahkan setiap kemahiran sebelum disimpan. Kemas kini kemudian di [[page:/app/profile]].",
        "improvement": "Tutup jurang [[skill:{skill}]] untuk anggaran +{gain} mata skor. {course}.",
        "no_closing_course": "Belum ada kursus katalog yang menutup jurang ini",
        "hello": "Hai, saya Adi! Saya boleh terangkan peranan padanan anda, apa perlu dipelajari, "
        "tren kemahiran, kos kursus dan tuntutan HRD Corp, serta kaitan laluan anda dengan SDG PBB.",
        "no_profile": "Mula-mula, beritahu kemahiran anda: dua minit di [[page:/app/onboarding]]. "
        "Kemudian saya boleh menyenaraikan peranan masa depan dan jurangnya.",
        "visitor_next": "Cuba pratonton CV percuma di halaman utama, atau [[page:/auth/signup]] "
        "untuk melihat peranan padanan, jurang kemahiran dan pelan pembelajaran.",
        "top": "Padanan terkuat anda ialah [[role:{role}]] dengan anggaran kesesuaian {score}.",
        "others": "Seterusnya: {roles}.",
        "gap": "Untuk merapatkan jurang, fokus pada {skills}.",
        "no_gap": "Anda sudah memenuhi kemahiran yang diperlukan; pelan anda boleh mendalaminya.",
        "why": "Ia anggaran, bukan jaminan.",
        "plan": "Pelan anda untuk [[role:{role}]] bermula dengan [[skill:{skill}]] melalui "
        "[[course:{course}]]. Jejak di [[page:/app/progress]].",
        "no_plan": "Pilih peranan dan simpan pelan di [[page:/app/pathway]]; saya akan bimbing "
        "anda langkah demi langkah.",
        "trend": "Dalam petikan terkini, kemahiran ini meningkat: {skills}. Tren ialah anggaran; "
        "lihat [[page:/app/radar]].",
        "my_trend": "Kemahiran anda: {skills}.",
        "cost": "Setiap kursus menunjukkan jam, harga bertarikh dan kelayakan tuntutan HRD Corp. "
        "Kelayakan tidak menjamin pembiayaan: sahkan yuran sijil, cukai dan kelulusan majikan "
        "sebelum membeli. Lihat [[page:/app/courses]].",
        "plan_progress": "Untuk pelan tersimpan bagi [[role:{role}]], {share} jam pembelajaran direkodkan selesai; {courses} kursus direkodkan selesai dan {closed} daripada {total} jurang kemahiran ditutup. Tamat kursus tidak menjamin semua kemahiran peranan dipenuhi. Lihat [[page:/app/progress]].",
        "plan_duration": "Pelan tersimpan bagi [[role:{role}]] menganggarkan {weeks} minggu pada {weekly} jam seminggu, dengan jumlah {hours} jam belajar. Ini anggaran pembelajaran, bukan jaminan tarikh tamat. Lihat [[page:/app/pathway]].",
        "plan_cost": "Pelan tersimpan bagi [[role:{role}]] merekodkan anggaran harga senarai RM {listed} dan kos pelajar RM {learner} berdasarkan andaian pembiayaan tersimpan. Sahkan yuran sijil, cukai, harga semasa dan kelulusan majikan sebelum membeli. Lihat [[page:/app/pathway]].",
        "progress_unavailable": "Saya tidak dapat memuatkan kemajuan pelan tersimpan. Cuba lagi atau lihat [[page:/app/progress]]; saya tidak boleh menganggap kemajuan sifar.",
        "totals_unavailable": "Saya tidak dapat memuatkan jumlah pelan tersimpan. Cuba lagi atau lihat [[page:/app/pathway]]; saya tidak boleh menganggar angka yang tiada.",
        "sdg": "Setiap peranan dan kemahiran dikaitkan dengan sasaran SDG PBB beserta "
        "sebabnya.{badges} Lihat [[page:/app/sdg]].",
        "privacy": "Fail CV anda dibaca dalam memori dan tidak disimpan; anda mengesahkan kemahiran yang diekstrak sebelum disimpan. Apabila perkhidmatan AI diaktifkan, teks sembang yang dibersihkan dan calon jawapan mungkin diproses oleh RunPod atau Google Gemini, dan padanan kemahiran pilihan menghantar frasa kemahiran pendek yang maklumat hubungannya disunting ke Gemini, bukan fail CV. Anda boleh muat turun atau padam data anda di Kemahiran saya. Butiran: [[page:/privacy]]; model AI yang digunakan: [[page:/about]].",
        "how": "Adept membawa anda dari kemahiran hari ini ke peranan masa depan: profil → Radar "
        "Kemahiran Masa Depan → peranan padanan → pelan pembelajaran yang dikaitkan dengan SDG "
        "PBB. Setiap anggaran ada sumber dan tarikh. [[page:/about]]",
        "team": "Pasukan anda: {members} ahli, {complete} dengan profil lengkap.{gap}",
        "team_gap": " Jurang purata terbesar ialah untuk [[role:{role}]] ({gap}).",
        "team_plan": " Pelan pasukan menyasarkan [[role:{role}]]: lihat [[page:/org/plan]].",
        "team_none": "Kongsi kod sertai dari [[page:/org/members]] supaya pasukan anda boleh "
        "menambah kemahiran mereka.",
        "plan_done": "Anda telah menamatkan semua kursus dalam pelan tersimpan untuk [[role:{role}]]. {gaps} Bandingkan peranan lain di [[page:/app/pathway/compare]] atau semak kemahiran di [[page:/app/progress]].",
        "plan_done_gaps": "{open} kemahiran yang diperlukan masih perlu latihan atau kursus yang belum ada dalam katalog.",
        "plan_done_closed": "Jurang kemahiran yang disenaraikan telah ditutup.",
        "work_pending": "Di {org}, program “{title}” untuk [[role:{role}]] menunggu jawapan anda. Semak perjanjian pembelajaran di [[page:/work/plan]]: terima, atau minta perubahan.",
        "work_active": "Di {org}, program “{title}” anda menuju [[role:{role}]] menjelang {date}, dengan {hours} jam seminggu masa belajar berbayar dan sehingga RM {budget} daripada majikan. {share} jam kursus direkodkan selesai.",
        "work_next": " Seterusnya: [[course:{course}]]. Jejak di [[page:/work/progress]].",
        "work_done": " Semua kursus direkodkan selesai; HR menyemak bukti di [[page:/work/progress]].",
        "work_none": "{org} belum menghantar program kepada anda. Apabila dihantar, anda akan menyemak perjanjian di [[page:/work/plan]]. Pelan peribadi anda kekal di ruang kerja peribadi.",
        "work_roles": "Penerokaan kerjaya adalah peribadi dan berada di ruang kerja peribadi: tukar ke Peribadi untuk melihat peranan padanan. Di {org} saya hanya membantu dengan programnya.",
        "privacy_work": "{org} melihat kemajuan program anda, bukti yang anda hantar atau kongsi di sini{skills}. Pelan peribadi, padanan dan perbualan anda dengan saya kekal peribadi. Ubah perkongsian di [[page:/work/skills]].",
        "privacy_shared": ", dan tahap kemahiran yang anda pilih untuk dikongsi",
        "privacy_not_shared": "; anda tidak berkongsi tahap kemahiran",
        "programmes": " Program: {count} dihantar; {accepted} diterima, {pending} menunggu, {changes} minta perubahan, {declined} ditolak. Lihat [[page:/org/programmes]].",
        "programmes_none": " Belum ada program dihantar: mulakan dari objektif perniagaan di [[page:/org/programmes/new]].",
        "team_shared": " {shared} daripadanya berkongsi tahap kemahiran.",
    },
    "zh": {
        "decision": "Adept 为您的判断提供支持，绝不作出招聘、解雇、晋升或录取决定。",
        "other_person": "我只能在此对话中讨论您自己的数据，不能透露他人的简历、技能、分数或私人计划。",
        "injection": "我不能遵循绕过规则或泄露隐藏指令的请求。我可以帮助解释您的 Adept 结果。",
        "action_not_supported": "聊天无法编辑或删除课程及计划步骤。请到 [[page:/app/pathway]] 查看计划，或通过 [[page:/app/pathway/compare]] 选择其他目标。",
        "no_data": "此对话中没有经过核实的薪资数据或按地点筛选的职位结果。我不会猜测。请浏览 [[page:/app/jobs]] 并查看雇主发布的信息。",
        "forecast_accuracy": "这些预测是根据有日期的研究关注度与劳动力预测形成的情景估计，并非经过校准的概率或保证。Adept 没有针对您个人结果的已验证预测准确率。覆盖不足、旧观察时间段及备用快照会限制结果。请在 [[page:/app/radar]] 查看来源日期。",
        "sources": "快照日期：{date}。已存来源：{sources}。您的计划课程：{courses}。课程链接指向提供方页面；职位请核对雇主信息。聊天无法确认当前供应情况或价格。",
        "sources_fallback": "正在显示 {date} 的最近一次可用快照（备用数据：无法加载最新趋势数据）。",
        "unavailable_busy": "我还在回答你上一个问题，请等待该回答后再提问。",
        "unavailable_overloaded": "Adi 正在回答很多问题，请稍后再试。",
        "unavailable_timeout": "暂时无法及时加载你的结果，请稍后重试。详见 [[page:/about]]。",
        "unavailable_catalogue": "此回答中的部分引用无法与目录核对，因此不会显示。请重试。详见 [[page:/about]]。",
        "sources_unavailable": "无法加载此回答的来源记录。请查看 [[page:/about]]；我不会编造引用。",
        "scenario": "在相同资料和同一日期快照下，{before} → {after}的估计分数：{rows}。排名是相对的，也可能不变。这是情景比较，不会更改您的选择。请在 [[page:/app/matches]] 使用 AI 变化速度切换。",
        "scenario_unavailable": "无法加载适合您资料的第二个可比情景。两种情景都是估计，并非保证。请在 [[page:/app/radar]] 使用 AI 变化速度切换来比较可用数据。",
        "pace_moderate": "适度",
        "pace_fast": "快速",
        "sdg_explain": "联合国可持续发展目标将学习和工作与公共目标联系起来。Adept 的 SDG 目录中的官方目标定义：{targets}。计划关联是提供支持的假设，并非联合国目标的实测进展。请查看 [[page:/app/sdg]]。",
        "sdg_unavailable": "当前目录上下文中没有该 SDG 定义。我不会编造，请查看 [[page:/app/sdg]]。",
        "rank_unavailable": "当前结果中没有该名次。请查看 [[page:/app/matches]]；我不会编造职位。",
        "rank_context": "这是第 {rank} 名。领先职位为 [[role:{role}]]，估计得分 {score}。排名由加权分数组成，同分时按目录 ID 排序。",
        "trend_declining": "此快照中需求下降的技能：{skills}。需求下降的职位：{roles}。这些是基于研究关注度和劳动力预测的估计，并不表示某个工作一定会消失。请查看 [[page:/app/radar]]。",
        "score_math": "[[role:{role}]] 的估计匹配度（权重 × 分项 = 得分）：{parts}。总计 = {total} 分，满分 100。",
        "skill_overlap": "技能重合",
        "trend_outlook": "趋势前景",
        "interest_fit": "兴趣契合",
        "neutral": "（未提供，取中性值）",
        "profile": "没有简历也没关系：在 [[page:/app/onboarding]] 可以手动选择技能和水平，或上传简历（PDF、Word 或文本）。文件只在内存中读取、不会保存，每项技能都由你确认后才保存。之后可在 [[page:/app/profile]] 更新。",
        "improvement": "弥补 [[skill:{skill}]] 差距，预计提高 {gain} 分。{course}。",
        "no_closing_course": "目录中暂时没有能完全弥补此差距的课程",
        "hello": "你好，我是 Adi！我可以解释你的匹配职位、下一步该学什么、技能趋势、课程费用与 HRD Corp "
        "补贴，以及你的路径如何关联联合国可持续发展目标。",
        "no_profile": "先告诉我你的技能：在 [[page:/app/onboarding]] 只需两分钟。之后我就能为你排序未来职位并显示差距。",
        "visitor_next": "试试首页的免费简历预览，或 [[page:/auth/signup]] 查看匹配职位、技能差距和学习计划。",
        "top": "你最匹配的职位是 [[role:{role}]]，估计匹配度 {score}。",
        "others": "其次：{roles}。",
        "gap": "要缩小差距，请重点学习 {skills}。",
        "no_gap": "你已具备该职位所需技能，学习计划可以帮你进一步提升。",
        "why": "这只是估计，不是保证。",
        "plan": "你为 [[role:{role}]] 保存的计划从 [[skill:{skill}]] 开始，课程是 [[course:{course}]]。在 [[page:/app/progress]] 跟踪进度。",
        "no_plan": "在 [[page:/app/pathway]] 选择职位并保存计划，我会一步步带你完成。",
        "trend": "在最新快照中，这些技能正在上升：{skills}。趋势是估计值；详见 [[page:/app/radar]]。",
        "my_trend": "你的技能：{skills}。",
        "cost": "每门课程均标明学时、带日期的价格及 HRD Corp 申报资格。符合资格不代表已获资助：购买前请确认凭证费用、税费及雇主批准。浏览 [[page:/app/courses]]。",
        "plan_progress": "你为 [[role:{role}]] 保存的计划中，已记录完成 {share} 的学习时数、{courses} 门课程，以及 {total} 项技能差距中的 {closed} 项。完成课程不代表已满足全部职位技能。详见 [[page:/app/progress]]。",
        "plan_duration": "你为 [[role:{role}]] 保存的计划预计需要 {weeks} 周，每周 {weekly} 小时，总计 {hours} 学习小时。这是学习时间估计，不是完成日期保证。详见 [[page:/app/pathway]]。",
        "plan_cost": "你为 [[role:{role}]] 保存的计划记录的预计标价为 RM {listed}，依照保存的资助假设，学员费用为 RM {learner}。购买前请确认凭证费用、税费、最新价格及雇主批准。详见 [[page:/app/pathway]]。",
        "progress_unavailable": "暂时无法加载已保存计划的进度，请重试或查看 [[page:/app/progress]]；我不会假设进度为零。",
        "totals_unavailable": "暂时无法加载已保存计划的总额，请重试或查看 [[page:/app/pathway]]；我不会估计缺失的数据。",
        "sdg": "每个职位和技能都关联联合国 SDG 具体目标并附理由。{badges} 详见 [[page:/app/sdg]]。",
        "privacy": "你的简历文件只在内存中读取，不会保存；提取的技能由你确认后才保存。启用 AI 服务时，经清理的聊天文本和候选答案可能由 RunPod 或 Google Gemini 处理，可选的技能匹配会把去除联系方式的简短技能短语发送给 Gemini，而不是简历文件。你可以在“我的技能”下载或删除数据。详情：[[page:/privacy]]；所用 AI 模型：[[page:/about]]。",
        "how": "Adept 带你从今天的技能走向未来职位：技能档案 → 未来技能雷达 → 匹配职位与差距 → 关联联合国 SDG 的学习计划。每个估计都注明来源和日期。[[page:/about]]",
        "team": "你的团队：{members} 名成员，其中 {complete} 名已完成档案。{gap}",
        "team_gap": " 平均差距最大的是 [[role:{role}]]（{gap}）。",
        "team_plan": " 团队计划目标为 [[role:{role}]]：详见 [[page:/org/plan]]。",
        "team_none": "在 [[page:/org/members]] 分享加入码，让成员添加他们的技能。",
        "plan_done": "你已完成为 [[role:{role}]] 保存的计划中的全部课程。{gaps} 可在 [[page:/app/pathway/compare]] 比较其他职位，或在 [[page:/app/progress]] 查看技能。",
        "plan_done_gaps": "仍有 {open} 项所需技能需要实践，或目录中尚无对应课程。",
        "plan_done_closed": "列出的技能差距均已补齐。",
        "work_pending": "在 {org}，面向 [[role:{role}]] 的项目“{title}”正在等待你的答复。请在 [[page:/work/plan]] 查看学习协议：接受，或申请调整。",
        "work_active": "在 {org}，你的项目“{title}”将在 {date} 前帮助你迈向 [[role:{role}]]，每周 {hours} 小时带薪学习时间，雇主最多承担 RM {budget}。已记录完成 {share} 的课程学时。",
        "work_next": " 下一步：[[course:{course}]]。在 [[page:/work/progress]] 跟踪。",
        "work_done": " 所有课程均已记录完成；HR 会在 [[page:/work/progress]] 审核凭证。",
        "work_none": "{org} 尚未向你发送项目。收到后，你可以在 [[page:/work/plan]] 查看协议。你的个人计划保留在个人工作区。",
        "work_roles": "职业探索属于个人隐私，位于个人工作区：切换到“个人”即可查看匹配职位。在 {org} 中我只解答其项目相关问题。",
        "privacy_work": "{org} 可以看到你的项目进度、你在此提交或分享的凭证{skills}。你的个人计划、匹配结果以及与我的对话均保持私密。可在 [[page:/work/skills]] 更改分享设置。",
        "privacy_shared": "，以及你选择分享的技能水平",
        "privacy_not_shared": "；你没有分享技能水平",
        "programmes": " 项目：已发送 {count} 个；{accepted} 人接受，{pending} 人待定，{changes} 人申请调整，{declined} 人拒绝。详见 [[page:/org/programmes]]。",
        "programmes_none": " 尚未发送项目：可在 [[page:/org/programmes/new]] 从业务目标开始。",
        "team_shared": " 其中 {shared} 人分享了技能水平。",
    },
}

# Follow-up chips. Each chip is an ordinary question that routes to the intent named in
# `CHIP_INTENTS` (checked by the tests), so tapping one always gets its grounded answer.
CHIPS: dict[str, dict[str, str]] = {
    "en": {
        "next": "What should I do next?",
        "raise": "What would raise my score?",
        "faster": "What if AI moves faster?",
        "sources": "Where does this data come from?",
        "declining": "Which skills are declining?",
        "rising": "Which skills are rising?",
        "accuracy": "How accurate are your forecasts?",
        "why_top": "Why is my top role a match?",
        "plan_cost": "How much will my plan cost?",
        "hrd": "Which courses are HRD Corp claimable?",
        "employer_see": "What does my employer see?",
        "programme": "How far along is my programme?",
        "team_gap": "Where is my team's biggest gap?",
        "programmes": "How are our programmes going?",
        "how": "How does Adept work?",
        "cv_stored": "Is my CV stored?",
    },
    "ms": {
        "next": "Apa langkah seterusnya?",
        "raise": "Bagaimana nak tingkatkan skor saya?",
        "faster": "Apa jadi kalau AI bergerak lebih laju?",
        "sources": "Dari mana data ini datang?",
        "declining": "Kemahiran apa yang semakin menurun?",
        "rising": "Kemahiran apa yang meningkat?",
        "accuracy": "Sejauh mana ketepatan ramalan anda?",
        "why_top": "Kenapa peranan teratas sesuai?",
        "plan_cost": "Berapa kos pelan saya?",
        "hrd": "Kursus mana boleh tuntut HRD Corp?",
        "employer_see": "Apa yang majikan nampak?",
        "programme": "Bagaimana kemajuan program saya?",
        "team_gap": "Di mana jurang terbesar pasukan?",
        "programmes": "Bagaimana program kami?",
        "how": "Bagaimana Adept berfungsi?",
        "cv_stored": "Adakah CV saya disimpan?",
    },
    "zh": {
        "next": "我下一步该做什么？",
        "raise": "如何提高匹配分数？",
        "faster": "如果AI发展更快会怎样？",
        "sources": "数据来源是什么？",
        "declining": "哪些技能在下降？",
        "rising": "哪些技能在上升？",
        "accuracy": "你们的预测有多准确？",
        "why_top": "为什么这个职位最匹配？",
        "plan_cost": "我的计划费用是多少？",
        "hrd": "哪些课程可用 HRD Corp 报销？",
        "employer_see": "雇主能看到什么？",
        "programme": "我的项目进度如何？",
        "team_gap": "团队最大的差距在哪里？",
        "programmes": "我们的项目进展如何？",
        "how": "Adept 如何运作？",
        "cv_stored": "我的简历会被保存吗？",
    },
}
# The answer block each chip asks for (for the audience it is offered to).
CHIP_INTENTS: dict[str, str] = {
    "next": "next",
    "raise": "score_improvement",
    "faster": "scenario",
    "sources": "sources",
    "declining": "trend_declining",
    "rising": "trend",
    "accuracy": "forecast_accuracy",
    "why_top": "roles",
    "plan_cost": "plan_cost",
    "hrd": "cost",
    "employer_see": "privacy",
    "team_gap": "team",
    "how": "how",
    "cv_stored": "privacy",
}
# Opening chips per audience: the questions people most often ask first.
_CHIP_DEFAULTS: dict[str, tuple[str, ...]] = {
    "visitor": ("how", "cv_stored", "rising"),
    "learner": ("raise", "faster", "sources"),
    "employee": ("next", "employer_see", "programme"),
    "manager": ("team_gap", "programmes", "sources"),
}
# Learner follow-ups after an answer of a given kind (managers: `_MANAGER_FOLLOW_UPS`);
# employees and visitors, and kinds not listed, get the audience defaults.
_CHIP_FOLLOW_UPS: dict[str, tuple[str, ...]] = {
    "roles": ("raise", "faster", "sources"),
    "score_breakdown": ("raise", "faster", "sources"),
    "match_detail": ("raise", "faster", "sources"),
    "score_improvement": ("next", "faster", "sources"),
    "trend": ("declining", "faster", "sources"),
    "trend_declining": ("rising", "faster", "sources"),
    "scenario": ("raise", "declining", "sources"),
    "sources": ("accuracy", "declining", "faster"),
    "forecast_accuracy": ("sources", "faster", "declining"),
    "next": ("why_top", "raise", "sources"),
    "learn": ("plan_cost", "raise", "sources"),
    "plan_progress": ("next", "plan_cost", "raise"),
    "plan_duration": ("plan_cost", "next", "raise"),
    "plan_cost": ("hrd", "next", "raise"),
    "cost": ("plan_cost", "next", "sources"),
    "privacy": ("next", "sources", "how"),
    "profile": ("cv_stored", "how", "next"),
}
_MANAGER_FOLLOW_UPS: dict[str, tuple[str, ...]] = {
    "trend": ("declining", "sources", "team_gap"),
    "trend_declining": ("rising", "sources", "team_gap"),
    "sources": ("accuracy", "declining", "team_gap"),
}


def intent(question: str, audience: str = "learner") -> str:
    """The single best answer block for a question (see `intents` for near ties)."""
    return intents(question, audience)[0]


def intents(question: str, audience: str = "learner") -> list[str]:
    """One answer-block ID, or two when the runner-up intent is nearly as strong.

    Safety intents come first and always stand alone. Then every intent is scored: a phrase or
    pattern hit counts twice a single-word hit, a typo-tolerant hit counts 0.6, and grounded fact
    intents (sources, scenarios, saved-plan figures, ...) weigh three times a general topic.
    """
    q = question.lower()
    # People decisions take precedence even when combined with other topics.
    if _decision_request(question, audience):
        return ["decision"]
    if find_injection(q) or any(_contains(q, word) for word in INTENTS["injection"]):
        return ["injection"]
    possessive = _POSSESSIVE.search(q)
    if any(_contains(q, word) for word in INTENTS["other_person"]) or (
        possessive and possessive.group(1) not in _NOT_PEOPLE
    ):
        return ["other_person"]
    scores: dict[str, float] = {}
    for name, words in INTENTS.items():
        if name in SAFETY_INTENTS:
            continue
        if name in PERSONAL_PLAN_INTENTS and audience not in ("learner", "employee"):
            continue
        if name == "team" and audience != "manager":
            continue
        patterns = sum(2 for pattern in PATTERNS.get(name, ()) if pattern.search(q))
        # Saved-plan totals answer only questions about the plan itself: "Which courses can I
        # finish in two hours?" is course advice, not "how long is my plan?".
        if (
            name in ("plan_cost", "plan_duration")
            and not any(_contains(q, word) for word in PLAN_WORDS)
            and not (patterns and name in PLAN_PATTERN_INTENTS)
        ):
            continue
        hits: float = patterns + sum(_strength(word) for word in words if _contains(q, word))
        if not hits:
            hits = 0.6 * any(_keyword_hit(q, word) for word in words)
        weight = 3.0 if name in FACT_INTENTS else 0.15 if name in {"how", "next"} else 1.0
        scores[name] = hits * weight
    specific = {
        name: value for name, value in scores.items() if name not in {"how", "next"} and value >= 1
    }
    if not specific:
        return [max(scores, key=lambda name: scores[name]) if any(scores.values()) else "next"]
    ranked = sorted(specific, key=lambda name: -specific[name])  # stable: ties keep table order
    if len(ranked) > 1 and specific[ranked[1]] >= NEAR_TIE * specific[ranked[0]]:
        return ranked[:2]
    return ranked[:1]


def _strength(word: str) -> int:
    """A phrase (or a Chinese phrase of three or more characters) is a strong hit."""
    if re.search(r"[一-鿿]", word):
        return 2 if len(word) >= 3 else 1
    return 2 if " " in word else 1


def _decision_request(question: str, audience: str) -> bool:
    """A request to hire, fire, promote, admit or reject a person (EN/BM/ZH)."""
    text = _mark_people(question).lower()
    for token in set(re.findall(r"[a-z]+", text)):
        verb = next((v for v in _DECISION_TYPOS if token != v and _typo(token, v)), None)
        if verb:
            text = re.sub(rf"\b{token}\b", verb, text)
    if any(p.search(text) for p in (*_DECISION_EN, *_DECISION_MS, *_DECISION_ZH)):
        return True
    return (
        audience == "manager"
        and _MANAGER_DECISION.search(text) is not None
        and _MANAGER_PERSON.search(text) is not None
    )


def _mark_people(question: str) -> str:
    """Replace capitalised mid-sentence names ("Ali", "Sarah") with a person marker."""

    def mark(match: re.Match[str]) -> str:
        before = question[: match.start()].rstrip()
        if not before or before[-1] in ".?!" or match.group(0).lower() in _NOT_NAMES:
            return match.group(0)
        return "__person__"

    return re.sub(r"(?<![A-Za-z])[A-Z][a-z]+(?![A-Za-z])", mark, question)


def reply_locale(question: str, locale: Locale) -> Locale:
    """Answer in the question's language when it is clearly Chinese or Malay."""
    if len(re.findall(r"[一-鿿]", question)) >= 2:
        return "zh"
    words = re.findall(r"[a-z]+", question.lower())
    malay = sum(word in _MALAY_CUES for word in words)
    english = sum(word in _ENGLISH_CUES for word in words)
    if malay >= 2 and malay > english:
        return "ms"
    return locale


def _keyword_hit(question: str, word: str) -> bool:
    """Exact or typo-tolerant match of every token of a keyword, in order."""
    if _contains(question, word):
        return True
    if re.search(r"[一-鿿]", word):
        return False
    tokens = re.findall(r"[a-z]+", question)
    parts = word.split()
    for start in range(len(tokens) - len(parts) + 1):
        if all(
            left == right or _typo(right, left)
            for left, right in zip(parts, tokens[start : start + len(parts)], strict=True)
        ):
            return True
    return False


def _typo(token: str, word: str) -> bool:
    """Whether `token` misspells `word`: same first letter, both at least four letters, and at
    most one edit (two for words of eight letters or more), an adjacent swap counting as one.
    Ordinary inflections ("source"/"sources", "promoted"/"promote") are different words."""
    if min(len(token), len(word)) < 4 or token[0] != word[0] or token in _inflections(word):
        return False
    limit = 2 if len(word) >= 8 else 1
    if abs(len(token) - len(word)) > limit:
        return False
    return _edit_distance(token, word) <= limit


def _inflections(word: str) -> set[str]:
    if word.endswith("s"):  # "sources" -> "source"; "sourcess" stays a typo
        return {word[:-1], word + "es"}
    stem = word[:-1] if word.endswith("e") else word
    return {word + "s", word + "es", word + "d", word + "ed", stem + "ing", stem + "ion"}


def _edit_distance(a: str, b: str) -> int:
    """Optimal string alignment distance (Levenshtein plus adjacent transpositions)."""
    previous2: list[int] = []
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, start=1):
        current = [i] + [0] * len(b)
        for j, right in enumerate(b, start=1):
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (left != right))
            if i > 1 and j > 1 and left == b[j - 2] and a[i - 2] == right:
                current[j] = min(current[j], previous2[j - 2] + 1)
        previous2, previous = previous, current
    return previous[-1]


def focus_context(question: str, ctx: Context) -> Context:
    """Resolve ordinal roles and catalogue targets without changing the stored context."""
    facts = dict(ctx.facts)
    ordinals = (("second", "2nd", "kedua", "第二"), ("third", "3rd", "ketiga", "第三"))
    matches = facts.get("matches") or []
    for index, words in enumerate(ordinals, start=1):
        if any(_contains(question.lower(), word) for word in words):
            facts["focus_rank"] = index + 1
            facts["focus_match"] = matches[index] if len(matches) > index else None
            break
    target = re.search(r"\bsdg\s*(\d{1,2}\.[a-z0-9]+)", question.lower())
    if target:
        facts["sdg_focus"] = target.group(1)
    facts["sdg_plan_question"] = any(_contains(question.lower(), word) for word in PLAN_WORDS)
    return replace(ctx, facts=facts)


def _contains(question: str, word: str) -> bool:
    if re.search(r"[一-鿿]", word):
        return word in question
    return re.search(rf"\b{re.escape(word)}\b", question) is not None


def _pct(v: float) -> str:
    return f"{round(v * 100)}%"


def _tags(kind: str, ids: list[str]) -> str:
    return ", ".join(f"[[{kind}:{i}]]" for i in ids)


def reply(question: str, ctx: Context, locale: Locale) -> str:
    return reply_for_intent(intent(question, ctx.audience), focus_context(question, ctx), locale)


def _score_math(match: dict[str, Any], t: dict[str, str]) -> str:
    """The weighted fit-score arithmetic: weight × component = points, per named component."""
    from app.features.matching.scoring import Weights

    weights = Weights()
    components = match.get("components") or [
        {"name": name, "value": match["parts"].get(name, 0), "weight": weight}
        for name, weight in (
            ("skill_overlap", weights.skill),
            ("trend_outlook", weights.trend),
            ("interest_fit", weights.interest),
        )
    ]
    arithmetic = " + ".join(
        f"{t.get(c.get('name', ''), c.get('name', ''))} "
        f"{c['weight'] * 100:g}% × {c['value'] * 100:.1f}% = {c['weight'] * c['value'] * 100:.1f}"
        + ("" if c.get("provided", True) else t["neutral"])
        for c in components
    )
    return t["score_math"].format(
        role=match["role_id"], parts=arithmetic, total=f"{match['score'] * 100:.1f}"
    )


def reply_for_intent(kind: str, ctx: Context, locale: Locale) -> str:
    """Render one server-authored answer from checked application facts."""
    t = T[locale]
    f = ctx.facts
    if kind in SAFETY_INTENTS or kind in {
        "action_not_supported",
        "no_data",
        "forecast_accuracy",
        "profile",
    }:
        return t[kind]
    if kind == "sources":
        if ctx.meta is None:
            return t["sources_unavailable"]
        sources = "; ".join(
            f"{source.name} ({source.url}; {source.retrieved_at})" for source in ctx.meta.sources
        )
        courses = list(
            dict.fromkeys(course for step in f.get("plan_steps", []) for course in step["courses"])
        )[:3]
        fallback = ctx.meta.is_fallback or ctx.meta.served_from == "fixture"
        return (t["sources_fallback"] if fallback else "").format(date=ctx.meta.snapshot_date) + t[
            kind
        ].format(
            date=ctx.meta.snapshot_date, sources=sources, courses=_tags("course", courses) or "—"
        )
    if kind == "scenario":
        comparison = f.get("scenario_comparison")
        if comparison is None:
            return t["scenario_unavailable"]
        rows = "; ".join(
            f"[[role:{item['role_id']}]]: {item['before'] * 100:.1f} → {item['after'] * 100:.1f} ({item['rank_before']} → {item['rank_after']})"
            for item in comparison["roles"]
        )
        return t[kind].format(
            before=t[f"pace_{comparison['before']}"],
            after=t[f"pace_{comparison['after']}"],
            rows=rows,
        )
    if kind == "sdg_explain":
        focus = f.get("sdg_focus")
        if focus and focus not in ctx.refs.sdg:
            return t["sdg_unavailable"]
        targets = (
            [focus]
            if focus
            else f.get("plan_sdg_targets") or f.get("sdg_targets") or list(ctx.refs.sdg)[:2]
        )
        if not targets:
            return t["sdg_unavailable"]
        prefix = t["no_plan"] + " " if f.get("sdg_plan_question") and not f.get("plan_role") else ""
        return prefix + t[kind].format(targets=_tags("sdg", targets[:4]))
    if kind == "trend_declining":
        return t[kind].format(
            skills=_tags("skill", f.get("declining", [])[:5]) or "—",
            roles=_tags("role", f.get("declining_roles", [])[:5]) or "—",
        )
    if (
        kind in ("score_improvement", "score_breakdown", "match_detail")
        and ctx.audience == "learner"
    ):
        matches = f.get("matches") or []
        if not matches:
            return t["no_profile"]
        if kind == "match_detail" and f.get("focus_rank") and not f.get("focus_match"):
            return t["rank_unavailable"]
        top = f.get("focus_match") or matches[0]
        body = _score_math(top, t)
        if kind == "match_detail":
            body += " " + t["rank_context"].format(
                rank=f.get("focus_rank", 1),
                role=matches[0]["role_id"],
                score=f"{matches[0]['score'] * 100:.1f}",
            )
        if kind == "score_improvement":
            for item in top.get("improvements", [])[:3]:
                course = (
                    f"[[course:{item['course_id']}]]"
                    if item.get("course_id")
                    else t["no_closing_course"]
                )
                body += "\n" + t["improvement"].format(
                    skill=item["skill"], gain=f"{item['score_gain'] * 100:.1f}", course=course
                )
        return body
    if ctx.audience == "employee":
        return _employee_reply(kind, ctx, t)
    if kind == "privacy":
        return t["privacy"]
    if kind == "how":
        return t["how"]
    if kind == "trend":
        out = t["trend"].format(skills=_tags("skill", f.get("rising", [])[:5]) or "—")
        mine = f.get("my_trends") or {}
        if mine:
            out += " " + t["my_trend"].format(
                skills=", ".join(f"[[skill:{s}]] {d}" for s, d in list(mine.items())[:6])
            )
        return out
    if kind == "cost":
        return t["cost"]
    if kind in PERSONAL_PLAN_INTENTS and ctx.audience == "learner":
        if not f.get("plan_role"):
            return t["no_plan"]
        if kind == "plan_progress":
            progress = f.get("plan_progress")
            if progress is None:
                return t["progress_unavailable"]
            return t[kind].format(
                role=f["plan_role"],
                share=_pct(progress["share"]),
                courses=progress["courses"],
                closed=progress["gap_closed"],
                total=progress["gap_total"],
            )
        totals = f.get("plan_totals")
        if totals is None:
            return t["totals_unavailable"]
        if kind == "plan_duration":
            return t[kind].format(
                role=f["plan_role"],
                weeks=totals["weeks"],
                weekly=f"{totals['hours_per_week']:g}",
                hours=f"{totals['hours']:g}",
            )
        return t[kind].format(
            role=f["plan_role"],
            listed=f"{totals['list_price_myr']:,.2f}",
            learner=f"{totals['out_of_pocket_myr']:,.2f}",
        )
    if ctx.audience == "manager" or kind == "team":
        if "members" not in f:
            return t["team_none"]
        total, complete = f["members"]
        gap = ""
        if f.get("role_gaps"):
            role, value = f["role_gaps"][0]
            gap = t["team_gap"].format(role=role, gap=_pct(value))
        if "members_shared" in f:
            gap = t["team_shared"].format(shared=f["members_shared"]) + gap
        programmes = f.get("programmes")
        if programmes:
            gap += t["programmes"].format(
                count=len(programmes),
                accepted=sum(p["accepted"] for p in programmes),
                pending=sum(p["pending"] for p in programmes),
                changes=sum(p["changes"] for p in programmes),
                declined=sum(p["declined"] for p in programmes),
            )
        elif programmes is not None:
            gap += t["programmes_none"]
        return t["team"].format(members=total, complete=complete, gap=gap)
    if ctx.audience == "visitor":
        return (
            (t["how"] + "\n\n" + t["visitor_next"])
            if kind == "next"
            else t["hello"] + "\n\n" + t["visitor_next"]
        )
    if not f.get("has_profile"):
        return t["no_profile"]
    matches = f.get("matches") or []
    if kind == "sdg":
        targets = f.get("sdg_targets") or []
        badges = " " + _tags("sdg", targets[:4]) if targets else ""
        return t["sdg"].format(badges=badges)
    if kind == "learn" or kind == "next":
        steps = f.get("plan_steps") or []
        done = set(f.get("done") or [])
        for step in steps:
            todo = [c for c in step["courses"] if c not in done]
            if todo:
                return t["plan"].format(role=f["plan_role"], skill=step["skill"], course=todo[0])
        if steps and f.get("plan_role"):
            open_gaps = f.get("plan_gaps", 0)
            if f.get("plan_progress"):
                progress = f["plan_progress"]
                open_gaps = progress["gap_total"] - progress["gap_closed"]
            gaps = (
                t["plan_done_gaps"].format(open=open_gaps) if open_gaps else t["plan_done_closed"]
            )
            return t["plan_done"].format(role=f["plan_role"], gaps=gaps)
        if matches:
            top = matches[0]
            missing = top["missing"] + top["partial"]
            body = t["top"].format(role=top["role_id"], score=_pct(top["score"]))
            body += " " + (
                t["gap"].format(skills=_tags("skill", missing[:4])) if missing else t["no_gap"]
            )
            return body + "\n\n" + t["no_plan"]
        return t["no_plan"]
    if matches:  # roles / why / default
        top = matches[0]
        body = t["top"].format(role=top["role_id"], score=_pct(top["score"]))
        # The same weighted arithmetic as the score-breakdown answer, in every language.
        body += " " + _score_math(top, t) + " " + t["why"]
        if len(matches) > 1:
            body += "\n\n" + t["others"].format(
                roles=_tags("role", [m["role_id"] for m in matches[1:3]])
            )
        missing = top["missing"] + top["partial"]
        if missing:
            body += " " + t["gap"].format(skills=_tags("skill", missing[:3]))
        return body
    return t["hello"]


def _employee_reply(kind: str, ctx: Context, t: dict[str, str]) -> str:
    """Organisation workspace: the member's own programmes only, named with the organisation."""
    f = ctx.facts
    org = ctx.org_name or "your organisation"
    if kind == "privacy":
        skills = t["privacy_shared"] if f.get("skills_shared") else t["privacy_not_shared"]
        return t["privacy_work"].format(org=org, skills=skills)
    if kind == "how":
        return t["how"]
    if kind == "trend":
        return t["trend"].format(skills=_tags("skill", f.get("rising", [])[:5]) or "—")
    if kind == "sdg":
        return t["sdg"].format(badges="")
    if kind == "roles":
        return t["work_roles"].format(org=org)
    pending = f.get("work_pending") or []
    if pending and kind in ("next", "learn"):
        first = pending[0]
        return t["work_pending"].format(org=org, title=first["title"], role=first["role"])
    work = f.get("work_active")
    if work is None:
        if pending:
            first = pending[0]
            return t["work_pending"].format(org=org, title=first["title"], role=first["role"])
        return t["work_none"].format(org=org)
    out = t["work_active"].format(
        org=org,
        title=work["title"],
        role=work["role"],
        date=work["date"],
        hours=f"{work['hours']:g}",
        budget=f"{work['budget']:,.0f}",
        share=_pct(work["share"]) if "share" in work else "—",
    )
    done = set(work.get("done") or [])
    todo = [c for c in work["courses"] if c not in done]
    out += t["work_next"].format(course=todo[0]) if todo else t["work_done"]
    if kind == "cost":
        out += "\n\n" + t["cost"]
    return out


def suggestions(ctx: Context, page: str, locale: Locale, kind: str | None = None) -> list[str]:
    """Three follow-up chips for the audience, chosen for the answer just given."""
    keys = _CHIP_DEFAULTS[ctx.audience]
    if kind and ctx.audience == "learner":
        keys = _CHIP_FOLLOW_UPS.get(kind, keys)
    elif kind and ctx.audience == "manager":
        keys = _MANAGER_FOLLOW_UPS.get(kind, keys)
    return [CHIPS[locale][key] for key in keys]
