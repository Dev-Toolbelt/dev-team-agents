import sys
from html import escape

W, H = 1600, 1060
BG, CARD, STROKE = "#0b1020", "#131a2c", "#25304b"
TXT, MUTED = "#e7eaf3", "#8f9bb8"
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, monospace"

S = {
    "en": {
        "title": "Dev Team Agents",
        "subtitle": "A multi-agent development harness — how a task flows from your prompt to a merged PR",
        "you": "You",
        "cmd_hint": "one command",
        "orch": "Orchestrator",
        "orch_sub": "main-session persona: routes the task, spawns agents in parallel",
        "ctx_title": "Context first",
        "ctx_sub": "Every agent loads the project before acting",
        "ctx": ["CLAUDE.md / AGENTS.md", "docs/project.md", "Architecture & standards", "ADRs (decisions)", "Wiki index", "Feature specs", "preferences.json"],
        "ctx_win": "Your project rules always win",
        "stages": [
            ("PLAN", "#8b7cf6", ["product-analyst", "software-architect", "database-specialist", "ui-ux-designer"], ["Spec with Given/When/", "Then acceptance criteria"]),
            ("PLAN GATE", "#f5b54a", ["you approve"], ["Nothing executes before", "approval. Steps mirror", "to the task board."]),
            ("BUILD", "#4cc3ff", ["backend-developer", "frontend-developer", "mobile-developer", "devops-specialist", "seo-specialist"], ["Isolated git worktree,", "parallel waves"]),
            ("TEST", "#4ade80", ["backend-test-specialist", "frontend-test-specialist"], ["Only tests covering", "the touched code"]),
            ("QUALITY GATE", "#f472b6", ["code-reviewer", "  backend-reviewer", "  frontend-reviewer", "security-specialist", "qa-specialist"], ["Findings are fixed,", "then re-reviewed"]),
            ("SHIP & LEARN", "#2dd4bf", ["/devteam:commit", "/devteam:pr", "/devteam:push", "/devteam:learn", "technical-writer"], ["Decision check before PR,", "CI watched & auto-fixed,", "docs kept in sync"]),
        ],
        "loop": "fix → re-review loop",
        "harness": "THE HARNESS — always on, enforced by hooks",
        "hooks_t": "Lifecycle hooks",
        "hooks": ["SessionStart · banner, language, context", "UserPromptSubmit · recall & context hints", "PreToolUse · guards & plugins", "Stop · session summary required", "Stop · lints & ADR gap"],
        "mem_t": "5-layer memory",
        "mem": [("Structural", "docs/ — stack, architecture"), ("Episodic", "session summary, ~30 days"), ("Semantic", "docs/wiki/ — never deleted"), ("Decisional", "ADRs — why, immutable"), ("Mechanical", "code graph — regenerated")],
        "tier_t": "Right model per role",
        "tiers": [("reasoning", "opus", "architecture, planning, security"), ("backend-exec", "sonnet", "implementation, review, QA"), ("frontend", "sonnet", "UI, components, frontend tests"), ("repetitive", "haiku", "docs, changelogs")],
        "stats": [("19", "agents"), ("150+", "skills"), ("43", "commands"), ("3", "providers")],
        "prov_t": "One canonical source, rendered per provider",
        "prov": ["Claude Code", "opencode", "OpenAI Codex CLI"],
        "cli": "devteam CLI + desktop app · global store · bind once per project",
    },
    "pt": {
        "title": "Dev Team Agents",
        "subtitle": "Um harness multi-agente para desenvolvimento — como uma tarefa vai do seu prompt até o PR",
        "you": "Você",
        "cmd_hint": "um comando",
        "orch": "Orquestrador",
        "orch_sub": "persona da sessão principal: roteia e dispara agentes em paralelo",
        "ctx_title": "Contexto primeiro",
        "ctx_sub": "Todo agente carrega o projeto antes de agir",
        "ctx": ["CLAUDE.md / AGENTS.md", "docs/project.md", "Arquitetura e padrões", "ADRs (decisões)", "Índice da wiki", "Specs de features", "preferences.json"],
        "ctx_win": "As regras do seu projeto sempre vencem",
        "stages": [
            ("PLANEJAR", "#8b7cf6", ["product-analyst", "software-architect", "database-specialist", "ui-ux-designer"], ["Spec com critérios", "Given/When/Then"]),
            ("APROVAÇÃO", "#f5b54a", ["você aprova"], ["Nada executa antes da", "aprovação. Os passos vão", "para o quadro de tarefas."]),
            ("CONSTRUIR", "#4cc3ff", ["backend-developer", "frontend-developer", "mobile-developer", "devops-specialist", "seo-specialist"], ["Worktree git isolada,", "ondas em paralelo"]),
            ("TESTAR", "#4ade80", ["backend-test-specialist", "frontend-test-specialist"], ["Só os testes do", "código alterado"]),
            ("QUALIDADE", "#f472b6", ["code-reviewer", "  backend-reviewer", "  frontend-reviewer", "security-specialist", "qa-specialist"], ["Achados corrigidos", "e revisados de novo"]),
            ("ENTREGAR", "#2dd4bf", ["/devteam:commit", "/devteam:pr", "/devteam:push", "/devteam:learn", "technical-writer"], ["Check de decisões no PR,", "CI monitorado e corrigido,", "docs sempre em dia"]),
        ],
        "loop": "ciclo corrigir → revisar",
        "harness": "O HARNESS — sempre ativo, garantido por hooks",
        "hooks_t": "Hooks de ciclo de vida",
        "hooks": ["SessionStart · banner, idioma, contexto", "UserPromptSubmit · recall e dicas de contexto", "PreToolUse · guardas e plugins", "Stop · resumo da sessão obrigatório", "Stop · lints e lacunas de ADR"],
        "mem_t": "Memória em 5 camadas",
        "mem": [("Estrutural", "docs/ — stack, arquitetura"), ("Episódica", "resumo de sessão, ~30 dias"), ("Semântica", "docs/wiki/ — nunca apagada"), ("Decisória", "ADRs — o porquê, imutável"), ("Mecânica", "grafo do código — regenerado")],
        "tier_t": "O modelo certo por papel",
        "tiers": [("reasoning", "opus", "arquitetura, planejamento, segurança"), ("backend-exec", "sonnet", "implementação, revisão, QA"), ("frontend", "sonnet", "UI, componentes, testes de front"), ("repetitive", "haiku", "docs, changelogs")],
        "stats": [("19", "agentes"), ("150+", "skills"), ("43", "comandos"), ("3", "providers")],
        "prov_t": "Uma fonte canônica, renderizada para cada provider",
        "prov": ["Claude Code", "opencode", "OpenAI Codex CLI"],
        "cli": "CLI devteam + app desktop · store global · bind uma vez por projeto",
    },
}

out = []
def add(s): out.append(s)
def t(x, y, s, size=14, fill=TXT, weight=400, font=SANS, anchor="start", extra=""):
    add(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{escape(s)}</text>')
def rect(x, y, w, h, r=14, fill=CARD, stroke=STROKE, sw=1, extra=""):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
def arrow(x1, y1, x2, y2, color=MUTED, dash=""):
    d = f'stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" {d} marker-end="url(#ah)"/>')

def build(L):
    s = S[L]
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    add('<defs>'
        f'<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
        '<linearGradient id="hdr" x1="0" x2="1"><stop offset="0" stop-color="#8b7cf6"/><stop offset="0.5" stop-color="#4cc3ff"/><stop offset="1" stop-color="#2dd4bf"/></linearGradient>'
        '<radialGradient id="glow" cx="0.5" cy="0" r="0.8"><stop offset="0" stop-color="#1c2550"/><stop offset="1" stop-color="#0b1020"/></radialGradient>'
        '</defs>')
    add(f'<rect width="{W}" height="{H}" fill="url(#glow)"/>')

    # header
    t(40, 64, s["title"], 34, TXT, 800)
    add(f'<rect x="40" y="78" width="120" height="4" rx="2" fill="url(#hdr)"/>')
    t(40, 108, s["subtitle"], 16, MUTED)
    sx = W - 40
    for num, lab in reversed(s["stats"]):
        bw = 96
        sx -= bw
        rect(sx, 40, bw - 10, 62, 12)
        t(sx + (bw - 10) / 2, 72, num, 22, TXT, 800, anchor="middle")
        t(sx + (bw - 10) / 2, 92, lab, 12, MUTED, anchor="middle")

    # context column
    cx, cy, cw, ch = 40, 140, 270, 500
    rect(cx, cy, cw, ch, 16, "#111a30", "#3a3170", 1.5)
    t(cx + 20, cy + 34, s["ctx_title"], 18, TXT, 700)
    t(cx + 20, cy + 56, s["ctx_sub"], 12, MUTED)
    yy = cy + 80
    for item in s["ctx"]:
        rect(cx + 18, yy, cw - 36, 34, 8, "#0d1426", STROKE)
        t(cx + 32, yy + 22, item, 13, TXT, 500, MONO if "." in item else SANS)
        yy += 44
    rect(cx + 18, cy + ch - 62, cw - 36, 44, 10, "#2a2350", "#8b7cf6")
    t(cx + cw / 2, cy + ch - 34, s["ctx_win"], 13 if len(s["ctx_win"]) < 32 else 11.5, "#d9d3ff", 700, anchor="middle")

    # top strip: you -> command -> orchestrator
    px = 340
    ty = 140
    rect(px, ty, 120, 70, 35, "#1e2a4a", "#4cc3ff", 1.5)
    t(px + 60, ty + 42, s["you"], 18, TXT, 700, anchor="middle")
    arrow(px + 124, ty + 35, px + 168, ty + 35)
    rect(px + 172, ty, 470, 70, 12, "#0d1426", STROKE)
    t(px + 190, ty + 30, "/devteam:plan · fix · review · commit · pr", 15, "#9fe3ff", 600, MONO)
    t(px + 190, ty + 52, s["cmd_hint"] + " · " + ("or plain language" if L == "en" else "ou linguagem natural"), 12, MUTED)
    arrow(px + 646, ty + 35, px + 690, ty + 35)
    ox = px + 694
    rect(ox, ty, W - 40 - ox, 70, 12, "#1a1f3d", "#8b7cf6", 1.5)
    t(ox + 20, ty + 30, s["orch"], 17, TXT, 700)
    t(W - 60, ty + 30, "/devteam:orchestrate", 13, "#9fe3ff", 600, MONO, "end")
    t(ox + 20, ty + 52, s["orch_sub"], 12, MUTED)
    # orchestrator fans out
    add(f'<path d="M{(ox + W - 40) / 2},{ty + 70} L{(ox + W - 40) / 2},{ty + 90} L{px + 95},{ty + 90} L{px + 95},{ty + 104}" fill="none" stroke="{MUTED}" stroke-width="2" marker-end="url(#ah)"/>')
    # context arrow into pipeline
    arrow(cx + cw + 2, 420, px - 6, 420, "#8b7cf6", "5 4")

    # pipeline
    n = 6
    gap = 18
    colw = (W - 40 - px - gap * (n - 1)) / n
    py, ph = 250, 390
    for i, (name, color, chips, note) in enumerate(s["stages"]):
        x = px + i * (colw + gap)
        gate = i == 1
        rect(x, py, colw, ph, 14, "#1d1a12" if gate else CARD, color if gate else STROKE, 1.5 if gate else 1)
        add(f'<rect x="{x}" y="{py}" width="{colw}" height="6" rx="3" fill="{color}"/>')
        add(f'<circle cx="{x + 26}" cy="{py + 36}" r="13" fill="{color}" fill-opacity="0.18" stroke="{color}"/>')
        t(x + 26, py + 41, str(i + 1), 13, color, 800, anchor="middle")
        t(x + 48, py + 41, name, 14, TXT, 800, extra='letter-spacing="1"')
        yy = py + 64
        if gate:
            # lock icon + approval
            add(f'<rect x="{x + colw / 2 - 22}" y="{yy + 30}" width="44" height="34" rx="6" fill="none" stroke="{color}" stroke-width="2.5"/>')
            add(f'<path d="M{x + colw / 2 - 13},{yy + 30} v-10 a13,13 0 0 1 26,0 v10" fill="none" stroke="{color}" stroke-width="2.5"/>')
            add(f'<circle cx="{x + colw / 2}" cy="{yy + 46}" r="4" fill="{color}"/>')
            yy += 86
            rect(x + 12, yy, colw - 24, 34, 8, "#3a2d10", color)
            t(x + colw / 2, yy + 22, "✓ " + chips[0], 13, "#ffd88a", 700, anchor="middle")
            yy += 48
        else:
            for c in chips:
                sub = c.startswith("  ")
                cx2 = x + (24 if sub else 12)
                rect(cx2, yy, colw - 12 - (cx2 - x), 30, 7, "#0d1426", color if not sub else STROKE, 1, 'stroke-opacity="0.55"')
                if sub:
                    add(f'<path d="M{x + 18},{yy - 6} v21 h5" fill="none" stroke="{MUTED}" stroke-width="1.5"/>')
                t(cx2 + 10, yy + 20, c.strip(), 11.5 if len(c.strip()) < 22 else 10.5, TXT, 500, MONO)
                yy += 38
        ny = py + ph - 22 - 18 * (len(note) - 1)
        add(f'<line x1="{x + 14}" y1="{ny - 24}" x2="{x + colw - 14}" y2="{ny - 24}" stroke="{STROKE}"/>')
        for j, line in enumerate(note):
            t(x + 14, ny + 18 * j, line, 12, MUTED)
        if i < n - 1:
            arrow(x + colw + 1, py + 36, x + colw + gap - 1, py + 36)

    # loop back arrow from quality gate to build
    bx = px + 2 * (colw + gap) + colw / 2
    qx = px + 4 * (colw + gap) + colw / 2
    ly = py + ph + 22
    add(f'<path d="M{qx},{py + ph} V{ly} H{bx} V{py + ph + 4}" fill="none" stroke="#f472b6" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#ah)"/>')
    rect((bx + qx) / 2 - 90, ly - 12, 180, 24, 12, BG, "#f472b6")
    t((bx + qx) / 2, ly + 5, s["loop"], 12, "#f9a8d4", 600, anchor="middle")

    # harness
    hy = 700
    t(40, hy, s["harness"], 13, MUTED, 800, extra='letter-spacing="2"')
    bw3 = (W - 80 - 2 * 20) / 3
    by, bh = hy + 16, 214
    # hooks
    x = 40
    rect(x, by, bw3, bh, 14)
    t(x + 20, by + 32, s["hooks_t"], 17, TXT, 700)
    for j, line in enumerate(s["hooks"]):
        k, v = line.split(" · ")
        yy = by + 64 + j * 30
        t(x + 20, yy, k, 12, "#9fe3ff", 600, MONO)
        t(x + 150, yy, v, 13, TXT)
    # memory
    x = 40 + bw3 + 20
    rect(x, by, bw3, bh, 14)
    t(x + 20, by + 32, s["mem_t"], 17, TXT, 700)
    cols = ["#8b7cf6", "#4cc3ff", "#4ade80", "#f5b54a", "#2dd4bf"]
    for j, (k, v) in enumerate(s["mem"]):
        yy = by + 50 + j * 30
        add(f'<rect x="{x + 20}" y="{yy}" width="6" height="22" rx="3" fill="{cols[j]}"/>')
        t(x + 36, yy + 16, k, 13, TXT, 700)
        t(x + 140, yy + 16, v, 13, MUTED)
    # tiers
    x = 40 + 2 * (bw3 + 20)
    rect(x, by, bw3, bh, 14)
    t(x + 20, by + 32, s["tier_t"], 17, TXT, 700)
    mc = {"opus": "#8b7cf6", "sonnet": "#4cc3ff", "haiku": "#4ade80"}
    for j, (tier, model, use) in enumerate(s["tiers"]):
        yy = by + 50 + j * 38
        t(x + 20, yy + 18, tier, 12, MUTED, 600, MONO)
        rect(x + 138, yy + 2, 70, 24, 12, "#0d1426", mc[model])
        t(x + 173, yy + 19, model, 12, mc[model], 700, MONO, "middle")
        t(x + 222, yy + 19, use, 12.5, TXT)

    # providers
    ry = by + bh + 22
    rect(40, ry, W - 80, 70, 14, "#0f1628", STROKE)
    t(64, ry + 30, s["prov_t"], 15, TXT, 700)
    t(64, ry + 52, s["cli"], 12.5, MUTED)
    pxp = W - 64
    for name in reversed(s["prov"]):
        w = 14 + len(name) * 8.6
        pxp -= w
        rect(pxp, ry + 18, w, 34, 17, "#1a2340", "#4cc3ff")
        t(pxp + w / 2, ry + 40, name, 13.5, TXT, 700, anchor="middle")
        pxp -= 12
    add("</svg>")
    return "\n".join(out)

L = sys.argv[1]
sys.stdout.write(build(L))
