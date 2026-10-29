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
    "trend_declining": (
        "declining",
        "losing demand",
        "kurang diperlukan",
        "menurun",
        "消失",
        "下降",
    ),
    "score_improvement": (
        "improve my match",
        "raise my score",
        "improve my score",
        "tingkatkan skor",
        "提高匹配分数",
    ),
    "score_breakdown": ("why is my score", "why did i get this score", "kenapa skor"),
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
PLAN_WORDS = ("plan", "plans", "pelan", "rancangan", "计划")

T: dict[str, dict[str, str]] = {
    "en": {
        "trend_declining": "Declining skills in this snapshot: {skills}. Declining roles: {roles}. These are estimates from research attention and labour projections, not a prediction that a job will disappear. See [[page:/app/radar]].",
        "score_math": "Estimated fit for [[role:{role}]]: {parts}. Total = {total} points out of 100. Weights are skill overlap, trend outlook and interest fit, in that order.",
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
        "why": "The fit score adds three parts: skill overlap ({skill}), trend outlook ({trend}) "
        "and interest fit ({interest}). It is an estimate, not a guarantee.",
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
        "trend_declining": "Kemahiran yang menurun dalam petikan ini: {skills}. Peranan yang menurun: {roles}. Ini anggaran berdasarkan perhatian penyelidikan dan unjuran tenaga kerja, bukan ramalan bahawa kerja akan hilang. Lihat [[page:/app/radar]].",
        "score_math": "Anggaran padanan untuk [[role:{role}]]: {parts}. Jumlah = {total} mata daripada 100. Wajaran mengikut susunan pertindihan kemahiran, prospek trend dan kesesuaian minat.",
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
        "why": "Skor kesesuaian terdiri daripada tiga bahagian: pertindihan kemahiran ({skill}), "
        "tinjauan tren ({trend}) dan minat ({interest}). Ia anggaran, bukan jaminan.",
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
        "trend_declining": "此快照中需求下降的技能：{skills}。需求下降的职位：{roles}。这些是基于研究关注度和劳动力预测的估计，并不表示某个工作一定会消失。请查看 [[page:/app/radar]]。",
        "score_math": "[[role:{role}]] 的估计匹配度：{parts}。总计 = {total} 分，满分 100。权重依次对应技能重合、趋势前景和兴趣契合。",
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
        "why": "匹配度由三部分组成：技能重合（{skill}）、趋势前景（{trend}）和兴趣契合（{interest}）。这只是估计，不是保证。",
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
        "privacy": "你的简历只在内存中读取，不会保存。你可以在“我的技能”下载或删除全部数据。详见 [[page:/about]]。",
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

SUGGESTIONS: dict[str, dict[str, list[str]]] = {
    "en": {
        "visitor": ["How does Adept work?", "Is my CV stored?", "Which skills are rising?"],
        "learner": [
            "What should I do next?",
            "Why is my top role a match?",
            "Which courses are HRD Corp claimable?",
        ],
        "employee": [
            "What should I do next?",
            "What does my employer see?",
            "How far along is my programme?",
        ],
        "manager": [
            "Where is my team's biggest gap?",
            "How are our programmes going?",
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
        "employee": [
            "Apa langkah seterusnya?",
            "Apa yang majikan nampak?",
            "Bagaimana kemajuan program saya?",
        ],
        "manager": [
            "Di mana jurang terbesar pasukan?",
            "Bagaimana program kami?",
            "Kemahiran apa yang meningkat?",
        ],
    },
    "zh": {
        "visitor": ["Adept 如何运作？", "我的简历会被保存吗？", "哪些技能在上升？"],
        "learner": ["我下一步该做什么？", "为什么这个职位最匹配？", "哪些课程可用 HRD Corp 报销？"],
        "employee": ["我下一步该做什么？", "雇主能看到什么？", "我的项目进度如何？"],
        "manager": ["团队最大的差距在哪里？", "我们的项目进展如何？", "哪些技能在上升？"],
    },
}


def intent(question: str, audience: str = "learner") -> str:
    q = question.lower()
    for name, words in INTENTS.items():
        if name in PERSONAL_PLAN_INTENTS and audience not in ("learner", "employee"):
            continue
        # Saved-plan totals answer only questions about the plan itself: "Which courses can I
        # finish in two hours?" is course advice, not "how long is my plan?".
        if name in ("plan_cost", "plan_duration") and not any(
            _contains(q, word) for word in PLAN_WORDS
        ):
            continue
        if name == "team" and audience != "manager":
            continue
        if any(_contains(q, word) for word in words):
            return name
    return "next"


def _contains(question: str, word: str) -> bool:
    if re.search(r"[一-鿿]", word):
        return word in question
    return re.search(rf"\b{re.escape(word)}\b", question) is not None


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
    if kind == "trend_declining":
        return t[kind].format(
            skills=_tags("skill", f.get("declining", [])[:5]) or "—",
            roles=_tags("role", f.get("declining_roles", [])[:5]) or "—",
        )
    if kind in ("score_improvement", "score_breakdown") and ctx.audience == "learner":
        matches = f.get("matches") or []
        if not matches:
            return t["no_profile"]
        top = matches[0]
        from app.features.matching.scoring import Weights

        weights = Weights()
        components = top.get("components") or [
            {"value": top["parts"].get(name, 0), "weight": weight}
            for name, weight in (
                ("skill_overlap", weights.skill),
                ("trend_outlook", weights.trend),
                ("interest_fit", weights.interest),
            )
        ]
        arithmetic = " + ".join(
            f"{c['weight'] * 100:g}% × {c['value'] * 100:.1f}% = {c['weight'] * c['value'] * 100:.1f}"
            for c in components
        )
        body = t["score_math"].format(
            role=top["role_id"], parts=arithmetic, total=f"{top['score'] * 100:.1f}"
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


def suggestions(ctx: Context, page: str, locale: Locale) -> list[str]:
    return list(SUGGESTIONS[locale][ctx.audience])
