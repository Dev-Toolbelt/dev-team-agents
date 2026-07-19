# Referências e Consistência — 2026-05-20

> Sugestões **originais** (não repetem fingerprints já registrados em `_index.md`).
> Cada item traz: evidência (arquivo:linha), motivo, impacto positivo da correção, risco/impacto
> negativo e recomendação. Severidade: **HIGH / MEDIUM / LOW**.

---

## R1 — A "canonical agent reference" (`docs/agents.md`) tem a coluna **Model** errada em 2 agentes  · **HIGH**

**Fingerprint:** `ref-docs-agents-md-model-column-wrong-technical-writer-listed-haiku-actually-sonnet-and-setup-assistant-listed-sonnet-actually-opus`

**Evidência:**

| Agente | `docs/agents.md` | Frontmatter real (`agents/<name>.md`) |
|--------|------------------|----------------------------------------|
| `technical-writer` | `docs/agents.md:26` → **Haiku** | `agents/technical-writer.md:4` → `model: claude-sonnet-4-6` |
| `setup-assistant` | `docs/agents.md:27` → **Sonnet** | `agents/setup-assistant.md` → `model: claude-opus-4-7` |

Verificação: `grep '^model:' agents/*.md | sort | uniq -c` → **4 Opus + 13 Sonnet, 0 Haiku**. Os 4
Opus são `product-analyst`, `software-architect`, `security-specialist` e `setup-assistant`.

**Motivo:** `docs/agents.md` é declarado em CLAUDE.md como a *referência canônica de agentes*. Ter a
coluna `Model` errada em 2 dos 17 agentes corrói a confiança no documento e induz decisões erradas de
custo/latência (ex.: alguém estimando custo assume `technical-writer` em Haiku, que é mais barato, mas
ele roda em Sonnet; assume `setup-assistant` em Sonnet, mas ele roda em Opus, o mais caro). Pior: o
caso `technical-writer` **contradiz a própria CLAUDE.md**, cujo Authoring Standards diz que Haiku está
reservado para *"future micro-agents"* e que deve ser readicionado *"when a concrete candidate
emerges"* — ou seja, a doc canônica anuncia um agente Haiku que a política diz não existir ainda, e
que de fato **não existe**. É um item **novo**, distinto do R1 de 2026-05-19 (que era sobre o
roteamento de review em `CLAUDE.md:183`).

**Impacto positivo da correção:** referência canônica volta a ser confiável; alinha doc ↔ frontmatter
↔ política de modelos; remove a contradição "Haiku reservado para o futuro" vs "technical-writer é Haiku".

**Impacto negativo / risco:** baixo — é edição de 2 células de tabela. Atenção: corrigir também
`docs/agents.pt-BR.md` (mesma tabela traduzida, 95 linhas, provavelmente com os mesmos 2 erros) na
mesma mudança, por causa da README/docs Sync Rule.

**Recomendação:** corrigir `docs/agents.md:26` (`Haiku` → `Sonnet`) e `:27` (`Sonnet` → `Opus`);
replicar em `docs/agents.pt-BR.md`. Para evitar regressão futura, considerar um check de CI que extraia
a coluna Model da tabela e compare com `grep '^model:' agents/*.md` (cruza doc ↔ frontmatter).

---

## R2 — Diretiva de carga do `comments-policy` copiada **verbatim em 8 agentes** (sem fonte única)  · **MEDIUM**

**Fingerprint:** `ref-comments-policy-load-directive-with-conditional-section-parenthetical-duplicated-verbatim-in-8-agents-no-single-source-of-truth`

**Evidência:** a frase abaixo aparece **idêntica** em 8 agentes —
`backend-developer.md:213`, `backend-reviewer.md:28`, `backend-test-specialist.md:94`,
`code-reviewer.md:41`, `database-specialist.md:122`, `devops-specialist.md:199`,
`frontend-reviewer.md`, `frontend-test-specialist.md`:

```
Load `skills/shared/comments-policy/SKILL.md`. Load additional sections conditionally based on
context (Python → type-annotations, tests → aaa-pattern, legacy review → anti-patterns) …
```

(`grep -rc "Load additional sections conditionally based on context (Python → type-annotations" agents/*.md`
→ 8 arquivos, 1 ocorrência cada.)

**Motivo:** a regra de **como** carregar condicionalmente as seções do `comments-policy` (o mapeamento
`Python → type-annotations`, `tests → aaa-pattern`, `legacy review → anti-patterns`) é uma decisão de
política que hoje vive **duplicada em 8 lugares**. Se o mapeamento mudar (ex.: adicionar
`TypeScript → strict-null`, ou renomear uma sub-seção), é preciso editar 8 arquivos em sincronia — e a
ausência de qualquer um gera drift silencioso. O mais natural seria essa regra de roteamento morar
**dentro** do próprio `comments-policy/SKILL.md` (que é a fonte única), e os agentes apenas dizerem
"carregue `comments-policy` e siga seu gate de seções". É item **novo** — nunca foi fingerprintado.

**Impacto positivo da correção:** uma única fonte de verdade para o roteamento de seções; mudanças de
política passam a ser 1 edição; reduz o corpo de 8 agentes em ~2-4 linhas cada.

**Impacto negativo / risco:** se a regra migrar para a skill, os agentes perdem a "dica" inline de
qual seção carregar — mitigável fazendo o `comments-policy/SKILL.md` abrir com uma tabela "contexto →
seção" auto-explicativa, e os agentes referenciarem só "siga a tabela de roteamento da skill".

**Recomendação:** mover o mapeamento condicional para o topo de `skills/shared/comments-policy/SKILL.md`
(tabela "contexto → seção"); substituir as 8 frases longas por uma curta: *"Load
`skills/shared/comments-policy/SKILL.md` and follow its context→section routing table."*

---

## R3 — File Structure do CLAUDE.md enumera `scripts/` omitindo 3 scripts de runtime enviados  · **MEDIUM**

**Fingerprint:** `ref-claude-md-file-structure-scripts-enumeration-omits-check-updates-rollback-validate-commit-msg-three-shipped-runtime-scripts`

**Evidência:**

- CLAUDE.md, bloco "File Structure": `scripts/ ← install.sh, update.sh, new-adr.sh, graphify-refresh.sh`.
- `find scripts -maxdepth 1 -name '*.sh'` revela **também**: `check-updates.sh`, `rollback.sh`, `validate-commit-msg.sh` — 3 scripts presentes e **enviados ao usuário** (estão sob `scripts/`, preservado por `KEEP_ROOT` no install).

**Motivo:** a enumeração da File Structure cita 4 scripts e omite 3 que existem no mesmo diretório e
são distribuídos. `rollback.sh` em especial é uma capacidade observável relevante (desfazer um update)
que não aparece na documentação estrutural — exatamente o tipo de coisa que a "Auto-Docs Rule" do
CLAUDE.md exige manter sincronizada. Distingue-se do fingerprint
`ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder` (2026-05-18), que tratava
de **diretórios de topo** (`helpers/`, `CLAUDE-md/`) e do `PRIVACY.md`; aqui o ângulo é o **conteúdo
interno de `scripts/`** sub-enumerado.

**Impacto positivo da correção:** a File Structure passa a refletir o conjunto real de scripts
enviados; `rollback.sh` ganha visibilidade documental; reduz a chance de um script de runtime ser
movido/renomeado sem rastro na doc.

**Impacto negativo / risco:** mínimo — edição de doc. Decidir entre listar todos os `.sh` (mais
manutenção) ou trocar a enumeração por uma descrição de categoria (ex.: *"install/update/rollback
lifecycle + new-adr.sh + graphify-refresh.sh + hooks/"*), que envelhece melhor.

**Recomendação:** acrescentar `check-updates.sh`, `rollback.sh`, `validate-commit-msg.sh` à linha de
`scripts/` na File Structure (e replicar em README se houver árvore equivalente). Preferir descrição
por categoria a uma lista exaustiva, para reduzir manutenção futura.

---

## Itens reverificados (não são sugestões novas — ver Guardian)

Continuam **🔴 não feitos** e já estão no índice; não são repropostos como novos:
`auto-docs-rule-violated-changelog-unreleased-missing-7-features`,
`ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`,
`ref-templates-backlog-template-md-orphan`,
`ref-helpers-archive-index-script-shipped-but-not-hooked`,
`ref-claude-md-183-code-reviewer-roles-...` (2026-05-19).
Detalhes em [00-guardian-audit.md](00-guardian-audit.md).
