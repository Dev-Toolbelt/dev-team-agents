# Eixo B — Referências e Consistência — 2026-10-10

**Baseline:** `HEAD` = `349f18c`

## Resultado

**Nenhum achado original neste eixo.** 6 candidatos, todos descartados pelas portas 3 ou 5.

Isso não é ausência de problemas — é a maturidade do banco. Cada candidato que a varredura
levantou já tem fingerprint, aberto, com remediação descrita e não executada.

## Gates rodados

| Gate | Saída |
|---|---|
| `helpers/orphan-skill-scan.sh` | `clean ✓` — **falso negativo conhecido**, ver abaixo |
| `helpers/orphan-template-scan.sh` | `clean ✓` |
| `helpers/agent-lint.sh` | `clean ✓` |
| `helpers/size-limits.sh` | `clean ✓` com WARN: `CLAUDE.md: 647 lines (warning threshold: 600, fails at 700)` |
| `helpers/check-fingerprint-uniqueness.sh` | `✓ All 287 fingerprint slugs are unique across 1 bank file(s)` |
| `helpers/preferences-sync-lint.sh` | `clean ✓ (2 mirrors checked)` — 2 dos 5 espelhos, fingerprint aberto |
| `helpers/archive-index.sh --dry-run` | nenhuma seção com mais de 90 dias; a mais antiga é 2026-07-30 (72 dias) |

O `clean ✓` do orphan-skill-scan é o falso negativo registrado em
`ref-orphan-skill-scan-blind-to-directory-form-skill-refs`: o scanner casa só
`skills/…/SKILL.md`, e os 7 caminhos mortos de `commands/relayout.md:35` estão na forma de
diretório. Rodei a varredura na forma de diretório por fora do scanner:

```
grep -rhoE 'skills/[a-zA-Z0-9/_-]+' agents/ commands/ skills/ CLAUDE.md CLAUDE-md/ templates/ \
 | sed 's#/SKILL\.md$##' | sort -u | while read -r r; do
     [ -d "$r" ] || [ -f "$r" ] || [ -f "$r.md" ] || echo "DEAD: $r"
   done
```

Os únicos caminhos genuinamente mortos no repositório inteiro são **os 7 já registrados**. Os
outros hits da lista são prefixos `.claude/skills/…` e `.codex/skills/devteam-…` cortados pelo
`sed` — falsos positivos da minha própria consulta, não do repositório.

## Checagens mecânicas que passaram

- **`name:` vs. basename do diretório** — 155 skills, **zero divergências**.
- **Nomes de skill duplicados entre categorias** — zero (`find skills -name SKILL.md | awk -F/ '{print $(NF-1)}' | sort | uniq -d` vazio).
- **Índice do wiki ↔ entradas em disco** — 51 entradas, 51 linhas de índice, **zero órfãs nos dois
  sentidos**. Inclui a entrada adicionada pelo delta
  (`store/windows-symlink-stubs-recognized-as-v2-output.md`), que tem sua linha. O protocolo de
  `wiki-format.md:90` foi cumprido à mão.
- **Numeração de ADR** — 29 ADRs, `0006`–`0034`, sem colisões e sem buracos internos.
  `0001`–`0005` nunca existiram no git (`git log --diff-filter=D` vazio): a numeração começou em
  `0006`. `scripts/new-adr.sh:74-78` deriva o próximo número de `sort -n | tail -1` + 1, ou seja
  do **máximo**, não da contagem — os buracos iniciais não geram colisão.

## Candidatos descartados

### Porta 5 (estado — já no conjunto aberto) — 4

1. **`CLAUDE.md:327` enumera um só arquivo sob `.github/scripts/release/`**
   (`bump-homebrew-formula.sh`) enquanto a árvore tem cinco — `render-app-cask.py`,
   `render-winget-manifests.py`, `stamp-code-signed.cjs` e `verify-mac-notarised.sh` entraram
   em `a2933cd`, no delta. Também: `infra/` não tem **nenhuma** linha na árvore de File Structure,
   apesar de `infra/supabase/functions/` emitir o entitlement assinado que o CLI confia
   (ADR-0029). Pertence a
   `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-four-recurrences-each-discarded-as-duplicate`
   (MEDIUM-HIGH, aberto) — esta é a quinta recorrência, e registrá-la como achado novo é
   exatamente o que aquele fingerprint existe para impedir.
2. **`CLAUDE.md:300-302` lista 20 dos ~44 módulos de `scripts/lib/devteam/`** (fora: `auth*`
   — 5 módulos —, `catalog`, `command_usage`, `compat`, `console`, `credentials_local`, `creds`,
   `detect`, `ed25519`, `entitlement`, `hooks`, `notifications`, `pr_refs`, `prefs`, `redirects`,
   `review_triggers`, `secrets`, `shells`, `store`, `tasks`, `upgrade`). Mesmo fingerprint-pai.
3. **`scripts/lib/first-task.json`, `stack-signals.json`, `auth-config.json` e
   `auth-config.dev.json` não aparecem na enumeração de `scripts/lib/`** — os dois últimos são a
   configuração de conta da ADR-0029. Mesmo fingerprint-pai.
4. **`README.pt-BR.md` linka 5 docs só em inglês** (`:60,61,62,66,262`), mais
   `docs/harness.pt-BR.md:179` e `docs/installation.pt-BR.md:5`. É o fingerprint aberto
   `docs-sync-readme-ptbr-agents-link-points-to-english-doc`, que registrou 1 link; medi 7. Escopo
   **maior**, não menor — a Porta 4 só admite sub-escopo estritamente contido, então isto é
   re-medição de um item aberto (anotada no `_index.md`), não achado novo.

### Porta 3 (semântica — 2 ou 3 de 3 atributos) — 2

5. **`02-readme-sync.sh` descobre pares só a partir de `*.pt-BR.md`**, então um doc EN novo
   sem tradução nunca é sinalizado — hoje 4 de 9 docs em `docs/` são EN-only
   (`install-claude.md`, `install-codex.md`, `install-opencode.md`, `providers.md`) e nada
   distingue "falta traduzir" de "EN por decisão". Contra
   `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair`
   (MEDIUM, aberto): mesmo arquivo-alvo (`:202,211`), mesma causa raiz (descoberta de pares em
   uma só direção), mesma remediação (simetrizar a descoberta ou registrar exceções). 3 de 3.
6. **Nenhum gate confere o índice do wiki contra as entradas em disco**, apesar de
   `wiki-format.md:90` declarar a linha de índice obrigatória e `project-context/SKILL.md:151`
   fazer a leitura depender dela ("uma entrada sem linha de índice é inalcançável, logo é uma
   escrita incompleta"). O repositório está limpo hoje — o que, pela própria ENFORCEMENT POLICY
   de `01-lint.sh`, é precisamente a condição para um check `blocking`. Contra
   `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-…`: alvo diferente,
   mas a mesma causa raiz (invariante 1:1 documentada sem verificação automática) e a mesma
   remediação (helper + gate). 2 de 3 → duplicata.

> A sexta é a mais dolorosa de descartar, porque é a mais fácil de implementar e a que o delta
> mais exercitou (12 entradas de wiki em um dia, 2026-10-02). Fica registrada aqui para que a
> execução do fingerprint-pai inclua o wiki no mesmo helper em vez de tratá-lo depois.
