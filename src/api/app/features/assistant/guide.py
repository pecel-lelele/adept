# ruff: noqa: E501  (EN/BM/ZH answer templates read best as one line each)
"""Adi's deterministic guide: answers common questions from the same facts the model sees.

Used when no language model is configured or it fails, so Adi always works and never invents.
Replies use the same [[kind:id]] tags, resolved to official labels by the service.
"""

from __future__ import annotations

import re

from app.contracts.assistant import Locale
from app.features.assistant.context import Context

# Keywords per intent in English, Malay and Chinese (lower-case; Chinese matched as substrings).
INTENTS: dict[str, tuple[str, ...]] = {
    "privacy": (
        "privacy",
        "stored",
        "store my",
        "my data",
        "personal data",
        "pdpa",
        "delete",
        "privasi",
        "simpan",
        "padam",
        "隐私",
        "保存",
        "删除",
        "个人数据",
    ),
    "how": (
        "how does",
        "how do",
        "what is adept",
        "how it works",
        "method",
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
        "hrd",
        "claim",
        "budget",
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
        "gap",
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
        "course",
        "skill",
        "plan",
        "study",
        "gap",
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
        "role",
        "job",
        "match",
        "career",
        "fit",
        "score",
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

T: dict[str, dict[str, str]] = {
    "en": {
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
        "why": "The fit score adds three parts: skill overlap ({skill}), trend outlook ({trend}) "
        "and interest fit ({interest}). It is an estimate, not a guarantee.",
        "plan": "Your saved plan for [[role:{role}]] starts with [[skill:{skill}]] through "
        "[[course:{course}]]. Track it on [[page:/app/progress]].",
        "no_plan": "Pick a role and save a plan on [[page:/app/pathway]]; I'll then walk you "
        "through it step by step.",
        "trend": "In the latest snapshot these skills are rising: {skills}. Trends are estimates "
        "from research attention and labour projections; see [[page:/app/radar]].",
        "my_trend": "Your own skills: {skills}.",
        "cost": "Every course shows hours, list price and whether HRD Corp may cover it; with HRD "
        "Corp eligibility a claimable course costs you RM 0, subject to your employer's claim. "
        "Browse [[page:/app/courses]].",
        "sdg": "Each role and skill links to UN SDG targets with a cited reason.{badges} See "
        "[[page:/app/sdg]].",
        "privacy": "Your CV is read in memory and never stored. You can download or delete all "
        "your data from My skills (or team Settings). See [[page:/about]] for sources and the AI "
        "model in use.",
        "how": "Adept takes you from today's skills to future roles: skill profile → Future "
        "Skills Radar → matched roles with a skills gap → an ordered learning plan linked to the "
        "UN SDGs. Every estimate shows its source and date. [[page:/about]]",
        "team": "Your team: {members} members, {complete} with a complete profile.{gap}",
        "team_gap": " The largest average gap is for [[role:{role}]] ({gap}).",
        "team_plan": " The team plan targets [[role:{role}]]: see [[page:/org/plan]].",
        "team_none": "Share your join code from [[page:/org/members]] so your people can add "
        "their skills; then I can show the gaps.",
    },
    "ms": {
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
        "why": "Skor kesesuaian terdiri daripada tiga bahagian: pertindihan kemahiran ({skill}), "
        "tinjauan tren ({trend}) dan minat ({interest}). Ia anggaran, bukan jaminan.",
        "plan": "Pelan anda untuk [[role:{role}]] bermula dengan [[skill:{skill}]] melalui "
        "[[course:{course}]]. Jejak di [[page:/app/progress]].",
        "no_plan": "Pilih peranan dan simpan pelan di [[page:/app/pathway]]; saya akan bimbing "
        "anda langkah demi langkah.",
        "trend": "Dalam petikan terkini, kemahiran ini meningkat: {skills}. Tren ialah anggaran; "
        "lihat [[page:/app/radar]].",
        "my_trend": "Kemahiran anda: {skills}.",
        "cost": "Setiap kursus menunjukkan jam, harga dan sama ada HRD Corp boleh menanggungnya; "
        "jika layak, kursus boleh tuntut tidak dikenakan kos kepada anda, tertakluk kepada "
        "tuntutan majikan. Lihat [[page:/app/courses]].",
        "sdg": "Setiap peranan dan kemahiran dikaitkan dengan sasaran SDG PBB beserta "
        "sebabnya.{badges} Lihat [[page:/app/sdg]].",
        "privacy": "CV anda dibaca dalam memori dan tidak disimpan. Anda boleh muat turun atau "
        "padam semua data anda di Kemahiran saya. Lihat [[page:/about]].",
        "how": "Adept membawa anda dari kemahiran hari ini ke peranan masa depan: profil → Radar "
        "Kemahiran Masa Depan → peranan padanan → pelan pembelajaran yang dikaitkan dengan SDG "
        "PBB. Setiap anggaran ada sumber dan tarikh. [[page:/about]]",
        "team": "Pasukan anda: {members} ahli, {complete} dengan profil lengkap.{gap}",
        "team_gap": " Jurang purata terbesar ialah untuk [[role:{role}]] ({gap}).",
        "team_plan": " Pelan pasukan menyasarkan [[role:{role}]]: lihat [[page:/org/plan]].",
        "team_none": "Kongsi kod sertai dari [[page:/org/members]] supaya pasukan anda boleh "
        "menambah kemahiran mereka.",
    },
    "zh": {
        "hello": "你好，我是 Adi！我可以解释你的匹配职位、下一步该学什么、技能趋势、课程费用与 HRD Corp "
        "补贴，以及你的路径如何关联联合国可持续发展目标。",
        "no_profile": "先告诉我你的技能：在 [[page:/app/onboarding]] 只需两分钟。之后我就能为你排序未来职位并显示差距。",
        "visitor_next": "试试首页的免费简历预览，或 [[page:/auth/signup]] 查看匹配职位、技能差距和学习计划。",
        "top": "你最匹配的职位是 [[role:{role}]]，估计匹配度 {score}。",
        "others": "其次：{roles}。",
        "gap": "要缩小差距，请重点学习 {skills}。",
        "no_gap": "你已具备该职位所需技能，学习计划可以帮你进一步提升。",
        "why": "匹配度由三部分组成：技能重合（{skill}）、趋势前景（{trend}）和兴趣契合（{interest}）。这只是估计，不是保证。",
        "plan": "你为 [[role:{role}]] 保存的计划从 [[skill:{skill}]] 开始，课程是 [[course:{course}]]。在 [[page:/app/progress]] 跟踪进度。",
        "no_plan": "在 [[page:/app/pathway]] 选择职位并保存计划，我会一步步带你完成。",
        "trend": "在最新快照中，这些技能正在上升：{skills}。趋势是估计值；详见 [[page:/app/radar]]。",
        "my_trend": "你的技能：{skills}。",
        "cost": "每门课程都显示学时、价格以及 HRD Corp 是否可报销；若符合资格，可报销课程对你免费（以雇主申请为准）。浏览 [[page:/app/courses]]。",
        "sdg": "每个职位和技能都关联联合国 SDG 具体目标并附理由。{badges} 详见 [[page:/app/sdg]]。",
        "privacy": "你的简历只在内存中读取，不会保存。你可以在“我的技能”下载或删除全部数据。详见 [[page:/about]]。",
        "how": "Adept 带你从今天的技能走向未来职位：技能档案 → 未来技能雷达 → 匹配职位与差距 → 关联联合国 SDG 的学习计划。每个估计都注明来源和日期。[[page:/about]]",
        "team": "你的团队：{members} 名成员，其中 {complete} 名已完成档案。{gap}",
        "team_gap": " 平均差距最大的是 [[role:{role}]]（{gap}）。",
        "team_plan": " 团队计划目标为 [[role:{role}]]：详见 [[page:/org/plan]]。",
        "team_none": "在 [[page:/org/members]] 分享加入码，让成员添加他们的技能。",
    },
}

SUGGESTIONS: dict[str, dict[str, list[str]]] = {
    "en": {
        "visitor": ["How does Adept work?", "Is my CV stored?", "Which skills are rising?"],
        "learner": [
            "What should I do next?",
            "Why is my top role a match?",
            "Which courses are HRD Corp claimable?",
        ],
        "manager": [
            "Where is my team's biggest gap?",
            "What is our team plan?",
            "Which skills are rising?",
        ],
    },
    "ms": {
        "visitor": [
            "Bagaimana Adept berfungsi?",
            "Adakah CV saya disimpan?",
            "Kemahiran apa yang meningkat?",
        ],
        "learner": [
            "Apa langkah seterusnya?",
            "Kenapa peranan teratas sesuai?",
            "Kursus mana boleh tuntut HRD Corp?",
        ],
        "manager": [
            "Di mana jurang terbesar pasukan?",
            "Apa pelan pasukan kami?",
            "Kemahiran apa yang meningkat?",
        ],
    },
    "zh": {
        "visitor": ["Adept 如何运作？", "我的简历会被保存吗？", "哪些技能在上升？"],
        "learner": ["我下一步该做什么？", "为什么这个职位最匹配？", "哪些课程可用 HRD Corp 报销？"],
        "manager": ["团队最大的差距在哪里？", "我们的团队计划是什么？", "哪些技能在上升？"],
    },
}


def intent(question: str, audience: str = "learner") -> str:
    q = question.lower()
    for name, words in INTENTS.items():
        if name == "team" and audience != "manager":
            continue
        if any(
            (w in q) if re.search(r"[一-鿿]", w) else re.search(rf"\b{re.escape(w)}\b", q)
            for w in words
        ):
            return name
    return "next"


def _pct(v: float) -> str:
    return f"{round(v * 100)}%"


def _tags(kind: str, ids: list[str]) -> str:
    return ", ".join(f"[[{kind}:{i}]]" for i in ids)


def reply(question: str, ctx: Context, locale: Locale) -> str:
    return reply_for_intent(intent(question, ctx.audience), ctx, locale)


def reply_for_intent(kind: str, ctx: Context, locale: Locale) -> str:
    """Render one server-authored answer from checked application facts."""
    t = T[locale]
    f = ctx.facts
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
    if ctx.audience == "manager" or kind == "team":
        if "members" not in f:
            return t["team_none"]
        total, complete = f["members"]
        gap = ""
        if f.get("role_gaps"):
            role, value = f["role_gaps"][0]
            gap = t["team_gap"].format(role=role, gap=_pct(value))
        if f.get("team_plan_role"):
            gap += t["team_plan"].format(role=f["team_plan_role"])
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
        parts = top["parts"]
        body = t["top"].format(role=top["role_id"], score=_pct(top["score"]))
        body += " " + t["why"].format(
            skill=_pct(parts.get("skill_overlap", 0)),
            trend=_pct(parts.get("trend_outlook", 0)),
            interest=_pct(parts.get("interest_fit", 0)),
        )
        if len(matches) > 1:
            body += "\n\n" + t["others"].format(
                roles=_tags("role", [m["role_id"] for m in matches[1:3]])
            )
        missing = top["missing"] + top["partial"]
        if missing:
            body += " " + t["gap"].format(skills=_tags("skill", missing[:3]))
        return body
    return t["hello"]


def suggestions(ctx: Context, page: str, locale: Locale) -> list[str]:
    return list(SUGGESTIONS[locale][ctx.audience])
