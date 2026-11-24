import sys
from html import escape

W, H = 1600, 1480
BG, TXT, MUTED, STROKE = "#0b1020", "#e7eaf3", "#8f9bb8", "#25304b"
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, monospace"
COLORS = ["#a78bfa", "#8b7cf6", "#6d8bff", "#4cc3ff", "#2dd4bf", "#4ade80", "#f5b54a", "#f472b6"]

S = {
    "en": {
        "title": "Dev Team Agents — the layers",
        "subtitle": "Your prompt crosses every layer of the harness before a single line of code is written",
        "prompt_tag": "YOUR PROMPT",
        "prompt": "“Add password reset to the API”",
        "layers": [
            ("Hooks", "Every prompt is enriched with recall and context hints before the model sees it", ["SessionStart", "UserPromptSubmit", "recall", "hints", "language"]),
            ("Project rules", "Your conventions come first — conflicts are flagged, never ignored", ["CLAUDE.md", "AGENTS.md", "contradiction guard"]),
            ("Memory", "What the project already knows, loaded by keyword, not in bulk", ["docs/project.md", "wiki index", "ADRs", "session summary", "code graph"]),
            ("Routing", "The command and the diff decide which specialists are needed", ["/devteam:*", "orchestrator", "auto-routing", "spawn classifier"]),
            ("Plan & spec", "Acceptance criteria and a plan — nothing runs without your approval", ["Given/When/Then", "plan template", "approval gate"]),
            ("Agents & skills", "19 specialists, each on the right model, loading only the skills it needs", ["opus", "sonnet", "haiku", "150+ skills"]),
            ("Workflow", "Isolated worktree, parallel waves, review until it is clean", ["build", "test", "review", "QA", "fix loop"]),
            ("Guardrails", "Stop hooks check the work before the session ends; devteam check guards the PR", ["session summary", "lints", "ADR gap", "devteam check", "scoped review"]),
        ],
        "result_tag": "RESULT",
        "result": ["Code + tests", "Commit & PR", "CI green", "Docs in sync"],
        "feedback": "/devteam:learn — memory grows",
        "foot": "Same layers on Claude Code · opencode · OpenAI Codex CLI",
    },
    "pt": {
        "title": "Dev Team Agents — as camadas",
        "subtitle": "Seu prompt atravessa todas as camadas do harness antes de qualquer linha de código ser escrita",
        "prompt_tag": "SEU PROMPT",
        "prompt": "“Adicione reset de senha na API”",
        "layers": [
            ("Hooks", "Todo prompt é enriquecido com recall e dicas de contexto antes de o modelo vê-lo", ["SessionStart", "UserPromptSubmit", "recall", "dicas", "idioma"]),
            ("Regras do projeto", "Suas convenções vêm primeiro — conflitos são apontados, nunca ignorados", ["CLAUDE.md", "AGENTS.md", "contradiction guard"]),
            ("Memória", "O que o projeto já sabe, carregado por palavra-chave, não em bloco", ["docs/project.md", "índice da wiki", "ADRs", "resumo de sessão", "grafo do código"]),
            ("Roteamento", "O comando e o diff decidem quais especialistas entram", ["/devteam:*", "orchestrator", "auto-routing", "spawn classifier"]),
            ("Plano & spec", "Critérios de aceite e um plano — nada roda sem a sua aprovação", ["Given/When/Then", "template de plano", "aprovação"]),
            ("Agentes & skills", "19 especialistas, cada um no modelo certo, carregando só as skills necessárias", ["opus", "sonnet", "haiku", "150+ skills"]),
            ("Fluxo", "Worktree isolada, ondas em paralelo, revisão até ficar limpo", ["construir", "testar", "revisar", "QA", "ciclo de correção"]),
            ("Guardrails", "Hooks de Stop verificam o trabalho antes do fim da sessão; o devteam check protege o PR", ["resumo de sessão", "lints", "lacuna de ADR", "devteam check", "revisão com escopo"]),
        ],
        "result_tag": "RESULTADO",
        "result": ["Código + testes", "Commit & PR", "CI verde", "Docs em dia"],
        "feedback": "/devteam:learn — a memória cresce",
        "foot": "As mesmas camadas no Claude Code · opencode · OpenAI Codex CLI",
    },
}

out = []
def add(s): out.append(s)
def t(x, y, s, size=14, fill=TXT, weight=400, font=SANS, anchor="start", extra=""):
    add(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{escape(s)}</text>')
def rect(x, y, w, h, r=12, fill="#131a2c", stroke=STROKE, sw=1, extra=""):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

def build(L):
    s = S[L]
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    add('<defs>'
        '<radialGradient id="bg" cx="0.3" cy="0.1" r="1"><stop offset="0" stop-color="#1b2450"/><stop offset="1" stop-color="#0b1020"/></radialGradient>'
        '<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="0.5" stop-color="#9fe3ff"/><stop offset="1" stop-color="#f472b6"/></linearGradient>'
        '<linearGradient id="hdr" x1="0" x2="1"><stop offset="0" stop-color="#a78bfa"/><stop offset="0.5" stop-color="#4cc3ff"/><stop offset="1" stop-color="#f472b6"/></linearGradient>'
        '<radialGradient id="hole"><stop offset="0" stop-color="#ffffff" stop-opacity="0.95"/><stop offset="0.35" stop-color="#9fe3ff" stop-opacity="0.6"/><stop offset="1" stop-color="#4cc3ff" stop-opacity="0"/></radialGradient>'
        '<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>'
        f'<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4ade80"/></marker>'
        '</defs>')
    add(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

    t(60, 72, s["title"], 34, TXT, 800)
    add(f'<rect x="60" y="88" width="140" height="4" rx="2" fill="url(#hdr)"/>')
    t(60, 120, s["subtitle"], 17, MUTED)

    cx = 470
    hw, hd, th = 300, 62, 14
    y0, step = 330, 120
    n = len(s["layers"])
    ys = [y0 + i * step for i in range(n)]

    # prompt bubble
    py = 160
    bw = 520
    add(f'<rect x="{cx - bw / 2}" y="{py}" width="{bw}" height="84" rx="20" fill="#1a2245" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.5"/>')
    add(f'<path d="M{cx - 14},{py + 84} L{cx},{py + 102} L{cx + 14},{py + 84} z" fill="#1a2245"/>')
    t(cx, py + 30, s["prompt_tag"], 12, "#9fe3ff", 800, anchor="middle", extra='letter-spacing="3"')
    t(cx, py + 62, s["prompt"], 22, TXT, 600, anchor="middle")

    # glow beam behind everything
    end_y = ys[-1] + 150
    add(f'<rect x="{cx - 8}" y="{py + 104}" width="16" height="{end_y - py - 104}" fill="#4cc3ff" fill-opacity="0.25" filter="url(#blur)"/>')

    def beam(y1, y2, col="#ffffff"):
        add(f'<rect x="{cx - 9}" y="{y1}" width="18" height="{y2 - y1}" fill="{col}" fill-opacity="0.22" filter="url(#blur)"/>')
        add(f'<rect x="{cx - 2}" y="{y1}" width="4" height="{y2 - y1}" rx="2" fill="{col}"/>')

    beam(py + 104, ys[0])
    for i, (name, desc, chips) in enumerate(s["layers"]):
        y = ys[i]
        c = COLORS[i]
        # plate: top face + two side faces
        L_, T_, R_, B_ = (cx - hw, y), (cx, y - hd), (cx + hw, y), (cx, y + hd)
        add(f'<path d="M{L_[0]},{L_[1]} L{B_[0]},{B_[1]} L{B_[0]},{B_[1] + th} L{L_[0]},{L_[1] + th} z" fill="{c}" fill-opacity="0.35"/>')
        add(f'<path d="M{B_[0]},{B_[1]} L{R_[0]},{R_[1]} L{R_[0]},{R_[1] + th} L{B_[0]},{B_[1] + th} z" fill="{c}" fill-opacity="0.22"/>')
        add(f'<path d="M{L_[0]},{L_[1]} L{T_[0]},{T_[1]} L{R_[0]},{R_[1]} L{B_[0]},{B_[1]} z" fill="{c}" fill-opacity="0.16" stroke="{c}" stroke-width="1.6"/>')
        # inner grid lines for texture
        for k in (1, 2, 3):
            f = k / 4
            add(f'<line x1="{L_[0] + (T_[0] - L_[0]) * f}" y1="{L_[1] + (T_[1] - L_[1]) * f}" x2="{B_[0] + (R_[0] - B_[0]) * f}" y2="{B_[1] + (R_[1] - B_[1]) * f}" stroke="{c}" stroke-opacity="0.18"/>')
            add(f'<line x1="{L_[0] + (B_[0] - L_[0]) * f}" y1="{L_[1] + (B_[1] - L_[1]) * f}" x2="{T_[0] + (R_[0] - T_[0]) * f}" y2="{T_[1] + (R_[1] - T_[1]) * f}" stroke="{c}" stroke-opacity="0.18"/>')
        # layer number on the plate
        t(cx - hw + 70, y + 6, f"0{i + 1}", 16, c, 800, MONO, "middle")
        # hole glow where the beam pierces
        add(f'<ellipse cx="{cx}" cy="{y}" rx="34" ry="12" fill="url(#hole)"/>')
        # beam continues downwards, emerging from under the plate
        nxt = ys[i + 1] if i + 1 < n else end_y
        beam(y + 2, nxt, c)

        # leader + label panel
        px, pw = 860, 700
        add(f'<line x1="{cx + hw + 8}" y1="{y}" x2="{px - 8}" y2="{y}" stroke="{c}" stroke-opacity="0.6" stroke-dasharray="3 5"/>')
        add(f'<circle cx="{cx + hw + 4}" cy="{y}" r="4" fill="{c}"/>')
        ph = 100
        rect(px, y - ph / 2, pw, ph, 14, "#121a2e", STROKE)
        add(f'<rect x="{px}" y="{y - ph / 2}" width="6" height="{ph}" rx="3" fill="{c}"/>')
        t(px + 24, y - 18, name, 19, TXT, 700)
        t(px + 24, y + 4, desc, 13.5, MUTED)
        chx = px + 24
        for ch in chips:
            w = len(ch) * 7.3 + 20
            rect(chx, y + 15, w, 24, 12, "#0d1426", c, 1, 'stroke-opacity="0.7"')
            t(chx + w / 2, y + 31, ch, 11.5, TXT, 500, MONO, "middle")
            chx += w + 8

    # result
    ry = end_y
    rw = 620
    add(f'<rect x="{cx - rw / 2}" y="{ry}" width="{rw}" height="110" rx="20" fill="#0f2a24" stroke="#4ade80" stroke-width="2"/>')
    t(cx, ry + 32, s["result_tag"], 12, "#4ade80", 800, anchor="middle", extra='letter-spacing="3"')
    items = s["result"]
    iw = (rw - 40) / len(items)
    for j, it in enumerate(items):
        x = cx - rw / 2 + 20 + j * iw
        rect(x + 4, ry + 50, iw - 8, 40, 10, "#123a30", "#4ade80", 1, 'stroke-opacity="0.5"')
        t(x + iw / 2, ry + 75, "✓ " + it, 13.5, "#c9f7d9", 700, anchor="middle")

    # feedback loop: result -> memory layer (left side)
    my = ys[2]
    lx = 70
    add(f'<path d="M{cx - rw / 2},{ry + 55} H{lx} V{my} H{cx - hw - 10}" fill="none" stroke="#4ade80" stroke-width="2" stroke-dasharray="7 5" marker-end="url(#ah)"/>')
    mid = (ry + 55 + my) / 2
    add(f'<g transform="translate({lx - 10},{mid}) rotate(-90)">')
    rect(-150, -14, 300, 28, 14, BG, "#4ade80")
    t(0, 5, s["feedback"], 12.5, "#86efac", 700, MONO, "middle")
    add('</g>')

    t(W - 60, H - 34, s["foot"], 13, MUTED, 500, anchor="end")
    add("</svg>")
    return "\n".join(out)

sys.stdout.write(build(sys.argv[1]))
