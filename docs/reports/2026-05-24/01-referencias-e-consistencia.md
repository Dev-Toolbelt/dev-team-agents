# Referências e Consistência — 2026-05-24

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 493 fingerprints (`_index.md`) e são inéditas.

---

## R1 — O conteúdo do sistema de notificação está **triplicado** em três arquivos sem fonte única de verdade — e já **derivou**: a tabela de convenção de sub-scripts do `CLAUDE-md/notifications.md` omite o tier `05-` (telemetria) que a `CLAUDE.md` canônica tem

**Severidade:** MEDIUM
**Fingerprint:** `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md-stop-subscript-table-already-drifted-omitting-05-telemetry`

**Evidência** — o mesmo material (formato, tipos, supressão, 15 tips, convenção de prefixos) vive em três lugares:

```
scripts/hooks/stop/04-notifier.sh      → implementação: formato + TIPS_EN/PTBR/ES (15×3) inline (240 linhas)
skills/shared/notifier/SKILL.md        → formato + tipos + supressão + tabela de 15 tips (131 linhas)
CLAUDE-md/notifications.md             → formato + tipos + canais + estimativa + tip-of-session + convenção (58 linhas)
```

A deriva já aconteceu. A tabela "Stop Sub-script Convention (updated)" do `CLAUDE-md/notifications.md:49-57` lista apenas `01- / 02- / 03- / 04- / 99-`:

```
CLAUDE-md/notifications.md  →  01- 02- 03- 04- 99-           (falta 05-)
CLAUDE.md (canônica)        →  01- 02- 03- 04- 05- 99-       (05- = telemetria)
```

E as **15 tips** existem em dois lugares: a tabela do `skills/shared/notifier/SKILL.md` (15 linhas `| N | … |`) **e** os arrays `TIPS_EN/PTBR/ES` do `04-notifier.sh`.

**Motivo:** três cópias do mesmo conhecimento, sem regra de sincronização. A prova de que isso quebra é a própria tabela de convenção: a `CLAUDE.md` ganhou o tier `05-` (telemetria), mas a cópia em `notifications.md` ficou para trás — mesma classe da divergência `docs/agents.md`×`docs/agents.pt-BR.md` (coluna Model), só que entre `CLAUDE.md` e seu próprio sub-arquivo. Distinto dos fingerprints `flow-notifier-hardcodes-45-tip-strings` (que trata só do array no script) e `ref-claude-md-356-stop-subscript-convention-omits-02b` (que trata só da tabela **na** `CLAUDE.md`): aqui o achado é a **triplicação** e a **deriva entre `CLAUDE.md` e `notifications.md`**.

**Impacto positivo da correção:** eleger **uma** fonte de verdade — o `skills/shared/notifier/SKILL.md` para formato/tipos/tips e a `CLAUDE.md` para a convenção de prefixos — e fazer os outros arquivos **apontarem** (não copiarem). Encerra a deriva silenciosa e reduz a manutenção de 3 lugares para 1.

**Impacto negativo / risco:** baixo. Risco de o script (`04-notifier.sh`) precisar das strings inline por não conseguir ler markdown em bash — mitigável extraindo as tips para um `tips.tsv`/`tips.json` lido tanto pelo script quanto referenciado pela skill, ou mantendo o script como fonte e a skill/doc apenas descrevendo o mecanismo.

---

## R2 — `CHANGELOG.md` `[Unreleased]` afirma "All 21 `/devteam:*` commands" mas o roster atual tem **30 comandos** (e **28** carregam `current-context`)

**Severidade:** LOW-MEDIUM
**Fingerprint:** `ref-changelog-unreleased-claims-all-21-devteam-commands-load-current-context-but-roster-is-30-and-28-load-it`

**Evidência:**

```
CHANGELOG.md:30  - All 21 `/devteam:*` commands now load `skills/shared/current-context/SKILL.md` …

$ ls commands/*.md | wc -l            → 30
$ grep -rl current-context commands/ | wc -l   → 28
   (os 2 que NÃO carregam: commit.md e update.md — exceções documentadas na CLAUDE.md)
```

**Motivo:** o número "21" contradiz tanto a contagem real de arquivos (**30**) quanto a aritmética da própria `CLAUDE.md`, que estabelece `commit.md` e `update.md` como as únicas exceções (logo, **28** carregam `current-context`). A seção `[Unreleased]` deve descrever o estado a ser lançado; com "21" ela está factualmente errada e, combinada com `02/F1` (a `[Unreleased]` já virou `v1.5`–`v1.7` nas tags), o erro foi efetivamente **publicado**. Distinto dos fingerprints de CHANGELOG existentes, que tratam de **omissões** de features — aqui é uma **contagem incorreta**.

**Impacto positivo da correção:** trocar "All 21" por "All commands except `commit` and `update` (28 of 30)" alinha o CHANGELOG com o roster e com a regra de exceção da `CLAUDE.md`; remove um número que envelhece a cada novo comando.

**Impacto negativo / risco:** nenhum funcional. Risco apenas de a frase voltar a envelhecer se novos comandos forem adicionados — mitigável usando a forma relativa ("todos exceto `commit`/`update`") em vez de um número absoluto.

---

## R3 — Duas tags git malformadas (`v.1.1.0` e `v.1.3.13`) violam a convenção `vX.Y.Z` documentada em `versioning.md` — risco de ordenação/resolução de versão e lacuna na sequência limpa

**Severidade:** LOW-MEDIUM
**Fingerprint:** `ref-two-malformed-git-tags-v-1-1-0-and-v-1-3-13-violate-vx-y-z-convention-in-versioning-md-break-version-sort-and-gap-clean-sequence`

**Evidência:**

```
$ git tag -l | grep -E '^v\.'
v.1.1.0      → 4702d9d  "Merge tag 'v.1.1.0'"
v.1.3.13     → f634deb  "perf(skills): shorten all 67 descriptions to ≤95 chars"

# Convenção declarada — CLAUDE-md/versioning.md:3
- Semantic versioning via git tags: `v1.0.0`, `v1.1.0`, `v2.0.0`

# Efeito colateral observável: a sequência limpa pula o 1.3.13
… v1.3.12 → (v.1.3.13 malformada) → v1.3.14 …
```

**Motivo:** o ponto após o `v` (`v.1.1.0`, `v.1.3.13`) destoa do padrão `vX.Y.Z`. O `install.sh` resolve "latest" via API do GitHub e permite **pin de versão** (`update.sh v1.0.0`); tags fora do padrão podem ser ignoradas por `sort -V` ou por um pin que assume `vMAJOR.MINOR.PATCH`, e já produziram uma **lacuna visível** (o `1.3.13` "some" da sequência canônica porque foi tagueado como `v.1.3.13`). É uma inconsistência de governança que sobrevive porque nenhum check valida nomes de tag contra a convenção.

**Impacto positivo da correção:** retagar `v.1.1.0`→`v1.1.0` e `v.1.3.13`→`v1.3.13` (ou criar aliases corretos) normaliza a resolução de versão e fecha a lacuna; um lint opcional de tags no CI evitaria recorrência. Tornaria `git tag -l | sort -V` 100% consistente com a política.

**Impacto negativo / risco:** **médio** — retagar tags já publicadas pode quebrar quem fez pin nelas. Mitigação: **não** apagar as tags antigas; criar as corretas em paralelo e documentar a equivalência no CHANGELOG; ou apenas adicionar o lint de convenção e tratar as duas tags como dívida histórica conhecida. Por isso a recomendação prioriza o lint preventivo sobre a reescrita destrutiva.
