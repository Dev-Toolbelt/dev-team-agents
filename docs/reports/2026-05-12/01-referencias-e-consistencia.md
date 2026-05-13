# Relatório — Referências e Consistência (2026-05-12)

Auditoria focada em **referências quebradas/órfãs, drift declarativo, e inconsistências estruturais** detectadas hoje (segunda-feira). Todas as sugestões abaixo são **originais** — não constam previamente no `_index.md` em formato idêntico. Quando há sobreposição parcial com fingerprint anterior, o novo escopo é especificado.

> **Contexto:** auditoria executada após o batch de 11 commits entre `b9c8b44` (publicação dos relatórios de 2026-05-11) e `c3b8db2` (HEAD em 2026-05-12). Foco especial em **drifts criados pela própria implementação dos commits do dia anterior** (especialmente a extração de docs/agents.md e docs/installation.md).

---

## 1. `docs-sync-extracted-docs-not-translated-to-pt-br`

**Severidade:** 🟡 Média

**Detecção:** Commit `7800516` extraiu `docs/agents.md` (6714 bytes) e `docs/installation.md` (5723 bytes) do README.md, **mas não criou versões em pt-BR**. README.pt-BR.md linha 17 e bloco "Opções avançadas" delegam para os mesmos paths em inglês:

```
README.pt-BR.md:17 → "Veja a [Referência de Agentes](docs/agents.md)"
README.pt-BR.md → "Opções avançadas […]: [docs/installation.md](docs/installation.md)"
```

**Impacto positivo (se corrigido):** restaura a regra de sincronia pt-BR estabelecida em `CLAUDE.md:15-24` ("README Sync Rule"), e permite que usuários brasileiros tenham documentação completa de instalação/agents.

**Impacto negativo (se mantido):** README.pt-BR.md hoje é uma "casca" — links principais (referência de agents, opções avançadas de instalação) apontam para conteúdo só em inglês. CI atual (`README sync check`) **não detecta** este drift porque só compara line-count entre README.md ↔ README.pt-BR.md, não dos derivados.

**Sugestão:** criar `docs/agents.pt-BR.md` e `docs/installation.pt-BR.md`; estender o `README sync check` no CI para verificar pares de arquivos em `docs/`.

---

## 2. `ref-jira-skill-over-500-line-hard-limit`

**Severidade:** 🟠 Alta — viola limite explícito do CLAUDE.md

**Detecção:** `wc -l skills/integrations/jira/SKILL.md` retorna **516 linhas**. `CLAUDE.md:139` declara: _"Max ~500 lines; move long reference material to `references/` subdirectory"_. A skill `jira` excede o limite, e a pasta `skills/integrations/jira/references/` **não existe**.

**Impacto positivo (se corrigido):** restaura conformidade com o próprio CLAUDE.md; reduz token cost quando carregada por qa-specialist, code-reviewer e product-analyst (3 agents).

**Impacto negativo (se mantido):** precedente para outras skills "esticarem" acima do limite sem consequência; agent-lint não valida tamanho de skill (só agent frontmatter).

**Sugestão:** mover REST API endpoints, JQL syntax reference e webhook payloads para `skills/integrations/jira/references/{rest-api.md,jql.md,webhooks.md}`.

---

## 3. `ref-large-skills-no-references-subdir-pattern-not-adopted`

**Severidade:** 🟡 Média

**Detecção:** 5 skills excedem 300 linhas mas **não usam o padrão `references/` subdir**:

| Skill | Linhas | references/ |
|-------|--------|-------------|
| `skills/integrations/jira/SKILL.md` | 516 | ❌ |
| `skills/devops/monitoring/SKILL.md` | 444 | ✅ (vazia) |
| `skills/devops/sonarqube/SKILL.md` | 435 | ❌ |
| `skills/devops/sentry/SKILL.md` | 368 | ❌ |
| `skills/shared/docs-sync/SKILL.md` | 351 | ❌ |
| `skills/devops/cloudflare/SKILL.md` | 343 | ❌ |
| `skills/devops/iac-terraform/SKILL.md` | 306 | ❌ |

**Padrão atual no repo:** apenas 2 skills usam `references/` — `monitoring` (vazia) e `comments-policy`. O padrão **existe mas é exceção**, não regra.

**Impacto positivo (se corrigido):** redução estimada de ~1.500 linhas inline em skills carregadas no startup; pasta `references/` é **lazy-loaded** apenas quando o agente precisa do detalhe.

**Impacto negativo (se mantido):** skills grandes continuam carregando completamente no contexto mesmo quando o agente só precisa do trigger top-level.

---

## 4. `ref-design-skills-non-standard-frontmatter-keys`

**Severidade:** 🟡 Média — viola CLAUDE.md explícito

**Detecção:** `CLAUDE.md:130-135` declara apenas `name` e `description` como chaves canônicas de skill frontmatter (e nota que `allowed-tools:` foi removido do `worktree`). Porém:

```yaml
# skills/design/web-design-guidelines/SKILL.md
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>

# skills/design/frontend-design/SKILL.md
license: Complete terms in LICENSE
```

Ambas violam o padrão.

**Impacto positivo (se corrigido):** consistência total nas 99 skills; `agent-lint.sh` poderia ser estendido para validar isso (novo lint rule `skill-frontmatter-strict`).

**Impacto negativo (se mantido):** consumidor automatizado (parser, IDE plugin futuro) não tem garantia de schema estável.

**Sugestão:** ou (a) remover chaves extras e mover info para body (ex.: rodapé), ou (b) atualizar CLAUDE.md para permitir chaves opcionais documentadas.

---

## 5. `ref-tools-frontmatter-ordering-divergence-reviewers-vs-coders`

**Severidade:** 🟢 Baixa (cosmético, mas mensurável)

**Detecção:** Ordenação dos `tools:` diverge sistematicamente entre famílias de agents:

| Família | Pattern |
|---------|---------|
| Coding agents (backend-developer, frontend-developer, mobile-developer, database, devops, test-specialists, ui-ux, qa, setup, technical-writer) | `Read, Write, Edit, Bash, Glob, Grep` |
| Reviewer agents (code-reviewer, backend-reviewer, frontend-reviewer) | `Read, Grep, Glob, Bash` |
| Outliers | `product-analyst` (+ WebSearch), `software-architect` (+ WebSearch), `security-specialist` (sem Write/Edit, + WebSearch) |

**Impacto positivo (se corrigido):** padronizar ordering facilita lint automatizado (`agent-lint.sh` poderia validar canonical order), e ajuda quando humano busca tools across agents.

**Impacto negativo (se mantido):** ordenação inconsistente sugere falta de validação automatizada; novo agent pode importar qualquer ordem.

**Sugestão:** definir canonical order (ex.: alphabetical, ou por categoria: read-tools → write-tools → exec-tools), adicionar regra ao `agent-lint.sh`.

---

## 6. `ref-security-specialist-tools-lack-write-edit-vs-report-generation-mismatch`

**Severidade:** 🟡 Média

**Detecção:** `agents/security-specialist.md` frontmatter: `tools: Read, Grep, Glob, Bash, WebSearch`. **Sem Write/Edit.** Porém:
- O agente carrega `skills/security/iso27001-sgsi/SKILL.md` e `skills/security/security-checklist/SKILL.md` que pedem geração de relatórios SAST/audit
- Workflow `security-patch.md` Step 4 pede output formal (recomendação de patch)
- Bash habilitado permite criar arquivo via `cat >`, mas isso é workaround do gap

**Impacto positivo (se corrigido com Write):** alinha o tooling com o output esperado; remove dependência de bash heredoc para artefatos.

**Impacto positivo (se mantido sem Write, mas justificado):** força o security-specialist a delegar emissão de artefatos a technical-writer — design conscious de separação de responsabilidades.

**Impacto negativo (se mantido):** ambiguidade sobre se o agent pode mesmo escrever; novos contribuidores podem inferir capacidades errado.

**Sugestão:** decidir e documentar — adicionar Write/Edit OU adicionar comentário no agent frontmatter explicando o porquê do read-only.

---

## 7. `ref-ci-yml-no-skill-size-limit-validation`

**Severidade:** 🟡 Média

**Detecção:** `.github/workflows/ci.yml` valida hoje:
- `agent-lint.sh` (frontmatter de agents)
- `orphan-skill-scan.sh` (skills órfãs/broken refs em agents)
- `shellcheck` (scripts)
- README sync check (5% threshold)

**Não valida:**
- Tamanho de skill (limit ~500 linhas do CLAUDE.md)
- Tamanho de agent (limit ~200 linhas do CLAUDE.md)
- Skill frontmatter (apenas `name`/`description` permitidos)
- Refs em `commands/` ou `workflows/` (escopo restrito a `agents/`)

**Impacto positivo (se corrigido):** CI passa a regressionar quando alguém esticar uma skill/agent além do limite, em vez de só detectarmos em audits manuais.

**Impacto negativo (se mantido):** as 5 violações ativas (jira 516, monitoring 444, sonarqube 435, setup-assistant 306-agent, etc.) provavelmente já passaram por PRs no passado sem alerta.

**Sugestão:** criar `scripts/size-limits.sh` (executado pelo CI) que percorra `agents/` e `skills/` e falhe quando exceder os limites declarados em CLAUDE.md.

---

## 8. `ref-claude-md-file-structure-misses-new-docs-children`

**Severidade:** 🟡 Média

**Detecção:** Após a extração do commit `7800516`, `docs/` agora contém:
```
docs/
├── agents.md         ← novo (extraído do README)
├── installation.md   ← novo (extraído do README)
└── reports/
    └── _index.md
```

**Mas o bloco "File Structure" em `CLAUDE.md:182-203` lista apenas:**
```
├── docs/            ← repository-level reports and internal docs
```

Sem subdivisão. Os dois novos arquivos canônicos (referência de agents + guia de instalação) ficam invisíveis na tree declarativa.

**Impacto positivo (se corrigido):** novos contribuidores descobrem `docs/agents.md` (canonical reference) pelo CLAUDE.md, em vez de só pelo README.

**Impacto negativo (se mantido):** crescimento futuro de `docs/` (ex.: `docs/architecture.md`, `docs/troubleshooting.md`) tenderá a continuar invisível.

---

## 9. `ref-changelog-package-exclusions-update-not-documented-in-unreleased`

**Severidade:** 🟢 Baixa

**Detecção:** Commit `09c00ca` expandiu a tabela "Package exclusions" em CLAUDE.md (de 8 para 14 linhas — adição de LICENSE, CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, docs/, separação de coluna Mechanism). **Esta mudança não foi documentada na seção `[Unreleased]` do CHANGELOG**, apesar de ser uma mudança observável de comportamento (regra de empacotamento).

**Impacto positivo (se corrigido):** rastreabilidade total das decisões de empacotamento; usuários consultando CHANGELOG entendem por que o install.sh ignora certos arquivos.

**Impacto negativo (se mantido):** padrão de "mudanças em CLAUDE.md ficam fora do CHANGELOG" tende a se consolidar (e o próprio CLAUDE.md tem auto-docs rule que **exige** sincronia).

---

## 10. `ref-claude-md-immutability-contract-vs-actual-symlinks-rule-drift`

**Severidade:** 🟢 Baixa

**Detecção:** `CLAUDE.md:213-219` ("Immutability Contract") afirma: _"These files are installed via symlinks into user projects."_ Porém o `install.sh` atual **não cria symlinks** — usa `mv` para colocar o tarball extraído em `.claude/dev-team-agents/`. A relação é por caminho fixo, não simbólica.

```bash
# scripts/install.sh — fluxo real
curl … → /tmp/devteam-*.tar.gz → tar -xzf → mv $TMP $INSTALL_DIR
```

**Impacto positivo (se corrigido):** texto do CLAUDE.md descreve fielmente o mecanismo; remove confusão para contribuidores tentando entender o "como" da instalação.

**Impacto negativo (se mantido):** documentação contradiz o código; futuros mantenedores podem fazer pull requests baseados na premissa errada (ex.: "vou usar `readlink` para…").

**Sugestão:** alterar para _"These files are installed at a fixed path (`.claude/dev-team-agents/`) and replaced entirely on every update. Users are warned not to modify them directly."_

---

## 11. `ref-orphan-scan-covers-agents-only-but-skills-may-be-loaded-only-by-commands`

**Severidade:** 🟡 Média — variante de fingerprint pendente

**Detecção:** Sub-escopo específico do antigo `ref-orphan-scan-only-checks-agents-not-commands-or-workflows` (2026-05-11, pendente): **2 skills hoje são carregadas exclusivamente por commands**, não por agents:

| Skill | Carregada por | Carregada por agent? |
|-------|---------------|--------------------|
| `skills/shared/current-context/SKILL.md` | 23 de 25 commands | ❌ (zero agents) |
| `skills/shared/spawn-classifier/SKILL.md` | apenas `commands/plan.md` | ❌ (zero agents) |

Ambas estão registradas na seção "Command-level skills" do CLAUDE.md (linhas 119-123) para evitar serem flagadas como órfãs. **Solução atual é uma exceção de allowlist**, não detecção real. Quando uma nova skill command-level for criada e o autor esquecer de adicionar à tabela, ela será flagada como órfã (falso positivo).

**Impacto positivo (se corrigido):** detecção real cobrindo `agents/`, `commands/` e `workflows/`; elimina a necessidade de tabela manual de exclusão.

**Impacto negativo (se mantido):** manutenção manual da tabela; risco de falso positivo no Stop hook.

---

## 12. `ref-package-exclusions-table-mechanism-column-overlap-with-install-sh-comments`

**Severidade:** 🟢 Baixa

**Detecção:** A tabela "Package exclusions" em CLAUDE.md agora tem 3 colunas (path, Mechanism, Reason). Porém, `install.sh` em si **não tem comentários inline** mapeando cada `rm -f` para a justificativa correspondente. A "Reason" mora apenas no CLAUDE.md.

```bash
# install.sh — sem comment ligando a CLAUDE.md
rm -rf "$EXTRACT_DIR/.claude"   # ← qual reason? leitor precisa abrir CLAUDE.md
rm -f "$EXTRACT_DIR/scripts/install.sh"
```

**Impacto positivo (se corrigido):** comentário inline (ex.: `# allowlist via KEEP_ROOT — see CLAUDE.md "Package exclusions"`) fecha o loop sem duplicar a tabela.

**Impacto negativo (se mantido):** quem está debugando o install.sh em produção precisa abrir CLAUDE.md para entender por que um arquivo é excluído.

---

## Resumo

| Severidade | Quantidade |
|------------|-----------|
| 🟠 Alta (viola regra explícita) | 1 |
| 🟡 Média | 7 |
| 🟢 Baixa | 4 |
| **Total** | **12** |

**Top 3 prioridades sugeridas para o próximo ciclo de implementação:**

1. `ref-jira-skill-over-500-line-hard-limit` — viola limite explícito do CLAUDE.md (`#3` reforça com 5 outras skills no mesmo padrão).
2. `docs-sync-extracted-docs-not-translated-to-pt-br` — README.pt-BR linka para arquivos só em inglês; quebra a "README Sync Rule".
3. `ref-ci-yml-no-skill-size-limit-validation` — previne regressões futuras desta classe de problema (size limits).
