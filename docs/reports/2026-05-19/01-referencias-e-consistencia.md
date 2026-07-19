# Referências e Consistência — 2026-05-19

> Sugestões **originais** (não repetem fingerprints já registrados em `_index.md`).
> Cada item traz: evidência (arquivo:linha), motivo, impacto positivo da correção, risco/impacto
> negativo e recomendação. Severidade: **HIGH / MEDIUM / LOW**.

---

## R1 — CLAUDE.md descreve o roteamento de review com os agentes ERRADOS  · **HIGH**

**Fingerprint:** `ref-claude-md-183-code-reviewer-roles-says-delegates-to-test-specialists-but-impl-routes-to-backend-frontend-reviewer`

**Evidência:**

- `CLAUDE.md:183` (parágrafo "Code Reviewer roles"): *"…delegates to `backend-test-specialist` or `frontend-test-specialist` as needed."*
- `agents/code-reviewer.md:21-22`: *"`BACKEND` → you proceed as `backend-reviewer`"* / *"`FRONTEND` → you proceed as `frontend-reviewer`"*
- `agents/code-reviewer.md:16`: carrega `skills/shared/review-router/SKILL.md` (router real).
- `commands/review.md` referencia `backend-reviewer`/`frontend-reviewer`, **não** os test-specialists.

**Motivo:** o documento que governa o repositório afirma um fluxo de delegação que **contradiz a
implementação**. `backend-test-specialist`/`frontend-test-specialist` são agentes de *escrita de
testes*; os revisores são `backend-reviewer`/`frontend-reviewer`. Isso é diferente do fingerprint
antigo `ref-code-reviewer-vs-specialists-roles-undocumented` (2026-05-09), que apontava **ausência**
de documentação — aqui a documentação **existe e está incorreta**, o que é pior (induz a erro). Os
agentes `backend-reviewer`/`frontend-reviewer` também **não aparecem em nenhuma tabela de roster ou
de comando** do CLAUDE.md (a linha 156 do `/devteam:review` lista apenas `code-reviewer`).

**Impacto positivo da correção:** quem ler o CLAUDE.md (humano ou agente) entende o fluxo real de
review; elimina risco de spawnar o agente errado em automações futuras.

**Impacto negativo / risco:** baixo — é edição de doc. Risco de re-introduzir drift se a tabela de
comandos e o parágrafo não forem atualizados juntos (CLAUDE.md já tem a "Auto-Docs Rule" para isso).

**Recomendação:** corrigir `CLAUDE.md:183` para citar `backend-reviewer`/`frontend-reviewer`;
adicionar os 2 revisores ao roster de agentes e à linha do `/devteam:review`.

---

## R2 — Dois diretórios chamados "helpers" com semânticas opostas de empacotamento  · **HIGH**

**Fingerprint:** `ref-two-helpers-dirs-naming-collision-root-stripped-vs-scripts-helpers-shipped-claude-md-file-structure-omits-scripts-helpers`

**Evidência:**

- `helpers/` (raiz): 6 ferramentas de autoria — `agent-lint.sh`, `archive-index.sh`, `check-fingerprint-uniqueness.sh`, `orphan-skill-scan.sh`, `orphan-template-scan.sh`, `size-limits.sh`. **Removido no install** (`scripts/install.sh:144`: `rm -rf "$EXTRACTED_ROOT/helpers"`).
- `scripts/helpers/telemetry-send.sh` (289 linhas): runtime, **enviado ao usuário** porque `KEEP_ROOT=(agents scripts skills workflows templates commands)` (`install.sh:129`) preserva todo `scripts/`.
- `install.sh:525` e `update.sh:76`: `_TELEMETRY_SEND="$INSTALL_DIR/scripts/helpers/telemetry-send.sh"`.

**Motivo:** dois diretórios com o **mesmo nome** ("helpers") e **regras de empacotamento opostas**
(um é dev-only e some no install, o outro é runtime e é distribuído). Isso é uma armadilha de
manutenção: um colaborador que mover um script de `scripts/helpers/` para `helpers/` (ou vice-versa)
muda silenciosamente se ele é enviado ou não ao usuário. O bloco "File Structure" do CLAUDE.md
documenta `helpers/` (pendente desde 2026-05-18) **e não menciona `scripts/helpers/` de forma alguma**.

**Impacto positivo da correção:** elimina ambiguidade ship/strip; reduz risco de vazar dev-tool para
o pacote do usuário ou de remover acidentalmente um script de runtime.

**Impacto negativo / risco:** renomear `scripts/helpers/` exige atualizar 2 referências
(`install.sh`, `update.sh`) — mudança pequena mas com risco se uma referência ficar para trás.

**Recomendação:** renomear `scripts/helpers/` → `scripts/runtime/` (ou `scripts/lib/`) para deixar a
semântica de runtime explícita; documentar ambos no "File Structure" deixando claro qual é stripado.

---

## R3 — Tabela de convenção de sub-scripts do Stop não documenta o prefixo `02b-`  · **MEDIUM**

**Fingerprint:** `ref-claude-md-356-stop-subscript-convention-omits-02b-orphan-template-scan-undocumented-prefix-in-02-tier`

**Evidência:**

- `CLAUDE.md:356` (tabela "Stop Hook Sub-script Convention"), faixa `02-`: lista apenas `02-orphan-skill-scan.sh`.
- Diretório real `scripts/hooks/stop/`: contém `02-orphan-skill-scan.sh` **e** `02b-orphan-template-scan.sh`.
- A própria CLAUDE.md instrui: *"pick a number within that tier (e.g., `02-new-check.sh`)"* — não prevê o sufixo de letra `02b-`.

**Motivo:** o prefixo `02b-` é uma inserção ad-hoc fora da convenção documentada. Como o dispatcher
faz glob de `*.sh` (ver [02-fluxos-e-workflows.md](02-fluxos-e-workflows.md), F3), o `02b-` roda na
prática, mas a convenção que deveria ser fonte única de verdade fica defasada — drift declarativo
clássico do projeto.

**Impacto positivo da correção:** convenção volta a refletir a realidade; futuros sub-scripts seguem
um padrão único (sem proliferação de `02b-`, `02c-`…).

**Impacto negativo / risco:** mínimo. Decidir entre "documentar o sufixo de letra como padrão
oficial" vs "renumerar para `03-` e empurrar os demais" — a segunda opção mexe em mais arquivos.

**Recomendação:** acrescentar `02b-orphan-template-scan.sh` à tabela (na faixa `02-`, integridade de
repositório) **ou** oficializar a convenção `NN[a-z]-` para checks correlatos dentro da mesma faixa.

---

## Itens reverificados (não são sugestões novas — ver Guardian)

Os seguintes continuam **🔴 não feitos** e já estão no índice; não são repropostos como novos:
`auto-docs-rule-violated-changelog-unreleased-missing-7-features`,
`ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`,
`ref-templates-backlog-template-md-orphan`,
`ref-helpers-archive-index-script-shipped-but-not-hooked`.
Detalhes em [00-guardian-audit.md](00-guardian-audit.md).
