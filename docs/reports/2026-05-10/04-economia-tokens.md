# 04 — Economia de Tokens

← [Voltar ao índice](index.md) · [← Seção anterior](03-agentes-e-skills.md)

**Data:** 2026-05-10
**Escopo:** Quinta passada — skills extraídas mas inline mantido, current-context não consumido por commands, frase token-efficiency em 6 variantes, install.sh blocklist vs allowlist, gates de hook condicionais, CLAUDE.md monolítico.
**Anti-repetição:** Os 110 fingerprints publicados em 2026-05-06 / -07 / -08 / -09 foram excluídos.

---

## Sumário

A passada anterior (09) identificou padrões redundantes em prosa — Reviewer Mindset replicado, comments-policy monolítico, README bilingual, foundational rule não-tabular. Verificação atual mostra:

- **`comments-policy`** foi reduzido a 76 linhas (era 417 conforme fingerprint anterior) — economia já realizada.
- **Reviewer Mindset** foi extraído como skill (`skills/shared/reviewer-mindset/SKILL.md`, 19 linhas), mas **`code-reviewer.md` ainda mantém o bloco inline** + carrega a skill — duplo carregamento (ver suggestion #2 abaixo).
- **`current-context`** skill criada, mas comandos ainda inlinearam o bloco git em 21 lugares (ver suggestion #1).

**Esta passada identifica seis classes de redundância ainda não cobertas:**

1. **Skills extraídas com inline mantido nos consumidores** — `reviewer-mindset` é o caso emblemático.
2. **`current-context` skill não consumida** — 21 commands com bloco git inline duplicado.
3. **Variantes da frase `Apply token-efficiency`** — 6 redações ligeiramente diferentes em 10 agentes.
4. **`install.sh` strip por blocklist** — cada novo arquivo no repo exige decisão; allowlist é mais barato a longo prazo.
5. **Hooks rodam incondicionalmente** — `02-orphan-skill-scan.sh` roda a cada Stop sem mudança em `agents/`/`skills/`.
6. **`CLAUDE.md` é monolítico** — 270+ linhas carregadas a cada início de sessão.

---

## Sugestões

### 1. `current-context` skill existe mas 21 commands inlinearam o bloco git

**Fingerprint:** `token-current-context-skill-vs-21-inline-blocks`

**Evidência:**

```bash
$ wc -l skills/shared/current-context/SKILL.md
29 skills/shared/current-context/SKILL.md

$ grep -l "current-context" commands/*.md | wc -l
0

$ grep "git branch --show-current" commands/*.md | wc -l
21
```

Bloco inline duplicado em 21 commands (~7 linhas/cada):

```markdown
Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.dev-team-agents/.worktree-session` if present — active worktree

Restrict all analysis and actions to files and changes within this context. Do NOT scan or act on the full codebase unless $ARGUMENTS explicitly requests a broader scope.
```

Total redundante: **~147 linhas duplicadas** (21 × 7) + ~30 linhas de prosa de "scope rule" replicada.

Substituição em 21 commands por:

```markdown
Load `skills/shared/current-context/SKILL.md` to identify the current branch,
modified files, and worktree state before acting. Restrict all actions to the
detected scope unless $ARGUMENTS explicitly requests broader.
```

Economia: **~120 linhas raw** + **drift entre 21 cópias eliminado** + alinhamento com CLAUDE.md (já promete esse uso).

**Impacto positivo:**
- Economia direta de tokens em cada invocação de command;
- Centralização do protocolo de detecção;
- Permite evoluir current-context skill (ex.: adicionar branch-stale check da seção 02) sem 21 edições.

**Impacto negativo:**
- User lendo command isoladamente precisa abrir skill (mitigado: skill descritor é específico).

**Esforço:** Médio. Substituição mecânica via `sed`.

---

### 2. `reviewer-mindset` skill extraída mas `code-reviewer.md` mantém bloco inline E carrega skill

**Fingerprint:** `token-reviewer-mindset-extracted-but-inline-kept-with-double-load`

**Evidência:**

`agents/code-reviewer.md` linhas 10-22:

```markdown
## Reviewer Mindset

You approach every diff with the bias of a **critic who wants this code to survive production**...

- **Bugs first**: where does this code break? ...
- **Contract violations**: ...
- **Security**: ...
- **Test coverage**: ...
- **Readability**: ...
- **Silent failures**: ...
- **Architecture conformance**: ...

You are not a linter. You are asking: **will this code fail, corrupt data, or confuse the next engineer?**
```

E linha 54 do mesmo arquivo:

```markdown
12. Load `skills/shared/reviewer-mindset/SKILL.md` — the canonical reviewer mindset reference; the inline Reviewer Mindset section above is a summary; the skill is the authoritative cross-reference for all reviewer agents
```

Resultado: **ambos** (inline ~12 linhas + skill ~19 linhas) são carregados a cada invocação do agente. O comentário "the inline Reviewer Mindset section above is a summary" é honesto — mas a duplicação é exatamente o que extração de skill deveria eliminar.

Mesmo padrão em `backend-reviewer.md` e `frontend-reviewer.md`:

```bash
$ grep -c "Reviewer Mindset" agents/backend-reviewer.md
1
$ grep -c "Reviewer Mindset" agents/frontend-reviewer.md
1
```

Proposta: remover o bloco inline; manter só o load da skill. Trocar por:

```markdown
## Reviewer Mindset

Load `skills/shared/reviewer-mindset/SKILL.md` — the canonical reviewer mindset
applied to every diff: bugs first, contract violations, security, coverage,
readability, silent failures, architecture conformance.
```

Economia: **~36 linhas** (12 × 3 agentes) — exatamente o que a passada 09 estimava em `token-reviewer-mindset-block-duplicate`, mas com ângulo refinado: o problema persiste **mesmo após extração** porque o inline não foi removido.

**Impacto positivo:**
- Skill vira fonte única real;
- Edições futuras na mentalidade têm 1 lugar (skill);
- Padrão "extraí mas mantive inline" é anti-pattern; remoção sinaliza o caminho correto.

**Impacto negativo:**
- Leitor de `code-reviewer.md` precisa abrir a skill para entender o tom (mitigado: descritor "production-survival bias..." resolve em 1 linha).

**Esforço:** Trivial (3 deletions).

---

### 3. Frase `Apply skills/shared/token-efficiency/SKILL.md` em 6 variantes redacionais

**Fingerprint:** `token-token-efficiency-apply-line-six-variants`

**Evidência:**

10 agentes têm a linha; redações diferentes:

| Agente | Continuação após "Apply ... token-efficiency/SKILL.md" |
|--------|-------------------------------------------------------|
| `backend-developer` | when loading many project files during context loading — prefer `grep`/`head` over reading entire files. |
| `backend-reviewer` | — prefer `grep`/`head` over full-file reads; use `git diff` output directly. |
| `backend-test-specialist` | when reading many files during context loading or large existing test suites — prefer `grep`/`head` over reading entire files. |
| `code-reviewer` | when reading many files during review — prefer `grep`/`head` over full-file reads; use `git diff` output directly rather than re-reading changed files. |
| `database-specialist` | when reading many schema files, migrations, or query logs during context loading — prefer `grep`/`head` over reading entire files. |
| `devops-specialist` | when processing large Docker logs, CI/CD pipeline configs, or Terraform state files — prefer `head`/`grep` over reading entire files. |
| `frontend-developer` | when loading many project files during context loading — prefer `grep`/`head` over reading entire files. |
| `frontend-reviewer` | — prefer `grep`/`head` over full-file reads; use `git diff` output directly. |
| `frontend-test-specialist` | when reading many component files or large test suites during context loading — prefer `grep`/`head` over reading entire files. |
| `software-architect` | when loading multiple architecture documents or traversing a large codebase during analysis — prefer `grep`/`head` over reading entire files. |

6 redações sutilmente diferentes para a **mesma instrução**. Frase canônica única:

```markdown
Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over
full reads; filter before reading; summarize instead of dumping.
```

Tudo o mais (Docker logs, schema files, test suites) é responsabilidade do agente em runtime — não precisa estar na regra.

**Impacto positivo:**
- Economia: ~30-40 linhas (variações verbosas);
- Padrão único auditável por `agent-lint.sh`;
- Reduz ambiguidade ("essa é a versão A ou B?").

**Impacto negativo:**
- Perde sinalização "use isso especificamente quando você ler X" (mitigado: a skill já é orientada por casos).

**Esforço:** Baixo (substituição em 10 arquivos).

---

### 4. `install.sh` strip por blocklist (8 itens) — allowlist seria mais robusto

**Fingerprint:** `token-install-sh-blocklist-vs-allowlist`

**Evidência:**

`scripts/install.sh` linhas 128-136:

```bash
rm -rf "$EXTRACTED_ROOT/.claude"
rm -rf "$EXTRACTED_ROOT/docs"
rm -f "$EXTRACTED_ROOT/CLAUDE.md"
rm -f "$EXTRACTED_ROOT/README.md"
rm -f "$EXTRACTED_ROOT/README.pt-BR.md"
rm -f "$EXTRACTED_ROOT/.gitignore"
rm -f "$EXTRACTED_ROOT/scripts/install.sh"
rm -f "$EXTRACTED_ROOT/scripts/orphan-skill-scan.sh"
```

8 entradas que **listam o que NÃO ir para o instalador**. Cada novo arquivo no repo precisa de decisão: "vai entrar no tarball ou não?". E não passar o filtro = vazar para projetos de usuários.

Casos:
- Hoje `LICENSE` (adicionado em 09) é distribuído junto — ok;
- Se mañana surgir `SECURITY.md` (sugestão da seção 01), é OK distribuir? Sim, mas precisa pensar;
- Se surgir `.editorconfig` no root, deve ir? Provavelmente sim;
- Se surgir `pyproject.toml` para tooling local, deve ir? Não, mas blocklist não pega.

Allowlist inverte:

```bash
# Allowlist: only these top-level entries survive
KEEP_ROOT=("agents" "skills" "workflows" "templates" "commands" "scripts" "LICENSE")

for item in "$EXTRACTED_ROOT"/*; do
    name=$(basename "$item")
    keep=false
    for k in "${KEEP_ROOT[@]}"; do
        [ "$name" = "$k" ] && keep=true && break
    done
    [ "$keep" = false ] && rm -rf "$item"
done

# Then strip scripts that don't belong inside installations
rm -f "$EXTRACTED_ROOT/scripts/install.sh"
rm -f "$EXTRACTED_ROOT/scripts/orphan-skill-scan.sh"
```

**Impacto positivo:**
- Default seguro (novo arquivo top-level **não** vaza para users por descuido);
- Decisão explícita exigida para incluir;
- Documenta o "shape" canônico de uma instalação.

**Impacto negativo:**
- Pode bloquear arquivos legítimos novos por esquecimento de adicionar à allowlist (mitigado: lista é curta e estável);
- Refactor do installer com risco se mal testado.

**Esforço:** Médio (refactor + teste).

---

### 5. `02-orphan-skill-scan.sh` roda a cada Stop hook independente de mudança em agents/skills

**Fingerprint:** `token-stop-hook-orphan-scan-unconditional-rerun`

**Evidência:**

`scripts/hooks/stop/02-orphan-skill-scan.sh`:

```bash
exec "$(dirname "${BASH_SOURCE[0]}")/../../orphan-skill-scan.sh" --quiet "$@"
```

Roda toda vez que o Stop hook dispara. Mas:

- Se o usuário rodou só uma sessão de "explicar código" e não tocou `agents/` ou `skills/` → scan inútil;
- Em sessões longas com vários Stops (e.g., interrupções de plan mode), reroda o mesmo trabalho.

Gate proposto:

```bash
#!/usr/bin/env bash
# 02-orphan-skill-scan.sh — gate by recent changes in agents/ or skills/
TOUCHED=$(git status --porcelain agents/ skills/ 2>/dev/null | head -1)
TODAY_COMMITS=$(git log --since="$(date +%Y-%m-%d) 00:00:00" --oneline -- agents/ skills/ 2>/dev/null | head -1)

if [ -z "$TOUCHED" ] && [ -z "$TODAY_COMMITS" ]; then
    exit 0  # nothing changed in scope; skip scan
fi

exec "$(dirname "${BASH_SOURCE[0]}")/../../orphan-skill-scan.sh" --quiet "$@"
```

Mesmo padrão aplicável a `03-agent-lint.sh` (gate por mudança em `agents/`).

**Impacto positivo:**
- Reduz overhead em sessões que não tocaram o repositório;
- Especialmente útil em CI quando rodado em forks/sessões de leitura;
- Mantém o safety-net (se houve mudança, ainda checa).

**Impacto negativo:**
- Sutileza extra; risco de bug "scan não rodou porque eu mudei coisa via outro caminho";
- Beneficiado é tempo de wall-clock (~100-300ms); ganho marginal.

**Esforço:** Baixo.

---

### 6. `CLAUDE.md` (272+ linhas) carregado a cada início de sessão

**Fingerprint:** `token-claude-md-monolithic-load-every-session`

**Evidência:**

```bash
$ wc -l CLAUDE.md
272 CLAUDE.md
```

O arquivo contém:
- Authoring standards para agents (~30 linhas);
- Authoring standards para skills (~25 linhas);
- Workflows authoring (~10 linhas);
- Templates authoring (~5 linhas);
- Scripts authoring (~10 linhas);
- File structure (~20 linhas);
- User data directory (~30 linhas);
- Versioning (~5 linhas);
- Immutability contract (~5 linhas);
- Memory system (session-summary, ADR, Stop hook) (~50 linhas);
- Commit rule (~10 linhas);
- Orphan skill scan (~10 linhas);
- Setup trigger (~10 linhas);
- Coexistence rule (~5 linhas).

Todos esses são lidos por **toda invocação de qualquer agente** no contexto do repo. Mas:

- Agente coding (`backend-developer`) não precisa de "Skill authoring standards";
- Agente review (`code-reviewer`) não precisa de "Workflows authoring";
- Apenas o setup do repo (humanos contribuindo) precisa de "Authoring standards".

Proposta: split em `CLAUDE.md` (curto, regras universais) + `.claude-md/<topic>.md` carregados sob demanda:

```
CLAUDE.md                          ← 30-50 linhas: coexistence, language, plan mode, immutability, link p/ módulos
.claude-md/authoring-agents.md     ← carregado por agente-creator e contribuintes
.claude-md/authoring-skills.md     ← idem
.claude-md/memory-system.md        ← carregado por agentes que escrevem session-summary
.claude-md/commands-and-workflows.md  ← carregado por workflows criadores
```

Padrão "load on demand" já usado por skills (progressive disclosure). Aplicar ao próprio CLAUDE.md.

**Impacto positivo:**
- Economia: ~200 linhas tipicamente não usadas por sessão;
- Setup-assistant + agente-creator carregam o necessário;
- Permite evoluir cada área isoladamente.

**Impacto negativo:**
- Quebra padrão "CLAUDE.md é a fonte de verdade" — agora há múltiplos CLAUDE-flavored;
- Sincronia entre módulos exige disciplina (mitigado: links explícitos);
- Refactor não-trivial; risco de quebrar carregamento existente.

**Esforço:** Alto. **Prioridade:** P3 (longo prazo).

---

### 7. CI usa `apt-get install shellcheck` (sem cache)

**Fingerprint:** `token-ci-shellcheck-no-binary-cache`

**Evidência:**

`.github/workflows/ci.yml` linhas 24-26:

```yaml
- name: Shellcheck scripts
  run: |
    sudo apt-get install -y shellcheck
    find scripts -name '*.sh' -exec shellcheck {} +
```

`apt-get install` no GitHub-hosted runner usa o cache do Ubuntu repository — mas requer round-trip de rede (5-10s por run). Alternativas:

```yaml
- uses: ludeeus/action-shellcheck@2.0.0
```

ou usar a versão pré-instalada do runner (`/usr/bin/shellcheck` existe em `ubuntu-latest`).

**Impacto positivo:**
- ~5-10s economizados por run;
- Reduz dependência de mirror Ubuntu;
- Idempotência: action pode pin de versão.

**Impacto negativo:**
- Action externo introduz dependência terceira (mitigado: pin de version).

**Esforço:** Trivial.

---

### 8. Pre-tool-use `01-check-updates.sh` faz HTTP a cada 24h sem ETag/If-Modified-Since

**Fingerprint:** `token-update-check-no-etag-handling`

**Evidência:**

`scripts/hooks/pre-tool-use/01-check-updates.sh` linhas 31-32:

```bash
HTTP_GET() { curl -fsSL --connect-timeout 5 --max-time 10 "$1"; }
```

Faz GET completo na GitHub Releases API a cada 24h. GitHub responde com cache-control + ETag, mas o script não envia `If-None-Match` para receber `304 Not Modified` quando nada mudou.

Para um projeto que faz releases relativamente raros (1-2 / mês), 28-30 das ~30 chamadas mensais por user resultam em payload duplicado.

Proposta:

```bash
ETAG_FILE="$USER_DATA_DIR/.last-releases-etag"
if [ -f "$ETAG_FILE" ]; then
    ETAG=$(cat "$ETAG_FILE")
    RESP=$(curl -fsSL --connect-timeout 5 --max-time 10 \
        -H "If-None-Match: $ETAG" -w "%{http_code}" -o /tmp/releases.json \
        "${GITHUB_API}/releases/latest")
    [ "$RESP" = "304" ] && exit 0
fi

# else: full request + persist new ETag
curl -fsSL ... -D /tmp/headers.txt -o /tmp/releases.json "$URL"
grep -i "^etag:" /tmp/headers.txt | sed 's/^[Ee]tag: //I' > "$ETAG_FILE"
```

**Impacto positivo:**
- Reduz banda em ~90% para users em latest;
- GitHub não conta `304` contra rate-limit;
- Boa cidadania técnica (HTTP correto).

**Impacto negativo:**
- Adiciona arquivo de estado (`.last-releases-etag`);
- Curl com `-w "%{http_code}"` complica o script.

**Esforço:** Baixo-Médio.

---

## Resumo dos Fingerprints

| # | Fingerprint | Economia (linhas / requests / wall-clock) | Esforço |
|---|------------|--------------------------------------------|---------|
| 1 | `token-current-context-skill-vs-21-inline-blocks` | ~120 linhas + drift | Médio |
| 2 | `token-reviewer-mindset-extracted-but-inline-kept-with-double-load` | ~36 linhas + duplo load | Trivial |
| 3 | `token-token-efficiency-apply-line-six-variants` | ~30-40 linhas | Baixo |
| 4 | `token-install-sh-blocklist-vs-allowlist` | Robustez de longo prazo | Médio |
| 5 | `token-stop-hook-orphan-scan-unconditional-rerun` | ~100-300ms / sessão | Baixo |
| 6 | `token-claude-md-monolithic-load-every-session` | ~200 linhas / sessão | Alto (P3) |
| 7 | `token-ci-shellcheck-no-binary-cache` | ~5-10s / CI run | Trivial |
| 8 | `token-update-check-no-etag-handling` | ~90% banda / hook | Baixo-Médio |

---

← [Seção anterior](03-agentes-e-skills.md) · [Voltar ao índice](index.md)
