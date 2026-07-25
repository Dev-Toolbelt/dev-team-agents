# Fluxos e Workflows — 2026-05-24

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 493 fingerprints (`_index.md`) e são inéditas.

---

## F1 — O `CHANGELOG.md` está **3 versões minor atrás das tags git**: `v1.5.0`…`v1.7.0` já foram criadas e lançadas, mas a última seção documentada é `[1.4.0]` — viola a Auto-Docs Rule e a política de versionamento

**Severidade:** HIGH
**Fingerprint:** `auto-changelog-three-minor-versions-behind-git-tags-v1-5-0-through-v1-7-0-tagged-and-shipped-content-stuck-in-unreleased-head-is-v1-7-0`

**Evidência:**

```
# Tags existentes (todas apontam para commits desta história)
v1.4.0   0ae9595  2026-05-10
v1.5.0   e6719f7  2026-05-11   feat(hooks): apply DEV TEAM AGENTS notifier format …
v1.5.1 … v1.5.5   2026-05-11
v1.6.0   1a5c511  2026-05-11   feat(skills): add Material Design 3 and iOS HIG …
v1.6.1 … v1.6.7   2026-05-12 … 2026-05-18
v1.7.0   9f1826d  2026-05-18   docs(telemetry): add PRIVACY.md …      ← HEAD do repo

# CHANGELOG.md — últimas seções de release
:10  ## [Unreleased]
:43  ## [1.4.0] — 2026-05-10        ← a "última release" segundo o doc
```

O `HEAD` (`9f1826d`) **é** a tag `v1.7.0`. Tudo o que está em `[Unreleased]` (telemetria, notifier, iOS/Android, helpers, README restructure…) **já foi lançado** sob `v1.5.0`–`v1.7.0`.

**Motivo:** este é o achado que **reposiciona** a pendência de CHANGELOG de 2026-05-18. Não é "esquecemos de preencher `[Unreleased]`" — é "**lançamos 13 versões (6 minor/patch além de 1.4.0) sem promover nenhuma seção do CHANGELOG**". Isso viola duas regras do próprio projeto simultaneamente: a **Auto-Docs Rule** (mudanças observáveis exigem CHANGELOG na mesma sessão) e a **política de versionamento** (`versioning.md`: "Semantic versioning via git tags"). Para qualquer consumidor que leia o CHANGELOG, o projeto "está em 1.4.0"; para o git, está em `v1.7.0`. Distinto de `auto-docs-rule-violated-changelog-unreleased-missing-7-features` (que era sobre o **conteúdo** faltando em `[Unreleased]`): aqui o achado é a **deriva entre tags e CHANGELOG**, descoberta só ao cruzar `git tag`.

**Impacto positivo da correção:** promover `[Unreleased]` para as seções datadas `## [1.5.0]`, `## [1.6.0]`, `## [1.7.0]` (com base nas datas/títulos das tags) reconcilia doc × tags e restaura a confiança no CHANGELOG. Abre espaço para um `[Unreleased]` limpo. Idealmente acompanhado de um check de CI que falhe quando a tag mais recente não tem seção correspondente no CHANGELOG.

**Impacto negativo / risco:** baixo. Trabalho de curadoria (decidir qual entrada do `[Unreleased]` pertence a qual tag) — mitigável usando `git log v1.4.0..v1.7.0 --oneline` como guia. Risco de erro na atribuição feature→versão, aceitável e corrigível.

---

## F2 — `telemetry-send.sh` tem comentários **contraditórios** sobre a chave do PostHog ("intentionally public" vs "Replace … before release") — um TODO de pré-release num caminho que **dispara por padrão** (telemetry=true)

**Severidade:** MEDIUM-HIGH
**Fingerprint:** `gov-telemetry-send-sh-posthog-key-comments-self-contradict-intentionally-public-vs-replace-before-release-todo-on-default-on-path`

**Evidência** — `scripts/helpers/telemetry-send.sh:24-26`:

```bash
# The capture API key is intentionally public (client-side key, not secret).
# Replace POSTHOG_API_KEY with the real project key before release.
POSTHOG_API_KEY="${DEVTEAM_POSTHOG_KEY:-phc_wBFupbyPPEw8DWTJd8Z8UAjNMxwHJusBEPJsrURsQ93a}"
```

E o default do consumo, `CLAUDE-md/preferences.md:37`:

```
| `telemetry` | `true` | Anonymous usage telemetry (set to `false` to opt out) |
```

**Motivo:** os dois comentários se contradizem — a linha 24 diz que a chave é final ("intentionally public"), a linha 25 diz que é placeholder ("Replace … before release"). Como `telemetry` **default true** e o evento de install já é enfileirado (`install.sh:530`) e flushado no Stop, **toda instalação nova começa a enviar eventos para essa chave**. Se for placeholder, os dados vão para um projeto errado/inexistente; se for final, o comentário "before release" é enganoso e fica como dívida latente. É o **único TODO de pré-release** que sobrou no código de runtime (a varredura por `TODO|FIXME|before release` no repo retorna só este, fora exemplos em skills). Distinto de `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install` (que trata do **default true sem prompt**): aqui o achado é o **TODO de chave não resolvido** num caminho default-on.

**Impacto positivo da correção:** resolver a contradição (decidir se a chave é a final e remover o comentário "before release", **ou** substituí-la) elimina ambiguidade e garante que a telemetria default-on aponte para o destino certo. Acrescentar uma asserção que falha o build/CI se a chave ainda for o placeholder fecharia a classe.

**Impacto negativo / risco:** baixo no código; **sensível em privacidade** — telemetria default-on é uma decisão de produto. A recomendação aqui é estritamente sobre **resolver o TODO/contradição**, não sobre mudar a política de opt-in/opt-out (que tem seu próprio fingerprint). Mitigação: tratar a resolução da chave e a decisão de default como itens separados.

---

## F3 — `.gitignore` tem uma **linha malformada** que funde duas entradas num path inexistente — `.dev-team-agents/user-data/` e `.notifier-state` **não estão sendo ignorados** (causa-raiz da nota recorrente de "user-data não-rastreado")

**Severidade:** MEDIUM
**Fingerprint:** `gov-gitignore-malformed-line-merges-notifier-state-and-user-data-dir-into-one-nonexistent-path-user-data-untracked-confirmed-by-check-ignore`

**Evidência** — `.gitignore` (última linha, via `cat -A`):

```
6  .dev-team-agents/user-data/session-summary.md
7  .dev-team-agents/user-data/.notifier-stateuser-data/$      ← duas entradas coladas

# Prova:
$ git check-ignore -v .dev-team-agents/user-data/        → (sem saída: NÃO ignorado)
$ git check-ignore -v .dev-team-agents/user-data/.notifier-state → (sem saída: NÃO ignorado)
```

A linha 7 deveria ser duas: `.dev-team-agents/user-data/.notifier-state` **e** `.dev-team-agents/user-data/` (ou `user-data/`). Coladas, viram um path que não casa com nada.

**Motivo:** por **5 passadas** os relatórios anotaram `.dev-team-agents/user-data/` como *untracked* tratando como "esqueceram de commitar". A causa real é este bug de `.gitignore`. Além disso, contradiz o comportamento documentado: `CLAUDE-md/user-data.md:24` diz que o instalador adiciona "`.dev-team-agents/user-data/` (entire directory)" ao ignore — mas o `.gitignore` **deste repo** só ignora `session-summary.md` e tem a linha quebrada, então o diretório inteiro vaza para o status do git. É um bug isolado (o `.gitignore` é stripado do pacote, então afeta só o repo dev), mas é a causa-raiz de uma nota que reaparece todo dia.

**Impacto positivo da correção:** separar a linha 7 em duas entradas válidas (`.dev-team-agents/user-data/.notifier-state` + `.dev-team-agents/user-data/`) faz `git status` parar de mostrar `user-data/` como untracked e **encerra a nota operacional recorrente** das auditorias. Alinha o repo dev ao comportamento que o instalador aplica aos projetos dos usuários.

**Impacto negativo / risco:** mínimo. Atenção única: se algum arquivo de `user-data/` já estiver **rastreado** no índice, será preciso `git rm --cached` antes do ignore valer. Como o `git status` mostra `user-data/` como `??` (untracked), nada está rastreado — o ignore passa a valer imediatamente, sem perda.
