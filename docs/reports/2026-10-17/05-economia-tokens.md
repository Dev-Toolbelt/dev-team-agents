# Eixo E — Economia de tokens — 2026-10-17

**Baseline:** `HEAD` = `bb0e883`.

O delta piorou três medidas já registradas e abertas — `interaction-patterns` 209 → **323**
linhas carregadas por **34** comandos, `plan-mode` 14.853 → **16.602 B**, `CLAUDE.md` 647 →
**678** linhas — e todas estão anotadas como re-ancoragem em
[`00-guardiao-verificacao.md`](00-guardiao-verificacao.md), não como achado novo (porta 5).

O que é território novo é a `spec-gate`, que cresceu 146 linhas neste delta e passou a ser
carregada por 9 agentes e 10 comandos.

---

## MEDIUM

### `spec-gate` virou a 2ª maior skill compartilhada e é carregada inteira por seis agentes que usam 7–16% dela

- **Fingerprint:** `token-spec-gate-17kb-loaded-whole-by-six-execution-agents-that-scope-two-sections`
- **Alvo:** `skills/shared/spec-gate/SKILL.md`
- **Evidência:**
  - `wc -c skills/shared/spec-gate/SKILL.md` → **17.463 B / 248 linhas**; só
    `project-context/SKILL.md` (18.629 B) é maior entre as 40 skills de `skills/shared/`. Eram
    102 linhas antes do delta (`git show 349f18c:…`).
  - Sem subdiretório: `ls skills/shared/spec-gate/` → apenas `SKILL.md`.
  - Quatro coding agents carregam a skill por **uma** seção —
    `agents/backend-developer.md:27`, `agents/frontend-developer.md:27`,
    `agents/mobile-developer.md:27`, `agents/database-specialist.md:29`: "load
    `skills/shared/spec-gate/SKILL.md` **and apply its Scope Lock**". § Scope Lock — Execution
    Agents tem **1.250 B** → **7,2%** do arquivo.
  - Dois test specialists carregam por duas — `agents/backend-test-specialist.md:52`,
    `agents/frontend-test-specialist.md:53`: "derive one test per scenario". § Test-First
    Derivation (2.204 B) + § Traceability (664 B) = **2.868 B** → **16,4%**.
  - As outras onze seções — Retroactive Spec (2.833 B), Task Resolution (1.797 B), Spec Sync
    Gate (1.440 B), Living Spec (1.442 B), Spec Status (1.377 B), Gate Rule (845 B), Mechanical
    Check (945 B), Sprint Linkage (428 B), QA Validation (375 B), Document Structure (301 B),
    Spec File (892 B) — pertencem a `product-analyst`, `qa-specialist`, `software-architect` e
    aos comandos, não aos seis acima.
- **Problema:** uma skill de referência de 17,5 KB com 14 seções e nenhum `references/`, lida
  inteira por todo agente que precisa de qualquer parte dela.
- **Por que importa no `HEAD` atual:** quantificado por fluxo. Um `/devteam:fullstack` com spec
  ligada e `TESTS_REQUIRED=yes` spawna os quatro coding agents e os dois test specialists:
  **6 × 17.463 B = 104.778 B carregados** contra **4 × 1.250 + 2 × 2.868 = 10.736 B** em escopo
  — **94.042 B (≈ 90%) de contexto que nenhum dos seis vai usar**, por execução. Numa onda de
  `/devteam:sprint` o número se multiplica por tarefa, porque cada worktree é um spawn novo. A
  skill cresceu 2,4× neste delta e os seis loaders não ganharam seção nenhuma: a conta piora a
  cada seção de produto que entra.
- **Proposta:** mover para `skills/shared/spec-gate/references/` as seções que só um papel usa —
  `retroactive-spec.md` (Retroactive Spec + QA Validation + Decide), `authoring.md` (Document
  Structure, Spec File, Spec Status, Gate Rule, Living Spec), `sprint.md` (Task Resolution,
  Sprint Linkage, Mechanical Check) — deixando no `SKILL.md` as três seções transversais (Scope
  Lock, Test-First Derivation, Traceability) mais a tabela de roteamento "quem carrega o quê",
  no padrão que `skills/shared/comments-policy/SKILL.md:107-109` já usa.
- **Impacto positivo:** o `SKILL.md` cai para ~5 KB; os seis agentes de execução passam a ler
  ~5 KB em vez de 17,5 KB — **≈ 75 KB a menos por `/devteam:fullstack` com spec**, e proporcional
  por tarefa numa onda de sprint. `product-analyst`, `qa-specialist` e os comandos pagam um
  `Read` a mais para alcançar a seção que já usavam.
- **Impacto negativo / risco:** o custo é real e tem três faces. (1) `product-analyst` e
  `/devteam:spec` passam a precisar de duas leituras onde hoje precisam de uma — para eles o
  saldo de tokens é pior, não melhor. (2) As seções da camada de spec se referenciam entre si
  (§ Task Resolution cita § Spec Status, § Retroactive Spec cita § Traceability); espalhá-las
  cria ponteiros entre arquivos que nenhum helper valida — `orphan-skill-scan.sh` só casa
  `skills/…/SKILL.md` literal e é cego para `references/*.md`, conforme o fingerprint aberto
  `ref-orphan-skill-scan-blind-to-directory-form-skill-refs`. (3) Vinte e três arquivos
  (`grep -l spec-gate/SKILL.md agents/ commands/`) citam a skill pelo caminho do `SKILL.md`;
  os que precisam de uma seção movida têm de ser reescritos no mesmo commit, ou passam a
  carregar um arquivo que não contém mais o que a frase promete.
- **Esforço:** Médio
