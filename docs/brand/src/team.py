import json, os, re, sys
from html import escape
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "app", "src", "renderer", "assets", "agents") + os.sep
d = json.load(open(A + "agents.json"))
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"; MONO = "'JetBrains Mono', Menlo, Consolas, monospace"
TXT, MUTED, STROKE = "#e7eaf3", "#8f9bb8", "#25304b"
LANG = sys.argv[2]
TX = {"pt-BR": {"title": "Dev Team Agents — Conheça o time", "sub": "{n} agentes especialistas — cada um com seu papel, modelo e identidade",
  "cats": ["Planejamento & arquitetura", "Implementação", "Qualidade & revisão", "Suporte"]},
 "en": {"title": "Dev Team Agents — Meet the team", "sub": "{n} specialist agents — each with its own role, model and identity",
  "cats": ["Planning & architecture", "Implementation", "Quality & review", "Enablement"]}}[LANG]
CATS = list(zip(["planning","implementation","quality","enablement"], TX["cats"]))
def t(x,y,s,size=14,fill=TXT,weight=400,font=SANS,anchor="start",extra=""):
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{escape(s)}</text>'
def inner(a):
    s = open(A + a + ".svg").read()
    return re.sub(r'^<svg[^>]*>|</svg>\s*$', '', s.strip())
def wrap(s, n=24):
    w, lines, cur = s.split(), [], ""
    for x in w:
        if len(cur) + len(x) + 1 > n and cur: lines.append(cur); cur = x
        else: cur = (cur + " " + x).strip()
    lines.append(cur); return lines[:2]
W, cols, gap, M = 1600, 7, 14, 40
cw = (W - 2*M - gap*(cols-1)) / cols; ch = 262
H = 170 + len(CATS)*(ch+62) + 30
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
 '<defs><radialGradient id="bg" cx="0.2" cy="0" r="1.1"><stop offset="0" stop-color="#1b2450"/><stop offset="1" stop-color="#0b1020"/></radialGradient>'
 '<linearGradient id="hdr" x1="0" x2="1"><stop offset="0" stop-color="#ef4444"/><stop offset="0.25" stop-color="#facc15"/><stop offset="0.5" stop-color="#22c55e"/><stop offset="0.75" stop-color="#3b82f6"/><stop offset="1" stop-color="#d946ef"/></linearGradient></defs>',
 f'<rect width="{W}" height="{H}" fill="url(#bg)"/>', t(M,72,TX["title"],34,TXT,800),
 f'<rect x="{M}" y="88" width="160" height="4" rx="2" fill="url(#hdr)"/>',
 t(M,120,TX["sub"].format(n=len(d)),17,MUTED)]
y = 160
for cat, title in CATS:
    agents = [a for a,v in d.items() if v["category"] == cat]
    o.append(t(M,y+24,title.upper(),13,MUTED,800,extra='letter-spacing="2"'))
    o.append(f'<line x1="{M+12+len(title)*10.5}" y1="{y+19}" x2="{W-M}" y2="{y+19}" stroke="{STROKE}"/>')
    cy = y + 42
    for i, a in enumerate(agents):
        v = d[a]; c = v["colors"]; x = M + i*(cw+gap)
        o.append(f'<rect x="{x}" y="{cy}" width="{cw}" height="{ch}" rx="16" fill="#121a2e" stroke="{STROKE}"/>')
        o.append(f'<rect x="{x}" y="{cy}" width="{cw}" height="{ch}" rx="16" fill="{c["base"]}" fill-opacity="0.06"/>')
        o.append(f'<g transform="translate({x+cw/2-46},{cy+22}) scale({92/64})">{inner(a)}</g>')
        lab = v["label"][LANG]
        o.append(t(x+cw/2,cy+142,lab,15.5 if len(lab)<20 else 14,TXT,700,anchor="middle"))
        o.append(t(x+cw/2,cy+162,a,10.5,c["light"],500,MONO,"middle"))
        for j, line in enumerate(wrap(v["description"][LANG])):
            o.append(t(x+cw/2,cy+190+j*17,line,12.5,MUTED,anchor="middle"))
        chip = f'{v["tier"]} · {v["model"]}'; w = len(chip)*6.8+22
        o.append(f'<rect x="{x+cw/2-w/2}" y="{cy+ch-40}" width="{w}" height="24" rx="12" fill="#0d1426" stroke="{c["light"]}" stroke-opacity="0.55"/>')
        o.append(t(x+cw/2,cy+ch-23.5,chip,11,c["light"],600,MONO,"middle"))
    y = cy + ch + 20
o.append("</svg>")
open(sys.argv[1],"w").write("\n".join(o))
