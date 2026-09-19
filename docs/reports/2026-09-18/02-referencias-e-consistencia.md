# Eixo B — Referências e Consistência — 2026-09-18

**Baseline:** `HEAD` = `ef69da3`

## Saída dos gates

| Helper | Exit | Leitura |
|---|---|---|
| `helpers/orphan-skill-scan.sh` | `0` | Nenhum órfão e nenhuma referência quebrada em `agents/`+`commands/`. Só o bloco **ACTION SUGGESTED** com as 3 "cargas duplicadas" já verificadas como falsos positivos do scanner em 2026-08-21 (`backend-test-specialist.md`/`frontend-test-specialist.md` → `test-pyramid`, `commands/merge.md` → `worktree`). |
| `helpers/orphan-template-scan.sh` | `0` | `orphan-template-scan: clean ✓` — os 5 templates resolvem de todos os sítios citados. |
| `helpers/agent-lint.sh` | `0` | `agent-lint: clean ✓` — frontmatter, drift `tiers.json`↔`model:`↔run-banner, identidade de skill (152 `name` == dir, sem colisão), quiz-first e roster `commands.json`↔`agents/` íntegros. |
| `helpers/size-limits.sh` | `1` | Único vermelho: `⚠ CLAUDE.md: 602 lines (warning threshold: 600)` contado como violação — bug já registrado (`auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red`, HIGH, aberto). 18 agentes / 152 skills / 35 comandos dentro dos limites. |

**`orphan-skill-scan.sh` não modificou nenhum arquivo** (bloco AUTO-FIXED vazio). `git status
--porcelain` antes e depois devolve apenas `?? docs/reports/2026-09-18/`. Nada a reverter; a árvore
permanece limpa.

**Verificações adicionais executadas sem achado:** 174 referências `skills/**/SKILL.md` e
`references/*` resolvem (as 4 quebradas estão só em `CHANGELOG.md` e em relatórios históricos);
0 de 152 descrições acima de 95 chars; 35=35=35 entre `commands/`, `commands.json` e a tabela do
`CLAUDE.md`; `plan_gate` de `commands.json` bate 9/20/6 com `CLAUDE.md:254`;
`grep -L current-context commands/*.md` devolve exatamente as 6 exceções listadas em `:252`; todos
os links markdown relativos de `README*`, `docs/*.md`, `CONTRIBUTING`, `SECURITY`, `PRIVACY`
resolvem; os 5 pares EN↔pt-BR (`agents`, `installation`, `harness`, `user-preferences`,
`credentials.local`) têm linhas, headings e linhas de tabela idênticas.

---

## MEDIUM-HIGH

### A tabela canônica de roteamento do `comments-policy` aponta para `sections/` três arquivos que vivem em `references/`

- **Fingerprint:** `ref-comments-policy-routing-table-points-to-sections-dir-not-references`
- **Alvo:** `skills/shared/comments-policy/SKILL.md`
- **Evidência:** `skills/shared/comments-policy/SKILL.md:107` — "`| Python files in scope | skills/shared/comments-policy/sections/type-annotations.md |`"; `:108` — "`sections/aaa-pattern.md`"; `:109` — "`sections/anti-patterns.md`". Os três arquivos existem em `skills/shared/comments-policy/references/` (`ls` devolve `aaa-pattern.md anti-patterns.md type-annotations.md`), e `sections/` contém outra coisa (`generic.md go.md javascript-typescript.md python.md`). O bloco correto está 7 linhas abaixo: `:114-116` — "`- references/aaa-pattern.md — AAA test pattern with examples`". `CLAUDE.md:161` elege justamente a tabela quebrada como casa canônica: "`| Comments policy, including TODO/FIXME handling | skills/shared/comments-policy/SKILL.md (Conditional Section Loading table) | Load it; the routing parenthetical belongs to the skill |`".
- **Problema:** as três linhas da *Conditional Section Loading* usam caminho absoluto com o diretório errado. Nenhum dos três resolve.
- **Por que importa:** a skill é carregada por 8+ agentes e é shipada para todo projeto instalado. Um agente com arquivo Python, de teste ou de legado em escopo segue a tabela e recebe file-not-found, gastando uma chamada de tool por linha antes de cair (ou não) no bloco `references/` de `:114-116`. Nenhum gate cobre: `orphan-skill-scan.sh` só varre `agents/`+`commands/` e só casa `skills/.../SKILL.md` (`:72`), nunca `references/`/`sections/`; o mesmo scan pula explicitamente esses diretórios na fase de órfãos (`:122-123`).
- **Proposta:** trocar `sections/` por `references/` nas três linhas `:107-109` e, já que o bloco `:114-116` lista os mesmos três arquivos, fundir os dois numa única tabela contexto→arquivo.
- **Impacto positivo:** elimina 3 caminhos mortos na única tabela que o `CLAUDE.md` declara canônica; remove uma duplicação de 3 linhas dentro do próprio arquivo.
- **Impacto negativo / risco:** a fusão muda a forma do documento, e qualquer prosa externa que cite "Conditional Section Loading" como bloco separado do "Reference Material" passa a referenciar uma seção que não existe mais; corrigir só os caminhos mantém a duplicação que permitiu a divergência.
- **Esforço:** Baixo

### O registro de espelhos de `preferences-defaults.json` nomeia os dois READMEs, que não carregam mais a tabela, e omite os dois docs que carregam — já defasados

- **Fingerprint:** `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair`
- **Alvo:** `CLAUDE.md`
- **Evidência:** `CLAUDE.md:375` — "**`scripts/lib/preferences-defaults.json` is the single source of truth for the default schema.** Everything else is a mirror … When you change a key, change every mirror in the same commit:"; `:382` — "`| README.md / README.pt-BR.md — worktree preference table | Documentation |`". Nenhum dos dois READMEs contém uma única chave `worktree_*`: `README.md:222` — "Worktree isolation, notification thresholds, language settings, and other local runtime knobs now live in [User Preferences](docs/user-preferences.md)." (espelhado em `README.pt-BR.md:222`). O conteúdo migrou em `affc6fe` para `docs/user-preferences.md` / `docs/user-preferences.pt-BR.md` (183 linhas cada), que trazem o bloco `## Default Schema` (`:43-67`) **e** uma `## Preference Reference` (`:80-95`) — e faltam `auto_learn_before_commit` nos dois lugares, nos dois idiomas (`grep -c auto_learn_before_commit docs/user-preferences*.md` → `0`, contra `1` no JSON canônico, `2` em `CLAUDE-md/preferences.md` e `2` em `skills/shared/user-preferences/SKILL.md`). Nenhum dos dois arquivos aparece na tabela `:377-382`.
- **Problema:** a tabela de espelhos aponta para dois arquivos onde a edição é no-op e não lista os dois arquivos onde ela é necessária. A deriva que a tabela existe para impedir já aconteceu nos arquivos não listados.
- **Por que importa:** são os documentos públicos linkados do README como referência de preferências. Quem seguir literalmente `CLAUDE.md:375-382` ao adicionar a próxima chave vai editar os READMEs (sem efeito) e deixar os dois docs reais para trás — exatamente o padrão que produziu `auto_learn_before_commit`. Não há gate: `02-readme-sync.sh` compara EN↔pt-BR (os dois estão igualmente errados, logo passa verde) e nada compara doc↔JSON.
- **Proposta:** trocar a linha `:382` por `| docs/user-preferences.md / docs/user-preferences.pt-BR.md — schema block + Preference Reference | Documentation |` e acrescentar `auto_learn_before_commit` ao bloco JSON (`:45-67`) e à tabela de campos dos dois arquivos.
- **Impacto positivo:** o registro volta a listar 100% dos espelhos reais (4 de 4 corretos em vez de 2 de 4) e fecha a lacuna de 1 chave em 2 arquivos × 2 idiomas.
- **Impacto negativo / risco:** aumenta de 2 para 2+2 os arquivos a tocar por mudança de chave (os READMEs saem, mas o par pt-BR entra e a README Sync Rule passa a valer também para ele); e o conserto reforça o padrão de espelho manual em vez de atacar a causa — cinco cópias humanas de um JSON de 21 linhas.
- **Esforço:** Baixo

---

## MEDIUM

### O parser de "User-Invocable Skills" do `orphan-skill-scan.sh` atravessa três tabelas e isenta silenciosamente `current-context` e `spawn-classifier` da detecção de órfãos

- **Fingerprint:** `auto-orphan-skill-scan-user-invocable-parser-overruns-into-next-table`
- **Alvo:** `helpers/orphan-skill-scan.sh`
- **Evidência:** `helpers/orphan-skill-scan.sh:37` — "`done < <(awk '/User-Invocable Skills/{found=1} found && /^\|/{print} found && /^### /{found=0}' "$CLAUDE_MD")`"; `:126` — "`is_user_invocable "$skill_name" && continue`". O heading que abre a seção é `CLAUDE.md:189` (`#### User-Invocable Skills`) e o próximo `^### ` só aparece em `CLAUDE.md:266` (`### Templates (templates/*.md)`) — `#### User-Invocable Commands` (`:206`) não casa `/^### /`. Reproduzido: rodar o `awk` de `:37` seguido do regex de `:34` devolve **cinco** nomes — `skill-creator`, `agent-creator`, `review`, `current-context`, `spawn-classifier` — contra os três da tabela real.
- **Problema:** a janela de captura vai de `:189` a `:266` (77 linhas, 3 tabelas). A tabela **Command-level skills** (`CLAUDE.md:203-205`) tem primeira célula em backticks com caracteres válidos para o regex `[a-zA-Z0-9_-]`, então suas duas entradas entram no array de isenção. (A tabela de comandos escapa por acaso: `/devteam:setup` contém `/` e `:`, fora da classe.)
- **Por que importa:** `current-context` e `spawn-classifier` são justamente as skills que `CLAUDE.md:201` define como "loaded by `commands/*.md` files rather than by agents directly" — a categoria que a detecção de órfãos deveria cobrir. Hoje ambas são referenciadas, então o defeito é latente: se qualquer comando parar de carregá-las, o scanner continua reportando `clean ✓` no CI e no `Stop`. E a janela é frágil por construção — acrescentar uma tabela com primeira célula em backticks em qualquer ponto entre `:189` e `:266` amplia a isenção sem aviso.
- **Proposta:** trocar o terminador do `awk` por uma linha em branco após a tabela, ou por `/^#{3,4} /` (que para em `#### User-Invocable Commands`), fechando a janela em `:206`.
- **Impacto positivo:** devolve 2 skills à cobertura de órfãos e torna a janela insensível a tabelas novas no mesmo bloco `### Skills`.
- **Impacto negativo / risco:** se alguém tiver passado a contar com a isenção larga, o scanner pode começar a emitir ACTION REQUIRED em skills hoje silenciosas; e o `Stop` roda esse script sem supervisão, então um terminador estrito demais reduz a lista de isenções legítimas e produz falso positivo em `skill-creator`/`agent-creator`/`review`.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### `skills/devops/monitoring/references/loki-config.md` é inalcançável — nenhum arquivo do repositório aponta para ele, e nenhum gate cobre reachability de `references/`

- **Fingerprint:** `ref-monitoring-loki-config-reference-unreachable-no-gate-covers-references-dir`
- **Alvo:** `skills/devops/monitoring/references/loki-config.md`
- **Evidência:** `rg -n 'loki-config' .` devolve **apenas** o próprio arquivo. O `SKILL.md` roteia três referências e nenhuma é essa: `skills/devops/monitoring/SKILL.md:29` — "`| Prometheus + Grafana (+ Loki) | references/prometheus-grafana.md |`", `:30` cloudwatch, `:31` datadog. O irmão `prometheus-alerts.md` sobrevive por um segundo salto que `loki-config.md` não tem: `references/prometheus-grafana.md:98` — "Base alert set (ServiceDown, HighErrorRate, HighLatencyP95, DiskUsageHigh, HighMemoryUsage): see `prometheus-alerts.md`." O arquivo tem 83 linhas / 1.984 bytes. O scanner que existe pula a classe por construção: `helpers/orphan-skill-scan.sh:122-123` — "`[[ "$rel_path" == *"/references/"* ]] && continue`".
- **Problema:** um arquivo de referência shipado sem nenhum ponteiro. Como o bloco Loki está inline em `prometheus-grafana.md:123-165` (docker-compose, labels, datasource), `loki-config.md` é também conteúdo paralelo não sincronizado.
- **Por que importa:** é peso morto no pacote instalado e, mais relevante, prova que a reachability de `references/` não é verificada por gate algum — `orphan-skill-scan` isenta o diretório, `orphan-template-scan` só cobre `templates/`, e `size-limits.sh` isenta `references/` do teto de 500.
- **Proposta:** acrescentar um ponteiro em `skills/devops/monitoring/SKILL.md` (ou em `prometheus-grafana.md`, ao lado da linha `:98` que já faz isso para `prometheus-alerts.md`); em paralelo, estender a Fase 2 do `orphan-skill-scan.sh` para reportar `references/*.md` sem ponteiro a partir do `SKILL.md` do próprio diretório ou de um irmão.
- **Impacto positivo:** fecha o único `references/` comprovadamente órfão de ~120 e dá cobertura de gate a uma classe que hoje tem zero.
- **Impacto negativo / risco:** estender o scanner a `references/` aumenta o custo da Fase 2 (hoje 2 greps por skill contra um arquivo combinado) e é quase certo que produzirá ACTION REQUIRED em arquivos alcançados por prosa que o regex não reconhece — ruído recorrente no `Stop` de toda sessão, o mesmo defeito que a Fase 3 já tem.
- **Esforço:** Baixo

### A coluna "opencode-zen (premium alternative)" de `docs/providers.md` mistura namespace de provedor e recita um id que o mesmo arquivo declara defasado

- **Fingerprint:** `docs-sync-providers-md-zen-premium-column-mixes-namespaces-pinned-ids`
- **Alvo:** `docs/providers.md`
- **Evidência:** `docs/providers.md:215` — "`| reasoning | opencode-go/qwen3.7-plus | opencode/claude-opus-4-7 |`"; `:216-217` — "`opencode/gpt-5.6-terra`" em `backend-exec` e a mesma célula em `frontend`; `:218` — "`opencode/gpt-5.6-luna`". Os três ids da direita são, com o prefixo trocado, os ids **Codex** de `tiers.json` (`openai/gpt-5.6-sol|terra|luna`) e o id Anthropic que o próprio arquivo aposentou: `:51` — "It previously held pinned ids (`claude-opus-4-7`, `claude-sonnet-4-6`) and had drifted a generation behind." Os únicos exemplos zen que o documento dá são de outra família: `:204-206` — "`opencode/gpt-5.1-codex`", "`opencode/claude-sonnet-4-6`", "`opencode/kimi-k2.7-code`". `grep -n zen docs/providers.md` devolve só `:183`, `:184`, `:213` — não existe catálogo zen para conferir nenhum dos quatro.
- **Problema:** uma coluna de sugestão cujos valores não vêm de `tiers.json`, não aparecem no catálogo do próprio arquivo, e contradizem a seção que explica por que ids pinados foram abandonados.
- **Por que importa:** o documento é o mapa tier→modelo dos provedores e `:220-221` convida à substituição — "The premium column is a suggested substitution — changing it here changes nothing; edit `tiers.json` to change what ships." Quem seguir a sugestão copia para `tiers.json` um id de namespace trocado e um `claude-opus-4-7` pinado, revertendo na prática a decisão de `:51`. Sem consequência funcional hoje: o renderer lê só a primeira coluna.
- **Proposta:** substituir a coluna por ids zen realmente presentes em `:204-206` (ou removê-la e deixar só a frase de `:220-221`), e nunca reusar um id `openai/` com prefixo `opencode/`.
- **Impacto positivo:** elimina 4 ids não verificáveis de um documento de referência e remove a contradição com `:51`.
- **Impacto negativo / risco:** remover a coluna tira do leitor a única dica de caminho premium que o repo oferece; mantê-la corrigida cria mais uma tabela de ids de modelo a envelhecer, exatamente o problema que a troca por aliases resolveu no lado Claude — e nenhum gate valida ids zen.
- **Esforço:** Baixo

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidente |
|---|---|---|
| `docs/agents.md:28` diz `repetitive` para `backend-test-specialist` (real `backend-exec`), espelhado no pt-BR | 5 (estado) | `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive` |
| `scripts/install.sh` sem `auto_learn_before_commit` no heredoc de fallback | 5 (estado) | `auto-install-heredoc-omits-auto-learn-before-commit` |
| `README.pt-BR.md:141` linka `docs/agents.md` (EN) enquanto `:15` linka `docs/agents.pt-BR.md` | 5 (estado) | `docs-sync-readme-ptbr-agents-link-points-to-english-doc` |
| `size-limits.sh` saindo 1 por `CLAUDE.md: 602 lines` | 5 (estado) | `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` |
| `CLAUDE.md:158` "12 items" para a Context Loading Order (são 11) | 5 (estado) | `docs-sync-claude-md-context-list-item-count-12-vs-11` |
| `CLAUDE.md:64` restringe `effort:` ao tier `repetitive` enquanto 5 agentes de outros tiers têm `low` | 5 (estado) | `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map` |
| `CLAUDE.md:386` diz `telemetry` nasce `true`; `install.sh` escreve `false` | 5 (estado) | `docs-sync-telemetry-fresh-install-default-documented-true-…` |
| `CLAUDE.md` § File Structure não lista `docs/user-preferences.md`, `docs/credentials.local.md`, `docs/harness.md`, `docs/prompts/` | 3 (3/3 contra a família) | `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-…` |
| `commands/update.md` referenciando `hooks/pre-tool-use/01-check-updates.sh` (é `_disabled-01-…`) | 3 (3/3) | `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook` |
| `CLAUDE-md/hooks.md:73` citando `stop/04-notifier.sh` como vivo | 3 (3/3) | `ref-notifier-documented-as-live-in-four-docs-while-hook-file-is-disabled` |
| As 3 "cargas duplicadas" do `orphan-skill-scan` (`test-pyramid` ×2, `worktree` ×1) | 3 (alvo + causa raiz) | `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-…` (falsos positivos do scanner, verificados em 2026-08-21) |
| Tabela de comandos do `README` omitindo `/devteam:install` | 5 (estado) | `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` |
| Referências quebradas a `skills/shared/workflow-detection/SKILL.md`, `skills/ui-libraries/jquery/SKILL.md`, `skills/shared/learn-nudge/SKILL.md`, `skills/shared/model-identity/references/format.md` | — (refutado por evidência) | Todas em `CHANGELOG.md:601` ou em relatórios históricos; nenhuma em superfície viva |
| `agents/mobile-test-specialist.md` citado e inexistente | — (refutado) | `docs/development/adrs/0006-mobile-pipeline-architecture.md:17-18` é a **opção A rejeitada** do ADR |
