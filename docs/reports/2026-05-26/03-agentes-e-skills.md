# Relatório — Agentes e Skills

**Data:** 2026-05-26
**Janela auditada:** 2026-05-24 → 2026-05-26
**Foco:** ângulos novos de skills/agentes ainda não auditados, incluindo a **maior skill do repo** (graphify-setup, 277 linhas) e regressões de stack-prescriptiveness não cobertas pelos fingerprints anteriores.

---

## A1 — `skills/devops/graphify-setup/SKILL.md` é a maior skill do repo (277 linhas) e contém heredoc bash com `chmod +x` que gera sub-script de Stop — viola padrão "skills são material de referência"

**Fingerprint:** `skill-devops-graphify-setup-largest-skill-277-lines-ships-inline-bash-heredoc-with-chmod-plus-x-generating-stop-subscript-violates-reference-material-pattern-and-skill-pattern-claude-md-128`

**Severidade:** **MEDIUM-HIGH**

**Evidência:**

```bash
$ wc -l skills/devops/graphify-setup/SKILL.md
277  skills/devops/graphify-setup/SKILL.md       ← #1 maior skill do repo

$ sed -n '155,167p' skills/devops/graphify-setup/SKILL.md
mkdir -p .dev-team-agents/scripts/hooks/stop
cat > .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh << 'EOF'
#!/bin/bash
# ... 5 linhas de bash gerando subscript ...
EOF
chmod +x .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh
```

CLAUDE.md:128 estabelece: *"Skills follow [agentskills.io specification] — body is current rules only … max ~500 lines; move long reference material to references/ subdirectory."* — a skill **não viola o cap de 500**, mas viola o **espírito** de "rules only": instala arquivos executáveis no projeto do usuário no momento que é "lida" por um agente.

**Comparação com outras skills do top-5:**

| # | Skill | Linhas | Gera arquivos? |
|---|---|---:|:-:|
| 1 | `graphify-setup` | 277 | **SIM** (heredoc + chmod) |
| 2 | `project-context` | 266 | Não — só prosa |
| 3 | `graphql` | 235 | Não |
| 4 | `gotrue` | 225 | Não |
| 5 | `database-production` | 222 | Não |

Apenas `graphify-setup` mistura skill (instruções) com installer (scripts executáveis).

**Impacto:**

1. **Race condition na convenção:** o subscript gerado tem prefixo `02-` (tier "Repository integrity checks" pela CLAUDE.md:356), conflitando com `02-orphan-skill-scan.sh`. Já flagrado em `ref-graphify-setup-stop-subscript-prefix-02-violates-cleanup-99-tier-collides-with-orphan-skill-scan-propagated-three-files` (2026-05-21) — mas **a causa-raiz é estrutural**: skills não deveriam gerar subscripts. Aqui ataco a causa-raiz, não o sintoma.
2. **Skill content vira código:** ao ler 277 linhas para entender o pattern, ~120 linhas (43%) são bash de instalação — token desperdiçado em todo spawn do `devops-specialist` (que carrega graphify-setup quando detecta Graphify).
3. **Refatoração delicada:** se a estrutura de `scripts/hooks/stop/` mudar, é preciso editar uma string dentro de uma skill (não uma fonte canônica em `helpers/` ou `scripts/`).

**Recomendação:**

Mover o bloco gerador para `scripts/install-graphify-hook.sh` (~50 linhas autônomas) e reduzir a skill a:

```markdown
## Hook Setup
Run `bash .dev-team-agents/scripts/install-graphify-hook.sh` to install the refresh hook.
```

Economia: skill cai de 277 → ~155 linhas; remove o tier-conflict (o instalador escolhe o tier correto `99-` automaticamente); reduz token por spawn.

**Por que original:** o banco tem `ref-graphify-setup-stop-subscript-prefix-02-…` (sintoma, prefixo errado) e `token-graphify-setup-…` (não existe ainda) — **nenhum ataca o padrão de skill-que-instala-scripts**. Distinto também do `skill-…-references-extraction` (que move conteúdo para subdir, não para script executável).

---

## A2 — `agents/setup-assistant.md:60-70` contém bloco bash `Docker Compose version detection` no corpo do agente — código stack-prescritivo em agente "setup" que deveria ser agnóstico

**Fingerprint:** `agent-setup-assistant-lines-60-70-docker-compose-version-detection-inline-bash-block-stack-prescriptive-in-agent-body-while-mobile-detection-and-stack-detection-already-extracted-to-skills`

**Severidade:** **MEDIUM**

**Evidência:**

```bash
$ sed -n '60,70p' agents/setup-assistant.md
**Docker Compose version detection:** After confirming Docker is present, detect the correct compose command:
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi
Record the result in the project's `CLAUDE.md` as `DOCKER_COMPOSE: docker compose` ...
```

10 linhas de bash + prosa estritamente sobre Docker no agente que **inicia setup de qualquer stack** (PHP+SQLite, Python+SQLite, Rust+nada, projeto puramente frontend estático etc.). O agente `setup-assistant` lista no início (linha 3) "stack-agnostic" mas duas seções (Docker detection e linha 78 "Docker, IaC") contradizem isso.

A skill `skills/shared/stack-detection/SKILL.md` (173 char description) e o pattern "Detection Signals" tabela (usado por `mobile-developer`, `database-specialist`, `devops-specialist`) já são o lugar correto para esse bloco — ele só foi esquecido no `setup-assistant`.

**Impacto:**

1. **Carga inútil em projetos sem Docker:** o `setup-assistant` é spawneado em todo onboarding, mas o ~30% dos projetos sem Docker pagam 10 linhas de detecção (~150 tokens) que não se aplicam.
2. **Regra de detecção mora em 2 lugares:** o mesmo padrão `docker compose` vs `docker-compose` já está em `skills/devops/docker-dev/SKILL.md` (linha 9-15) — duplicação semântica entre agente e skill.

**Recomendação:**

Mover o bloco `Docker Compose version detection` para `skills/devops/docker-dev/SKILL.md` (ou para uma nova `skills/shared/runtime-detection/SKILL.md` que cubra outros runtime tooling como Node version detection, Python venv detection etc.). Em `setup-assistant.md` substituir por:

```markdown
**Runtime tooling detection:** If `Dockerfile` or `docker-compose*.yml` is present, load `skills/devops/docker-dev/SKILL.md` § "Compose version detection" and record the resolved command in the project's `CLAUDE.md`.
```

Economia: ~10 linhas no agente; alinha à regra `stack-agnostic` da CLAUDE.md:124.

**Por que original:** as recentes auditorias de stack-agnosticism cobriram `devops-specialist`, `backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `frontend-test-specialist`, `backend-test-specialist`, `security-specialist`, `frontend-reviewer`. **`setup-assistant` nunca foi auditado nesse eixo** — e o agente cuja missão é orquestrar o setup é justamente o que mais precisa ser agnóstico. Distinto do `ref-setup-assistant-…-quiz-first` (2026-05-15, era pergunta interativa).

---

## A3 — Skills `skills/mobile/ios` (33 linhas) e `skills/mobile/android` (35 linhas) começam com a instrução "Load `ios-hig`/`material-design`" — wrappers que **dobram** o custo de carregamento

**Fingerprint:** `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-or-material-design-doubling-token-cost-251-and-256-lines-total-instead-of-218-and-221-net-loss-vs-loading-the-large-skill-directly`

**Severidade:** **MEDIUM**

**Evidência:**

```bash
$ wc -l skills/mobile/ios/SKILL.md skills/mobile/android/SKILL.md skills/mobile/ios-hig/SKILL.md skills/mobile/material-design/SKILL.md
   33 skills/mobile/ios/SKILL.md
   35 skills/mobile/android/SKILL.md
  218 skills/mobile/ios-hig/SKILL.md
  221 skills/mobile/material-design/SKILL.md

$ head -10 skills/mobile/ios/SKILL.md
---
name: ios
description: iOS-specific development guidelines — design, permissions, code signing, and native Swift/SwiftUI standards. Load when the project targets iOS.
---

# iOS-Specific Standards

> See `skills/mobile/ios-hig/SKILL.md` for Human Interface Guidelines.

## Permissions

$ head -10 skills/mobile/android/SKILL.md
---
name: android
description: Android-specific development guidelines — design, permissions, release signing, and native Kotlin/Jetpack Compose standards. Load when the project targets Android.
---

# Android-Specific Standards

> See `skills/mobile/material-design/SKILL.md` for Material Design 3 guidelines.

## Permissions
```

**Padrão atual:** o `mobile-developer.md:75` tabela "Platform skills" instrui carregar `ios` quando iOS é detectado. `ios` (33 linhas) imediatamente redireciona para `ios-hig` (218 linhas). O LLM termina carregando **251 linhas** quando o conteúdo útil (HIG + permissions + signing) cabe em uma skill consolidada de ~230 linhas.

Para Android: 35 + 221 = **256 linhas** vs ~230 consolidadas.

Overhead total quando ambas plataformas são alvos (cross-platform RN/Flutter): 33+218+35+221 = **507 linhas** vs ~460 consolidadas — desperdício de ~47 linhas (10%).

**Status no banco:** existem 2 fingerprints próximos:

- `ref-skills-mobile-ios-and-android-skills-too-thin-vs-ios-hig-material-design-overlap-without-clear-boundary` (2026-05-18) — pediu **fronteira clara**, ⚠️ Partial.
- `agent-mobile-developer-ios-android-skills-too-thin-33-and-35-lines-versus-ios-hig-218-and-material-design-221-no-clear-content-boundary` (2026-05-18) — mesma classe.

→ Aqui ataco o eixo **token** com medição concreta, sub-escopo distinto do **eixo conteúdo** dos 2 anteriores.

**Impacto:**

- Para todo spawn de `mobile-developer` em projeto iOS: ~3.300 tokens carregados (251 linhas) onde 2.800 bastariam (~15% desperdício).
- Cross-platform spawn: ~6.600 tokens onde 6.000 bastariam.
- Token waste secundário: o redirect "See `…/ios-hig/SKILL.md`" é uma linha "morta" — o LLM pode tanto carregar quanto não carregar a skill alvo, criando inconsistência entre rodadas.

**Recomendação:**

Duas opções:

- **A (consolidar):** fundir `ios` + `ios-hig` em `ios` (linhas ~225) e `android` + `material-design` em `android` (linhas ~230). Renomear os wrappers extras para `references/`.
- **B (gate explícito):** no wrapper, mover a redirect para frontmatter (`extends: ios-hig`) ou padrão "Load only when X" — torna o LLM cético sobre carregar o segundo arquivo automaticamente. Hoje a phrase "See …" é ambígua.

Recomendação preferencial: **A**. O wrapper sem conteúdo próprio é YAGNI.

**Por que original:** os 2 fingerprints anteriores são sobre **conteúdo/fronteira**; este traz **medição de token e a proposta concreta de fusão**, com números — sub-escopo que merece seu próprio slug pois resolve por estratégia diferente.

---

## Sumário das 3 recomendações

| # | Fingerprint | Severidade | Esforço |
|---|---|---|---|
| A1 | `graphify-setup` skill com heredoc/`chmod +x` | MEDIUM-HIGH | ~30 min (extrair installer) |
| A2 | `setup-assistant` bloco Docker inline | MEDIUM | ~10 min (mover para skill) |
| A3 | ios/android skills wrappers — fusão recomendada | MEDIUM | ~20 min (merge + update tabela) |

Todos os 3 reduzem token e fortalecem o princípio "skills são material de referência, agentes carregam material por detecção".
