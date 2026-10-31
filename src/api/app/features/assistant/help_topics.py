# ruff: noqa: E501  (EN/BM/ZH answer templates read best as one line each)
"""Server-authored help blocks: how to use Adept and where each page is.

Every block here is a fixed, reviewed answer with links to the right page. Nothing in them is
generated or computed: they carry no scores, prices or catalogue facts, so they need no
attribution. Routing is deterministic (keywords, phrase patterns, then a typo-tolerant
vocabulary match) and a configured model may only choose among the block IDs
(`select_ids_or_fallback` / `validate_ids`), never write the answer.

Audience variants: ``learner`` is the default; ``employee`` (organisation member) and
``manager`` override it where the page or the steps differ.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Locale = Literal["en", "ms", "zh"]
LOCALES: tuple[Locale, ...] = ("en", "ms", "zh")

# Questions about storing or sharing a CV are privacy questions, not "where do I upload".
_PRIVACY_NEG = (
    r"(?!.*(?:\b(?:stor\w+|delet\w+|privacy|private|share\w*|employer|safe|secure|keep|simpan|disimpan|"
    r"padam|privasi|kongsi|majikan)\b|保存|删除|隐私|雇主|分享|安全))"
)


def _all(*groups: str, neg: str = "") -> re.Pattern[str]:
    """A phrase pattern that needs every group somewhere in the question, in any order."""
    return re.compile("(?s)" + neg + "".join(f"(?=.*(?:{g}))" for g in groups))


@dataclass(frozen=True)
class Topic:
    id: str
    words: tuple[str, ...]
    patterns: tuple[re.Pattern[str], ...]
    vocab: frozenset[str]
    en: str
    ms: str
    zh: str
    employee: dict[str, str] = field(default_factory=dict)
    manager: dict[str, str] = field(default_factory=dict)


# "Where is X" style cues: asking for a place, not for an explanation of the content.
_ASK = (
    r"\b(?:where|find|open|locate|navigate|access|go\s+to|get\s+to|mana|cari|buka)\b|"
    r"哪里|哪儿|在哪|打开|找"
)

TOPICS: tuple[Topic, ...] = (
    Topic(
        id="help_cv_upload",
        words=(
            "upload cv",
            "upload my cv",
            "upload a cv",
            "upload resume",
            "upload my resume",
            "cv upload",
            "resume upload",
            "add my cv",
            "add my resume",
            "attach cv",
            "attach resume",
            "import cv",
            "import resume",
            "submit cv",
            "submit resume",
            "muat naik cv",
            "muat naik resume",
            "上传简历",
            "添加简历",
            "提交简历",
        ),
        patterns=(
            _all(
                r"\b(?:cvs?|resumes?|résumés?|curriculum\s+vitae)\b",
                r"\b(?:upload\w*|attach\w*|import\w*|submit\w*|add\w*|send\w*|where|how|put|drop|scan\w*|read\w*|"
                r"pars\w+|provide|load\w*|file|pdf|docx|word|insert\w*|paste|extract\w*|need\w*|require\w*|must|"
                r"without|no|supported|format\w*)\b",
                neg=_PRIVACY_NEG,
            ),
            _all(
                r"\b(?:cv|resume|resumé)\b",
                r"\bmuat\s+naik\b|\b(?:letak|hantar|tambah|mana|bagaimana|cara|nak|mahu|upload)\b",
                neg=_PRIVACY_NEG,
            ),
            _all(r"简历", r"上传|添加|提交|导入|哪里|哪儿|在哪|怎么|如何|传|放", neg=_PRIVACY_NEG),
            _all(
                r"\b(?:upload\w*|attach\w*)\b",
                r"\b(?:file|document|pdf|docx|word)\b",
                neg=_PRIVACY_NEG,
            ),
        ),
        vocab=frozenset({"cv", "resume", "upload", "pdf", "docx", "attach"}),
        en="Open [[page:/app/onboarding]] and choose “Upload CV (PDF, Word or text)”, under 5 MB. Adept reads the file in memory and never stores it, and you confirm every skill before it is saved. No CV? Pick your skills by hand on the same page, and edit them any time on [[page:/app/profile]].",
        ms="Buka [[page:/app/onboarding]] dan pilih “Muat naik CV (PDF, Word atau teks)”, bawah 5 MB. Adept membaca fail dalam memori dan tidak menyimpannya, dan anda mengesahkan setiap kemahiran sebelum disimpan. Tiada CV? Pilih kemahiran sendiri di halaman yang sama, dan ubahnya bila-bila masa di [[page:/app/profile]].",
        zh="打开 [[page:/app/onboarding]]，选择“上传简历（PDF、Word 或文本）”，文件需小于 5 MB。Adept 只在内存中读取文件，不会保存，并且每项技能都由你确认后才会保存。没有简历？可在同一页面手动选择技能，之后随时在 [[page:/app/profile]] 修改。",
        employee={
            "en": "Your CV upload is in your personal workspace: use the workspace switcher in the menu, then open the skill intake. Adept reads the file in memory and never stores it, and you confirm every skill. In your organisation workspace, [[page:/work/skills]] shows only what you choose to share.",
            "ms": "Muat naik CV ada dalam ruang kerja peribadi anda: guna penukar ruang kerja di menu, kemudian buka pengambilan kemahiran. Adept membaca fail dalam memori dan tidak menyimpannya, dan anda mengesahkan setiap kemahiran. Dalam ruang kerja organisasi, [[page:/work/skills]] hanya menunjukkan apa yang anda pilih untuk dikongsi.",
            "zh": "上传简历在你的个人工作区：用菜单中的工作区切换器切换，然后打开技能录入。Adept 只在内存中读取文件，不会保存，每项技能都由你确认。在组织工作区中，[[page:/work/skills]] 只显示你选择分享的内容。",
        },
        manager={
            "en": "Team members add their own skills: share your join code from [[page:/org/members]], and each person uploads a CV (PDF, Word or text) or picks skills by hand. CVs are read in memory and never stored.",
            "ms": "Ahli pasukan menambah kemahiran sendiri: kongsi kod sertai anda dari [[page:/org/members]], dan setiap orang memuat naik CV (PDF, Word atau teks) atau memilih kemahiran sendiri. CV dibaca dalam memori dan tidak disimpan.",
            "zh": "团队成员自行添加技能：从 [[page:/org/members]] 分享加入码，每个人上传简历（PDF、Word 或文本）或手动选择技能。简历只在内存中读取，不会保存。",
        },
    ),
    Topic(
        id="help_target_role",
        words=(
            "target role",
            "choose a role",
            "choose role",
            "choose this role",
            "pick a role",
            "select a role",
            "set my role",
            "change my role",
            "change role",
            "switch role",
            "change my target",
            "save a role",
            "career goal",
            "peranan sasaran",
            "tukar peranan",
            "pilih peranan",
            "目标职位",
            "目标角色",
            "选择职位",
            "更换职位",
            "换职位",
        ),
        patterns=(
            re.compile(
                r"\b(?:choos\w+|chose\w*|pick\w*|select\w*|set\w*|chang\w+|switch\w*|sav\w+|swap\w*|decid\w+|"
                r"updat\w+|edit\w*|replac\w+)\s+(?:a\s+|an\s+|my\s+|the\s+|this\s+|that\s+|another\s+|new\s+|"
                r"different\s+|other\s+)*(?:target\s+|goal\s+|dream\s+)?(?:role|job|position|career)\b"
            ),
            re.compile(r"\b(?:target|goal|dream|chosen)\s+(?:role|job|position|career)\b"),
            re.compile(r"\b(?:role|job|career)\s+(?:goal|target)\b"),
            re.compile(r"(?:选择|选|更换|换|设置|设定|修改).{0,4}(?:目标)?(?:职位|角色|岗位)"),
            re.compile(r"\b(?:pilih|tukar|ubah|tetapkan)\s+(?:peranan|jawatan|kerja)"),
        ),
        vocab=frozenset({"target", "role", "choose", "pick", "goal"}),
        en="Open [[page:/app/matches]], compare your matched roles, and press “Choose this role” on the one you want. It then shows as “Your target role” at the top of that page, and your plan on [[page:/app/pathway]] and your progress follow it. To change it, choose a different role the same way.",
        ms="Buka [[page:/app/matches]], bandingkan peranan padanan anda, dan tekan “Pilih peranan ini” pada yang anda mahu. Ia kemudian muncul sebagai “Peranan sasaran anda” di bahagian atas halaman itu, dan pelan anda di [[page:/app/pathway]] serta kemajuan anda mengikutinya. Untuk menukar, pilih peranan lain dengan cara yang sama.",
        zh="打开 [[page:/app/matches]]，比较你的匹配职位，在想要的职位上点击“选择此职位”。它会显示在该页面顶部的“你的目标职位”，你在 [[page:/app/pathway]] 的计划和进度也会随之更新。想更换时，用同样的方式选择另一个职位即可。",
        employee={
            "en": "Your employer's programme names its own target role. If you would rather work toward a different catalogue role, you can propose one from [[page:/work/plan]]; your manager reviews it.",
            "ms": "Program majikan anda menetapkan peranan sasarannya sendiri. Jika anda mahu peranan katalog lain, anda boleh mencadangkannya dari [[page:/work/plan]]; pengurus anda akan menyemaknya.",
            "zh": "雇主的项目有自己的目标职位。如果你想朝另一个目录中的职位发展，可以在 [[page:/work/plan]] 提出，由你的经理审核。",
        },
        manager={
            "en": "When you create a programme on [[page:/org/programmes/new]] you choose the target role and the cohort, then compare course plans for each member. Members can propose a different role for you to review.",
            "ms": "Apabila anda mencipta program di [[page:/org/programmes/new]], anda memilih peranan sasaran dan kohort, kemudian membandingkan pelan kursus bagi setiap ahli. Ahli boleh mencadangkan peranan lain untuk anda semak.",
            "zh": "在 [[page:/org/programmes/new]] 创建项目时，你选择目标职位和成员群组，然后比较每位成员的课程方案。成员也可以提出其他职位供你审核。",
        },
    ),
    Topic(
        id="help_matches",
        words=(
            "matches page",
            "match page",
            "match card",
            "match cards",
            "what does fit mean",
            "percentage mean",
            "compare roles",
            "lihat padanan",
            "匹配页面",
            "匹配卡片",
        ),
        patterns=(
            _all(
                _ASK,
                r"\b(?:matches|matched\s+roles|role\s+matches|roles\s+page|match\s+page|my\s+roles|future\s+roles|padanan)\b",
            ),
            _all(
                r"\b(?:percent\w*|%|score)\b",
                r"\b(?:mean|means|show|shows|represent\w*|stand\w*)\b",
                r"\b(?:card|cards|role|match|matches)\b",
            ),
            _all(
                r"\bwhat\s+(?:is|are|does)\b",
                r"\b(?:match\s+card|fit\s+percent\w*|skills\s+to\s+build)\b",
            ),
            re.compile(
                r"(?:匹配|职位).{0,6}(?:在哪|哪里)|(?:哪里|在哪).{0,6}(?:看|查看).{0,4}(?:匹配|职位)"
            ),
        ),
        vocab=frozenset({"matches", "matched", "percentage", "card", "cards"}),
        en="[[page:/app/matches]] ranks roles by an estimated fit for your skills and interests at the AI pace you pick (Moderate or Fast). Each card shows the fit percentage, the skills you could build, and a short tip on what would raise the score. Choose a role to make it your target. Scores are estimates, not guarantees.",
        ms="[[page:/app/matches]] menyusun peranan mengikut anggaran kesesuaian dengan kemahiran dan minat anda pada kadar AI yang dipilih (Sederhana atau Pantas). Setiap kad menunjukkan peratus kesesuaian, kemahiran yang boleh dibina dan petua ringkas untuk menaikkan skor. Pilih satu peranan sebagai sasaran. Skor ialah anggaran, bukan jaminan.",
        zh="[[page:/app/matches]] 按你选择的 AI 速度（适中或较快），根据技能和兴趣的估计匹配度对职位排序。每张卡片显示匹配百分比、可培养的技能，以及提高分数的简短建议。选择一个职位作为目标。分数只是估计，不是保证。",
        employee={
            "en": "Your matched roles are in your personal workspace; use the workspace switcher in the menu. Your organisation workspace shows your employer's programme on [[page:/work/plan]].",
            "ms": "Peranan padanan anda ada dalam ruang kerja peribadi; guna penukar ruang kerja di menu. Ruang kerja organisasi menunjukkan program majikan anda di [[page:/work/plan]].",
            "zh": "你的匹配职位在个人工作区，请用菜单中的工作区切换器切换。组织工作区在 [[page:/work/plan]] 显示雇主的项目。",
        },
        manager={
            "en": "For a team, [[page:/org/gaps]] shows which skills your sharing members are missing for a target role. Individual role matching is in each person's own workspace.",
            "ms": "Untuk pasukan, [[page:/org/gaps]] menunjukkan kemahiran yang kurang pada ahli yang berkongsi bagi peranan sasaran. Padanan peranan individu ada dalam ruang kerja setiap orang.",
            "zh": "对团队而言，[[page:/org/gaps]] 显示愿意分享的成员在目标职位上缺少哪些技能。个人职位匹配在每个人自己的工作区。",
        },
    ),
    Topic(
        id="help_plan",
        words=(
            "learning plan",
            "study plan",
            "reskilling plan",
            "create a plan",
            "make a plan",
            "build a plan",
            "save a plan",
            "generate a plan",
            "pathway page",
            "learning pathway",
            "pelan pembelajaran",
            "buat pelan",
            "学习计划",
            "制定计划",
            "学习路径",
        ),
        patterns=(
            _all(
                _ASK + r"|\b(?:creat\w+|make|build|sav\w+|start|generat\w+|reset)\b",
                r"\b(?:learning\s+plan|study\s+plan|reskilling\s+plan|my\s+plan|a\s+plan|the\s+plan|pathway|roadmap)\b",
                neg=r"(?!.*\b(?:how\s+(?:long|much|many|far)|cost\w*|price\w*|hours?|weeks?|finish\w*|complete\w*|progress|done|afford\w*)\b)",
            ),
            re.compile(
                r"(?:怎么|如何|哪里|在哪).{0,6}(?:制定|创建|生成|保存|找).{0,3}(?:学习计划|计划)"
            ),
            re.compile(
                r"\b(?:macam\s+mana|bagaimana|cara)\s+(?:nak\s+)?(?:buat|cipta|simpan)\b.{0,20}\bpelan\b"
            ),
        ),
        vocab=frozenset({"pathway", "roadmap"}),
        en="Choose a target role on [[page:/app/matches]] first, then open [[page:/app/pathway]]. Adept orders the skills to build and picks verified catalogue courses for each, with hours and dated prices. Save the plan to follow it on [[page:/app/progress]]. Prices are estimates, so check the provider before you buy.",
        ms="Pilih peranan sasaran di [[page:/app/matches]] dahulu, kemudian buka [[page:/app/pathway]]. Adept menyusun kemahiran untuk dibina dan memilih kursus katalog yang disahkan bagi setiap satu, dengan jam dan harga bertarikh. Simpan pelan untuk mengikutinya di [[page:/app/progress]]. Harga ialah anggaran, jadi semak penyedia sebelum membeli.",
        zh="先在 [[page:/app/matches]] 选择目标职位，再打开 [[page:/app/pathway]]。Adept 会排列要培养的技能，并为每项技能挑选目录中已核实的课程，附学时和带日期的价格。保存计划后可在 [[page:/app/progress]] 跟进。价格仅为估计，购买前请向提供方确认。",
        employee={
            "en": "Your employer's programme plan is on [[page:/work/plan]]: review the learning agreement, accept it or ask for a change. Track it on [[page:/work/progress]].",
            "ms": "Pelan program majikan anda ada di [[page:/work/plan]]: semak perjanjian pembelajaran, terima atau minta perubahan. Jejaki di [[page:/work/progress]].",
            "zh": "雇主的项目计划在 [[page:/work/plan]]：查看学习协议，接受或申请更改。在 [[page:/work/progress]] 跟进进度。",
        },
        manager={
            "en": "Build a full programme on [[page:/org/programmes/new]], or get a quick team plan on [[page:/org/plan]]: one ordered plan toward the target role, naming the members who need each step.",
            "ms": "Bina program penuh di [[page:/org/programmes/new]], atau dapatkan pelan pasukan pantas di [[page:/org/plan]]: satu pelan tersusun ke arah peranan sasaran, dengan nama ahli yang memerlukan setiap langkah.",
            "zh": "在 [[page:/org/programmes/new]] 建立完整项目，或在 [[page:/org/plan]] 生成快速团队计划：一份朝目标职位的有序计划，并列出每一步需要的成员。",
        },
    ),
    Topic(
        id="help_progress",
        words=(
            "mark done",
            "mark as done",
            "mark a course",
            "add evidence",
            "upload evidence",
            "upload certificate",
            "add certificate",
            "my badges",
            "track my progress",
            "tandakan selesai",
            "bukti",
            "sijil",
            "标记完成",
            "上传证书",
            "徽章",
        ),
        patterns=(
            _all(
                r"\b(?:mark\w*|record\w*|log|tick|report|submit)\b",
                r"\b(?:course|courses|step|steps|done|complete\w*|finished)\b",
            ),
            _all(
                r"\b(?:upload\w*|add\w*|attach\w*|submit\w*)\b",
                r"\b(?:evidence|proof|certificates?|certificate|badge|badges)\b",
            ),
            _all(_ASK, r"\b(?:progress\s+page|my\s+badges|badges?)\b"),
            re.compile(
                r"(?:怎么|如何|哪里).{0,6}(?:标记|记录).{0,4}(?:完成|课程)|(?:上传|添加).{0,4}(?:证书|证明)"
            ),
        ),
        vocab=frozenset({"evidence", "badge", "badges", "certificate"}),
        en="On [[page:/app/progress]] you can mark a course as done and add evidence such as a certificate. Your progress, badges and remaining skill gaps update there. Finishing a course does not guarantee every role skill. In an employer programme, HR reviews the evidence.",
        ms="Di [[page:/app/progress]] anda boleh menandakan kursus sebagai selesai dan menambah bukti seperti sijil. Kemajuan, lencana dan jurang kemahiran yang tinggal dikemas kini di situ. Menamatkan kursus tidak menjamin setiap kemahiran peranan. Dalam program majikan, HR menyemak bukti.",
        zh="在 [[page:/app/progress]] 可以把课程标记为完成，并添加证书等证明。你的进度、徽章和剩余技能差距会在那里更新。完成课程并不保证掌握职位所需的每项技能。在雇主项目中，由 HR 审核证明。",
        employee={
            "en": "Record each finished course and its evidence on [[page:/work/progress]]. It counts toward programme progress straight away as self-reported; HR then reviews the evidence. Approval gives you earned skill credit, and a rejected completion stops counting.",
            "ms": "Rekod setiap kursus yang selesai beserta buktinya di [[page:/work/progress]]. Ia terus dikira dalam kemajuan program sebagai lapor sendiri; HR kemudian menyemak bukti. Kelulusan memberi anda kredit kemahiran, dan penyelesaian yang ditolak tidak lagi dikira.",
            "zh": "在 [[page:/work/progress]] 记录每门完成的课程及其证明。它会先以自我报告的形式立即计入项目进度，之后由 HR 审核证明。获批后你才能获得技能认证；被拒绝的完成将不再计入。",
        },
        manager={
            "en": "Review members' completions and evidence on [[page:/org/verify]]. Self-reported completions count toward progress and team course totals until you reject them; approving one gives the member earned skill credit. Treat unreviewed totals as self-reported. The decision stays with you.",
            "ms": "Semak penyelesaian dan bukti ahli di [[page:/org/verify]]. Penyelesaian lapor sendiri dikira dalam kemajuan dan jumlah kursus pasukan sehingga anda menolaknya; meluluskannya memberi ahli kredit kemahiran. Anggap jumlah yang belum disemak sebagai lapor sendiri. Keputusan kekal pada anda.",
            "zh": "在 [[page:/org/verify]] 审核成员的完成情况和证明。自我报告的完成会计入进度和团队课程总数，直到你拒绝为止；批准后成员才获得技能认证。未审核的总数应视为自我报告。决定权在你。",
        },
    ),
    Topic(
        id="help_jobs",
        words=(
            "job openings",
            "job board",
            "jobs page",
            "find jobs",
            "job listings",
            "apply for jobs",
            "career roadmap",
            "certifications",
            "jawatan kosong",
            "papan kerja",
            "职位空缺",
            "招聘信息",
            "证书认证",
        ),
        patterns=(
            _all(
                _ASK,
                r"\b(?:openings?|job\s+board|job\s+listings?|vacanc\w+|jobs\s+page|job\s+postings?)\b",
            ),
            _all(
                r"\b(?:find|look\s+for|search\w*|browse|see)\b",
                r"\b(?:jobs?|openings?|vacanc\w+)\b",
            ),
            re.compile(r"\b(?:career\s+roadmap|certifications?)\b"),
            re.compile(r"(?:哪里|怎么|如何).{0,6}(?:找|看).{0,3}(?:工作|职位)"),
        ),
        vocab=frozenset({"openings", "vacancies", "roadmap", "certifications"}),
        en="[[page:/app/jobs]] lists openings for your matched roles with a link to each employer's own page, plus certifications and a career roadmap. A match is an estimated skill fit, not proof that an employer is hiring or will hire you, so apply on the employer's page.",
        ms="[[page:/app/jobs]] menyenaraikan jawatan kosong untuk peranan padanan anda dengan pautan ke laman majikan, serta pensijilan dan peta jalan kerjaya. Padanan ialah anggaran kesesuaian kemahiran, bukan bukti majikan sedang mengambil pekerja, jadi mohon di laman majikan.",
        zh="[[page:/app/jobs]] 列出与你匹配职位相关的空缺，并附雇主官方页面链接，还有认证和职业路线图。匹配只是对技能契合度的估计，不代表雇主正在招聘或会录用你，请在雇主页面申请。",
        employee={
            "en": "Job openings are in your personal workspace: use the workspace switcher in the menu. They link to each employer's own page; I can't apply for you.",
            "ms": "Jawatan kosong ada dalam ruang kerja peribadi anda: guna penukar ruang kerja di menu. Ia memaut ke laman setiap majikan; saya tidak boleh memohon bagi pihak anda.",
            "zh": "职位空缺在你的个人工作区：请用菜单中的工作区切换器。它们链接到各雇主自己的页面；我无法替你申请。",
        },
        manager={
            "en": "Job openings are shown to each person in their own workspace, linking to employers' own pages. For your team's skills, see [[page:/org/gaps]].",
            "ms": "Jawatan kosong ditunjukkan kepada setiap orang dalam ruang kerja masing-masing, dengan pautan ke laman majikan. Untuk kemahiran pasukan, lihat [[page:/org/gaps]].",
            "zh": "职位空缺显示在每个人自己的工作区，并链接到雇主页面。团队技能请看 [[page:/org/gaps]]。",
        },
    ),
    Topic(
        id="help_courses",
        words=(
            "course catalogue",
            "course catalog",
            "browse courses",
            "find courses",
            "courses page",
            "katalog kursus",
            "cari kursus",
            "课程目录",
            "浏览课程",
        ),
        patterns=(
            _all(
                _ASK,
                r"\b(?:course\s+catalogue|course\s+catalog|courses\s+page|catalogue|catalog)\b",
            ),
            _all(r"\b(?:find|browse|search\w*|look\s+for)\b", r"\bcourses?\b"),
            re.compile(r"(?:哪里|怎么|如何).{0,6}(?:找|看|浏览).{0,3}课程"),
        ),
        vocab=frozenset({"catalogue", "catalog", "browse"}),
        en="[[page:/app/courses]] is the course catalogue: each course shows its provider, hours, a dated price and whether HRD Corp claims may apply. Open a course to go to the provider's site and enrol there; I can't enrol you from chat.",
        ms="[[page:/app/courses]] ialah katalog kursus: setiap kursus menunjukkan penyedia, jam, harga bertarikh dan sama ada tuntutan HRD Corp mungkin terpakai. Buka kursus untuk ke laman penyedia dan mendaftar di sana; saya tidak boleh mendaftarkan anda dari sembang.",
        zh="[[page:/app/courses]] 是课程目录：每门课程显示提供方、学时、带日期的价格，以及是否可能适用 HRD Corp 报销。打开课程即可前往提供方网站并在那里报名；我无法在聊天中替你报名。",
        employee={
            "en": "Your programme's courses are listed on [[page:/work/plan]]. Each links to the provider's own site, where you enrol; I can't enrol you from chat.",
            "ms": "Kursus program anda disenaraikan di [[page:/work/plan]]. Setiap satu memaut ke laman penyedia, tempat anda mendaftar; saya tidak boleh mendaftarkan anda dari sembang.",
            "zh": "项目中的课程列在 [[page:/work/plan]]。每门课程链接到提供方网站，你在那里报名；我无法在聊天中替你报名。",
        },
        manager={
            "en": "[[page:/org/courses]] is the course catalogue for your team: provider, hours, dated prices and whether HRD Corp claims may apply.",
            "ms": "[[page:/org/courses]] ialah katalog kursus untuk pasukan anda: penyedia, jam, harga bertarikh dan sama ada tuntutan HRD Corp mungkin terpakai.",
            "zh": "[[page:/org/courses]] 是团队的课程目录：提供方、学时、带日期的价格，以及是否可能适用 HRD Corp 报销。",
        },
    ),
    Topic(
        id="help_impact",
        words=(
            "impact page",
            "impact and evidence",
            "impact & evidence",
            "evidence page",
            "sdg links",
            "mycol",
            "critical occupation",
            "halaman kesan",
            "影响页面",
            "影响与证据",
        ),
        patterns=(
            _all(
                _ASK + r"|\b(?:see|view|show)\b",
                r"\b(?:impact|evidence|sdg\s+links?|sdg\s+page|sdg\s+impact|kesan|bukti)\b",
            ),
            re.compile(r"\b(?:di\s+mana|mana)\b.{0,25}\b(?:kesan|bukti)\b"),
            re.compile(r"\b(?:mycol|critical\s+occupations?|masco)\b"),
            re.compile(
                r"(?:影响|证据).{0,3}(?:页面|页)|(?:怎么|如何|哪里|在哪).{0,6}(?:看|查看).{0,4}(?:影响|证据|sdg)"
            ),
        ),
        vocab=frozenset({"impact", "evidence", "mycol", "masco"}),
        en="[[page:/app/sdg]] (Impact and evidence) shows how your chosen role and planned learning hours link to UN SDG targets, with the reason for each link, plus the sources and data edition behind it. Links are hoped-for contributions, not measured UN progress.",
        ms="[[page:/app/sdg]] (Kesan dan bukti) menunjukkan bagaimana peranan pilihan dan jam pembelajaran anda dipautkan kepada sasaran SDG PBB, dengan sebab bagi setiap pautan, serta sumber dan edisi data di sebaliknya. Pautan ialah sumbangan yang diharapkan, bukan kemajuan PBB yang diukur.",
        zh="[[page:/app/sdg]]（影响与证据）展示你选择的职位和计划学时如何关联到联合国 SDG 目标，附每条关联的理由，以及背后的来源和数据版本。这些关联是预期贡献，并非已衡量的联合国进展。",
        employee={
            "en": "Your programme's progress and hours are on [[page:/work/progress]]. The SDG links and sources are on the Impact and evidence page in your personal workspace.",
            "ms": "Kemajuan dan jam program anda ada di [[page:/work/progress]]. Pautan SDG dan sumber ada di halaman Kesan dan bukti dalam ruang kerja peribadi anda.",
            "zh": "项目的进度和学时在 [[page:/work/progress]]。SDG 关联和来源在你个人工作区的“影响与证据”页面。",
        },
        manager={
            "en": "[[page:/org/sdg]] shows how your team's planned learning links to UN SDG targets, with the reason for each link and its sources. Links are hoped-for contributions, not measured UN progress.",
            "ms": "[[page:/org/sdg]] menunjukkan bagaimana pembelajaran terancang pasukan anda dipautkan kepada sasaran SDG PBB, dengan sebab bagi setiap pautan dan sumbernya. Pautan ialah sumbangan yang diharapkan, bukan kemajuan PBB yang diukur.",
            "zh": "[[page:/org/sdg]] 展示团队的计划学习如何关联到联合国 SDG 目标，附每条关联的理由及来源。这些关联是预期贡献，并非已衡量的联合国进展。",
        },
    ),
    Topic(
        id="help_about",
        words=(
            "data and ai use",
            "ai use",
            "which ai",
            "what ai",
            "which model",
            "what model",
            "ai disclosure",
            "about page",
            "how adept works",
            "data sources page",
            "penggunaan ai",
            "model ai",
            "数据与ai",
            "ai 使用",
            "使用的模型",
        ),
        patterns=(
            _all(
                r"\b(?:which|what)\b",
                r"\b(?:ai|llm|model|models|provider)\b",
                r"\b(?:use|uses|used|using|power\w*|run\w*)\b",
            ),
            _all(
                _ASK,
                r"\b(?:about\s+page|data\s+and\s+ai|ai\s+disclosure|methodology|how\s+adept\s+works)\b",
            ),
            re.compile(r"(?:用|使用).{0,6}(?:什么|哪个|哪些).{0,4}(?:模型|ai)"),
            re.compile(r"\bmodel\s+ai\s+(?:apa|mana)\b"),
        ),
        vocab=frozenset({"methodology", "disclosure"}),
        en="[[page:/about]] (Data and AI use) lists the data sources, the AI models used and what each is used for, and the guardrails: Adept never invents jobs or courses and never makes hiring decisions. [[page:/privacy]] explains how your data is handled.",
        ms="[[page:/about]] (Data dan penggunaan AI) menyenaraikan sumber data, model AI yang digunakan dan tujuannya, serta pagar pelindung: Adept tidak mereka-reka pekerjaan atau kursus dan tidak membuat keputusan pengambilan pekerja. [[page:/privacy]] menerangkan cara data anda dikendalikan.",
        zh="[[page:/about]]（数据与 AI 使用）列出数据来源、所用 AI 模型及其用途，以及保障措施：Adept 从不编造职位或课程，也从不做招聘决定。[[page:/privacy]] 说明你的数据如何处理。",
    ),
    Topic(
        id="help_org",
        words=(
            "organisation mode",
            "organization mode",
            "org mode",
            "organisation workspace",
            "organization workspace",
            "team workspace",
            "hr dashboard",
            "manager dashboard",
            "create organisation",
            "create organization",
            "set up my organisation",
            "set up my organization",
            "create a programme",
            "create a program",
            "mod organisasi",
            "组织模式",
            "团队空间",
        ),
        patterns=(
            _all(
                r"\b(?:org|organi[sz]ation)\b",
                r"\b(?:mode|workspace|dashboard|setup|set\s+up|create|manage)\b",
            ),
            re.compile(r"\b(?:hr|manager|l&d)\s+(?:dashboard|mode|view)\b"),
            _all(
                r"\b(?:creat\w+|start|set\s+up|build|run)\b",
                r"\b(?:programmes?|programs?|cohort)\b",
            ),
            re.compile(r"组织(?:模式|空间)|团队(?:空间|仪表)|(?:创建|建立).{0,3}(?:项目|组织)"),
        ),
        vocab=frozenset({"organisation", "organization", "programme", "programmes", "cohort"}),
        en="Organisation mode is for HR, L&D and careers advisers. A manager creates an organisation, shares a join code, then sees team skill gaps, builds programmes and reviews completions. Members only share what they consent to. If your employer gave you a code, join on [[page:/app/join]].",
        ms="Mod organisasi untuk HR, L&D dan penasihat kerjaya. Pengurus mencipta organisasi, berkongsi kod sertai, kemudian melihat jurang kemahiran pasukan, membina program dan menyemak penyelesaian. Ahli hanya berkongsi apa yang mereka setujui. Jika majikan memberi kod, sertai di [[page:/app/join]].",
        zh="组织模式面向 HR、L&D 和职业顾问。经理创建组织、分享加入码，然后查看团队技能差距、建立项目并审核完成情况。成员只分享自己同意分享的内容。如果雇主给了你加入码，请在 [[page:/app/join]] 加入。",
        employee={
            "en": "You are in an organisation workspace. Your employer's programme is on [[page:/work/plan]] and your progress on [[page:/work/progress]]; you choose what you share on [[page:/work/skills]]. Your personal workspace stays separate and private.",
            "ms": "Anda berada dalam ruang kerja organisasi. Program majikan ada di [[page:/work/plan]] dan kemajuan anda di [[page:/work/progress]]; anda memilih apa yang dikongsi di [[page:/work/skills]]. Ruang kerja peribadi anda kekal berasingan dan peribadi.",
            "zh": "你当前在组织工作区。雇主的项目在 [[page:/work/plan]]，进度在 [[page:/work/progress]]；你在 [[page:/work/skills]] 选择分享的内容。个人工作区保持独立且私密。",
        },
        manager={
            "en": "Your team space: members on [[page:/org/members]], skill gaps on [[page:/org/gaps]], programmes on [[page:/org/programmes]] (new ones on [[page:/org/programmes/new]]), completions to review on [[page:/org/verify]], and organisation settings on [[page:/org/setup]]. Adept informs your decisions; people make them.",
            "ms": "Ruang pasukan anda: ahli di [[page:/org/members]], jurang kemahiran di [[page:/org/gaps]], program di [[page:/org/programmes]] (yang baharu di [[page:/org/programmes/new]]), penyelesaian untuk disemak di [[page:/org/verify]], dan tetapan organisasi di [[page:/org/setup]]. Adept membantu keputusan anda; manusia yang membuatnya.",
            "zh": "你的团队空间：成员在 [[page:/org/members]]，技能差距在 [[page:/org/gaps]]，项目在 [[page:/org/programmes]]（新建见 [[page:/org/programmes/new]]），待审核的完成情况在 [[page:/org/verify]]，组织设置在 [[page:/org/setup]]。Adept 为你的决定提供参考，决定由人来做。",
        },
    ),
    Topic(
        id="help_join_org",
        words=(
            "join code",
            "join an organisation",
            "join an organization",
            "join my company",
            "join my team",
            "invite code",
            "invite members",
            "invite my team",
            "add team members",
            "kod sertai",
            "sertai organisasi",
            "加入码",
            "加入组织",
            "邀请成员",
        ),
        patterns=(
            _all(
                r"\b(?:join|enter|use|redeem|invite|add)\w*\b",
                r"\b(?:code|organi[sz]ation|company|employer|team|members?|colleagues?)\b",
            ),
            re.compile(r"(?:加入|邀请).{0,4}(?:组织|公司|团队|成员)|加入码"),
            re.compile(
                r"\b(?:sertai|jemput|undang)\b.{0,20}\b(?:organisasi|syarikat|pasukan|ahli)\b"
            ),
        ),
        vocab=frozenset({"invite", "join"}),
        en="Ask your manager for the join code, then open [[page:/app/join]] (or use it when you sign up) and confirm that you want to join. You choose what to share, and nothing is shared without your consent. Managers share the code from [[page:/org/members]].",
        ms="Minta kod sertai daripada pengurus anda, kemudian buka [[page:/app/join]] (atau gunakan semasa mendaftar) dan sahkan bahawa anda mahu menyertai. Anda memilih apa yang dikongsi, dan tiada apa dikongsi tanpa persetujuan anda. Pengurus berkongsi kod dari [[page:/org/members]].",
        zh="向你的经理索取加入码，然后打开 [[page:/app/join]]（或在注册时使用），确认你要加入。分享什么由你决定，未经你同意不会分享任何内容。经理可在 [[page:/org/members]] 分享加入码。",
        employee={
            "en": "You have already joined an organisation. What you share with it is managed on [[page:/work/skills]]. A different organisation's code can be used from your personal workspace.",
            "ms": "Anda sudah menyertai sebuah organisasi. Apa yang dikongsi diurus di [[page:/work/skills]]. Kod organisasi lain boleh digunakan dari ruang kerja peribadi anda.",
            "zh": "你已加入一个组织。你分享的内容在 [[page:/work/skills]] 管理。其他组织的加入码可在个人工作区使用。",
        },
        manager={
            "en": "Share your organisation's join code from [[page:/org/members]]. Each person joins with it, adds their skills and chooses what to share; you see who has finished their profile.",
            "ms": "Kongsi kod sertai organisasi anda dari [[page:/org/members]]. Setiap orang menyertai dengannya, menambah kemahiran dan memilih apa yang dikongsi; anda boleh melihat siapa yang telah siap profil.",
            "zh": "从 [[page:/org/members]] 分享组织的加入码。每个人用它加入、添加技能并选择分享内容；你可以看到谁已完成资料。",
        },
    ),
    Topic(
        id="help_workspaces",
        words=(
            "switch workspace",
            "change workspace",
            "workspace switcher",
            "personal workspace",
            "switch to personal",
            "switch to organisation",
            "switch to organization",
            "tukar ruang kerja",
            "ruang kerja peribadi",
            "切换工作区",
            "个人工作区",
        ),
        patterns=(
            _all(
                r"\bworkspaces?\b",
                r"\b(?:switch\w*|chang\w+|move|go|between|differen\w+|which|what|where|how)\b",
            ),
            re.compile(
                r"\b(?:personal|organi[sz]ation)\s+(?:vs|versus|or|and)\s+(?:personal|organi[sz]ation)\b"
            ),
            re.compile(r"工作区"),
            re.compile(r"\bruang\s+kerja\b"),
        ),
        vocab=frozenset({"workspace", "workspaces"}),
        en="If you belong to an organisation, use the workspace switcher in the menu to move between your personal workspace and the organisation workspace. They are separate: your personal plans, matches and chats stay private, and your employer sees only what you consent to share.",
        ms="Jika anda ahli sebuah organisasi, guna penukar ruang kerja di menu untuk bertukar antara ruang kerja peribadi dan ruang kerja organisasi. Kedua-duanya berasingan: pelan, padanan dan sembang peribadi anda kekal peribadi, dan majikan hanya melihat apa yang anda setuju kongsikan.",
        zh="如果你属于某个组织，可使用菜单中的工作区切换器在个人工作区和组织工作区之间切换。两者相互独立：你的个人计划、匹配和聊天保持私密，雇主只能看到你同意分享的内容。",
    ),
    Topic(
        id="help_sharing",
        words=(
            "stop sharing",
            "withdraw consent",
            "change consent",
            "revoke consent",
            "share my skills",
            "sharing consent",
            "what i share",
            "berhenti berkongsi",
            "tarik balik persetujuan",
            "停止分享",
            "撤回同意",
            "分享设置",
        ),
        patterns=(
            _all(
                r"\b(?:stop|withdraw|revoke|change|manage|turn\s+off|opt\s+out|update|control)\w*\b",
                r"\b(?:sharing|consent|share)\b",
            ),
            re.compile(r"(?:停止|撤回|修改|管理).{0,3}(?:分享|同意)"),
            re.compile(
                r"\b(?:berhenti|tarik\s+balik|ubah)\b.{0,15}\b(?:kongsi|berkongsi|persetujuan)\b"
            ),
        ),
        vocab=frozenset({"consent", "sharing"}),
        en="Nothing about your skills is shared with an employer unless you agree. In an organisation workspace, you manage what you share, and can withdraw it, on [[page:/work/skills]]. Your personal workspace is never shared. More in the [[page:/privacy]] notice.",
        ms="Tiada apa tentang kemahiran anda dikongsi dengan majikan melainkan anda bersetuju. Dalam ruang kerja organisasi, anda mengurus apa yang dikongsi, dan boleh menariknya balik, di [[page:/work/skills]]. Ruang kerja peribadi anda tidak pernah dikongsi. Maklumat lanjut dalam notis [[page:/privacy]].",
        zh="除非你同意，关于你技能的任何信息都不会分享给雇主。在组织工作区，你可在 [[page:/work/skills]] 管理并撤回分享。你的个人工作区从不分享。更多信息见 [[page:/privacy]] 隐私声明。",
    ),
    Topic(
        id="help_languages",
        words=(
            "change language",
            "switch language",
            "change the language",
            "tukar bahasa",
            "切换语言",
            "更换语言",
        ),
        patterns=(
            re.compile(
                r"\b(?:chang\w+|switch\w*|set|use|select\w*|available|support\w*|which|what)\b.{0,25}\blanguages?\b"
            ),
            re.compile(
                r"\blanguages?\b.{0,25}\b(?:chang\w+|switch\w*|set|available|support\w*|options?)\b"
            ),
            re.compile(
                r"\b(?:in|to|into)\s+(?:malay|bahasa(?:\s+melayu)?|chinese|mandarin|english)\b"
            ),
            re.compile(r"语言|中文|马来文|英文|\b(?:tukar|ubah|guna)\s+bahasa\b"),
        ),
        vocab=frozenset({"language", "languages", "bahasa", "mandarin"}),
        en="Adept speaks English, Bahasa Melayu and 中文. Change the language from the language switcher in the top menu, and the whole interface follows. I also reply in the language you write to me in.",
        ms="Adept menyokong Bahasa Inggeris, Bahasa Melayu dan 中文. Tukar bahasa dari penukar bahasa di menu atas dan seluruh antara muka akan mengikutinya. Saya juga membalas dalam bahasa yang anda gunakan.",
        zh="Adept 支持 English、Bahasa Melayu 和中文。在顶部菜单的语言切换器中更换语言，整个界面都会随之变化。我也会用你提问的语言回答。",
    ),
    Topic(
        id="help_account",
        words=(
            "sign up",
            "signup",
            "create an account",
            "create account",
            "register an account",
            "log in",
            "login",
            "sign in",
            "log out",
            "logout",
            "sign out",
            "forgot password",
            "reset password",
            "change password",
            "delete my account",
            "delete account",
            "download my data",
            "daftar akaun",
            "log masuk",
            "log keluar",
            "padam akaun",
            "注册",
            "登录",
            "退出登录",
            "忘记密码",
            "删除账号",
            "下载我的数据",
        ),
        patterns=(
            re.compile(r"\b(?:sign|log)\s*(?:in|up|out|on)\b|\b(?:login|logout|signup)\b"),
            re.compile(r"\b(?:forgot|forget|reset|chang\w+|lost)\b.{0,10}\bpasswords?\b"),
            re.compile(
                r"\b(?:creat\w+|open|register|delete|remov\w+|clos\w+)\b.{0,15}\b(?:an?\s+)?account\b"
            ),
            re.compile(r"\b(?:download|export)\b.{0,15}\b(?:my\s+)?data\b"),
            re.compile(r"(?:注册|登录|登入|退出|忘记密码|账号|账户)"),
            re.compile(r"\b(?:daftar|log\s+masuk|log\s+keluar|kata\s+laluan|akaun)\b"),
        ),
        vocab=frozenset({"account", "password", "login", "signup"}),
        en="Create a free account on [[page:/auth/signup]], or sign in from the top menu; sign out from the same menu. You can download or delete your data from My skills ([[page:/app/profile]]) or, for managers, team Settings. Details are in the [[page:/privacy]] notice.",
        ms="Cipta akaun percuma di [[page:/auth/signup]], atau log masuk dari menu atas; log keluar dari menu yang sama. Anda boleh memuat turun atau memadam data di Kemahiran saya ([[page:/app/profile]]) atau, bagi pengurus, Tetapan pasukan. Butiran dalam notis [[page:/privacy]].",
        zh="在 [[page:/auth/signup]] 创建免费账号，或从顶部菜单登录；同一菜单可退出登录。你可以在“我的技能”（[[page:/app/profile]]）下载或删除自己的数据，经理则在团队设置中操作。详情见 [[page:/privacy]] 隐私声明。",
        manager={
            "en": "Account and organisation settings are on [[page:/org/setup]]; sign in or out from the top menu. Details on how data is handled are in the [[page:/privacy]] notice.",
            "ms": "Akaun dan tetapan organisasi ada di [[page:/org/setup]]; log masuk atau keluar dari menu atas. Butiran pengendalian data ada dalam notis [[page:/privacy]].",
            "zh": "账号和组织设置在 [[page:/org/setup]]；在顶部菜单登录或退出。数据处理的详情见 [[page:/privacy]] 隐私声明。",
        },
    ),
    Topic(
        id="help_radar",
        words=(
            "radar",
            "future skills radar",
            "skills radar",
            "trend radar",
            "radar page",
            "radar tidak ada",
            "雷达",
            "技能雷达",
        ),
        patterns=(re.compile(r"\bradar\b|雷达"),),
        vocab=frozenset({"radar"}),
        en="The Future Skills Radar is on [[page:/app/radar]]: skills and roles that are rising or cooling off in the latest dated snapshot, for the AI pace you pick. They are estimates from research and labour projections, not guarantees; the sources are listed on [[page:/about]].",
        ms="Radar Kemahiran Masa Depan ada di [[page:/app/radar]]: kemahiran dan peranan yang meningkat atau menurun dalam petikan bertarikh terkini, mengikut kadar AI yang dipilih. Ia anggaran daripada penyelidikan dan unjuran tenaga kerja, bukan jaminan; sumber disenaraikan di [[page:/about]].",
        zh="未来技能雷达在 [[page:/app/radar]]：按你选择的 AI 速度，显示最新带日期快照中上升或降温的技能和职位。这些是根据研究和劳动力预测得出的估计，不是保证；来源列在 [[page:/about]]。",
        employee={
            "en": "Trend signals for your skills are on [[page:/work/skills]]; the sources are listed on [[page:/about]]. They are dated estimates, not guarantees.",
            "ms": "Isyarat trend untuk kemahiran anda ada di [[page:/work/skills]]; sumber disenaraikan di [[page:/about]]. Ia anggaran bertarikh, bukan jaminan.",
            "zh": "与你技能相关的趋势信号在 [[page:/work/skills]]；来源列在 [[page:/about]]。它们是带日期的估计，不是保证。",
        },
        manager={
            "en": "The team radar is on [[page:/org/radar]]: rising and cooling skills and roles in the latest dated snapshot. They are estimates, not guarantees; sources are on [[page:/about]].",
            "ms": "Radar pasukan ada di [[page:/org/radar]]: kemahiran dan peranan yang meningkat dan menurun dalam petikan bertarikh terkini. Ia anggaran, bukan jaminan; sumber di [[page:/about]].",
            "zh": "团队雷达在 [[page:/org/radar]]：最新带日期快照中上升和降温的技能与职位。这些是估计，不是保证；来源见 [[page:/about]]。",
        },
    ),
    Topic(
        id="help_index",
        words=(
            "what can i ask",
            "what can i do here",
            "what pages",
            "all pages",
            "list of pages",
            "site map",
            "sitemap",
            "feature list",
            "dashboard guide",
            "give me a tour",
            "getting started",
            "get started",
            "user guide",
            "apa yang boleh saya tanya",
            "panduan",
            "senarai ciri",
            "我能问什么",
            "功能列表",
            "使用指南",
            "新手指南",
        ),
        patterns=(
            re.compile(r"\bwhat\s+(?:can|could)\s+i\s+(?:ask|do\s+here|use)\b"),
            re.compile(r"\b(?:which|what)\s+(?:features?|pages?|sections?|tabs?)\b"),
            re.compile(
                r"\b(?:explain|describe|show|list)\b.{0,15}\b(?:features?|pages?|dashboard|tabs?|menu)\b"
            ),
            re.compile(
                r"\bhow\s+(?:do|to|can)\s+i\s+(?:use|start|begin)\s+(?:adept|this|the\s+(?:app|site|dashboard|platform))\b"
            ),
            re.compile(r"(?:怎么|如何).{0,4}(?:使用|用)(?:adept|这个|本)|有哪些(?:功能|页面)"),
        ),
        vocab=frozenset({"features", "dashboard", "tour", "pages"}),
        en="I can help with Adept and its pages: adding skills or uploading your CV ([[page:/app/onboarding]]), choosing a target role and reading your matches ([[page:/app/matches]]), your learning plan ([[page:/app/pathway]]), progress and evidence ([[page:/app/progress]]), job openings ([[page:/app/jobs]]), courses ([[page:/app/courses]]), Impact and evidence ([[page:/app/sdg]]), and Data and AI use ([[page:/about]]). Try “Where do I upload my CV?”.",
        ms="Saya boleh membantu tentang Adept dan halamannya: menambah kemahiran atau memuat naik CV ([[page:/app/onboarding]]), memilih peranan sasaran dan membaca padanan ([[page:/app/matches]]), pelan pembelajaran ([[page:/app/pathway]]), kemajuan dan bukti ([[page:/app/progress]]), jawatan kosong ([[page:/app/jobs]]), kursus ([[page:/app/courses]]), Kesan dan bukti ([[page:/app/sdg]]), dan Data dan penggunaan AI ([[page:/about]]). Cuba “Di mana saya boleh muat naik CV?”.",
        zh="我可以帮你了解 Adept 及其页面：添加技能或上传简历（[[page:/app/onboarding]]）、选择目标职位并查看匹配（[[page:/app/matches]]）、学习计划（[[page:/app/pathway]]）、进度与证明（[[page:/app/progress]]）、职位空缺（[[page:/app/jobs]]）、课程（[[page:/app/courses]]）、影响与证据（[[page:/app/sdg]]）以及数据与 AI 使用（[[page:/about]]）。试试问“在哪里上传简历？”。",
        employee={
            "en": "I can help with your organisation workspace: your programme plan ([[page:/work/plan]]), progress and evidence ([[page:/work/progress]]), and what you share ([[page:/work/skills]]). Ask about uploading a CV, switching workspace, privacy, or how Adept works ([[page:/about]]).",
            "ms": "Saya boleh membantu tentang ruang kerja organisasi anda: pelan program ([[page:/work/plan]]), kemajuan dan bukti ([[page:/work/progress]]), dan apa yang anda kongsi ([[page:/work/skills]]). Tanya tentang muat naik CV, menukar ruang kerja, privasi atau cara Adept berfungsi ([[page:/about]]).",
            "zh": "我可以帮你了解组织工作区：项目计划（[[page:/work/plan]]）、进度与证明（[[page:/work/progress]]）以及你分享的内容（[[page:/work/skills]]）。也可以问上传简历、切换工作区、隐私或 Adept 如何运作（[[page:/about]]）。",
        },
        manager={
            "en": "I can help with your team space: members ([[page:/org/members]]), skill gaps ([[page:/org/gaps]]), programmes ([[page:/org/programmes]]), completions to review ([[page:/org/verify]]), team Impact ([[page:/org/sdg]]) and settings ([[page:/org/setup]]). Ask about any of them, or about data and AI use ([[page:/about]]).",
            "ms": "Saya boleh membantu tentang ruang pasukan anda: ahli ([[page:/org/members]]), jurang kemahiran ([[page:/org/gaps]]), program ([[page:/org/programmes]]), penyelesaian untuk disemak ([[page:/org/verify]]), Kesan pasukan ([[page:/org/sdg]]) dan tetapan ([[page:/org/setup]]). Tanya tentang mana-mana, atau tentang data dan penggunaan AI ([[page:/about]]).",
            "zh": "我可以帮你了解团队空间：成员（[[page:/org/members]]）、技能差距（[[page:/org/gaps]]）、项目（[[page:/org/programmes]]）、待审核的完成情况（[[page:/org/verify]]）、团队影响（[[page:/org/sdg]]）和设置（[[page:/org/setup]]）。也可以问数据与 AI 使用（[[page:/about]]）。",
        },
    ),
)

TOPIC_IDS: frozenset[str] = frozenset(topic.id for topic in TOPICS)
_BY_ID: dict[str, Topic] = {topic.id: topic for topic in TOPICS}


def text(topic_id: str, audience: str, locale: Locale) -> str:
    """The server-authored help block for an audience, falling back to the learner version."""
    topic = _BY_ID[topic_id]
    variants = {"employee": topic.employee, "manager": topic.manager}.get(audience, {})
    return variants.get(locale) or getattr(topic, locale)


def keywords() -> dict[str, tuple[str, ...]]:
    return {topic.id: topic.words for topic in TOPICS}


def patterns() -> dict[str, tuple[re.Pattern[str], ...]]:
    return {topic.id: topic.patterns for topic in TOPICS}


def _edit1(a: str, b: str) -> bool:
    """True when two words differ by at most one insertion, deletion or substitution."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = j = diff = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        diff += 1
        if diff > 1:
            return False
        if len(a) == len(b):
            i += 1
        j += 1
    return diff + (len(b) - j) + (len(a) - i) <= 1


def fuzzy(question: str) -> str | None:
    """Best help topic by typo-tolerant vocabulary overlap, or None.

    Used only when no keyword or phrase rule matched, so a misspelt paraphrase such as
    "wher do i uplaod my resumee" still reaches the right block. A topic needs two distinct
    vocabulary hits (or one hit for its single-word vocabulary of one) to win.
    """
    tokens = set(re.findall(r"[a-z]{3,}", question.lower()))
    if not tokens:
        return None
    best: tuple[int, str] | None = None
    for topic in TOPICS:
        hits = sum(
            1
            for word in topic.vocab
            if word in tokens or (len(word) >= 5 and any(_edit1(word, t) for t in tokens))
        )
        need = 1 if len(topic.vocab) <= 2 else 2
        if hits >= need and (best is None or hits > best[0]):
            best = (hits, topic.id)
    return best[1] if best else None
