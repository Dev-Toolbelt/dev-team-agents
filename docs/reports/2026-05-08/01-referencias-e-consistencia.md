# 1. Referências e Consistência (Scripts, CLAUDE.md, Templates, Dogfooding)

← [Voltar ao índice](index.md)

Esta seção foca em **inconsistências silenciosas** entre o que o repositório declara e o que ele efetivamente executa: scripts duplicados que ninguém percebeu, comandos que apontam para arquivos legados, pastas declaradas em estrutura mas subutilizadas e — mais sutil — o fato de o próprio repositório `dev-team-agents` não consumir suas próprias regras de hook.

---

## 1.1 `scripts/check-updates.sh` é um duplicata fantasma de `01-check-updates.sh`

O arquivo `scripts/check-updates.sh` (72 linhas) **não é mais consumido pelo dispatcher de hooks**. O dispatcher real (`scripts/hooks/pre-tool-use.sh`) executa o sub-script `pre-tool-use/01-check-updates.sh` (91 linhas), que é uma **versão evoluída** com auto-update embutido.

Confirmação por `diff`:

```text
< scripts/check-updates.sh                          (legado, 72 linhas)
> scripts/hooks/pre-tool-use/01-check-updates.sh    (canônico, 91 linhas, +AUTO_UPDATE_FLAG)
```

A versão legada **não tem** o bloco de auto-update (linhas 64–79 da versão canônica). Ainda assim, dois consumidores apontam para a versão legada:

| Arquivo | Linha | Trecho |
|---------|-------|--------|
| `CLAUDE.md` | 134 | `` `/devteam:update` runs `check-updates.sh` + `update.sh` `` |
| `commands/update.md` | 21 | `bash .claude/dev-team-agents/scripts/check-updates.sh` |

Resultado prático: quando o usuário roda `/devteam:update`, ele é levado por um caminho que **diverge** do hook automático. Em uma futura mudança no comportamento de detecção (ex.: novo formato de tag, novo flag), as duas vias precisarão ser atualizadas — e a tendência é só uma ser.

> **Fingerprint:** `ref-check-updates-script-duplicate`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (consolidar)** | Uma única fonte da verdade para detecção de versão; menos linhas para manter |
| **Positivo (consolidar)** | Evita que `commands/update.md` e o hook divirjam silenciosamente |
| **Negativo (consolidar)** | Quem chama `check-updates.sh` direto via shell precisa ser migrado (3 referências externas) |

**Recomendação:** transformar `scripts/check-updates.sh` em um shim de uma linha:

```bash
#!/usr/bin/env bash
exec bash "$(dirname "${BASH_SOURCE[0]}")/hooks/pre-tool-use/01-check-updates.sh" "$@"
```

…ou removê-lo de vez e atualizar `commands/update.md` para chamar `update.sh --check` (que já delega corretamente, conforme `update.sh:23`).

---

## 1.2 `CLAUDE.md` descreve `/devteam:update` rodando dois scripts; o real é um só

Direto da tabela de comandos do `CLAUDE.md` (linha 134):

> `/devteam:update` | runs `check-updates.sh` + `update.sh` | Checking for and applying dev-team-agents updates

Mas `scripts/update.sh` linhas 22–24 já entregam o que está prometido:

```bash
if [[ "${1:-}" == "--check" ]]; then
    exec bash "$(dirname "${BASH_SOURCE[0]}")/hooks/pre-tool-use/01-check-updates.sh"
fi
```

Ou seja, `update.sh --check` **já** delega para o hook canônico. O `+ check-updates.sh` na descrição do `CLAUDE.md` está descrevendo um fluxo que não existe mais — sobrou da era pré-dispatcher.

> **Fingerprint:** `docs-sync-update-flow-claude-md`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Documento volta a refletir o código |
| **Positivo** | Reduz risco do contribuinte tentar "manter compatibilidade" com fluxo inexistente |
| **Negativo** | Mudança puramente documental — sem ganho operacional |

**Recomendação:** atualizar a linha do `CLAUDE.md` para `runs update.sh --check + update.sh` (ou mais simples: `runs update.sh`).

---

## 1.3 Pasta `templates/` é declarada como diretório de templates, mas hospeda 1 arquivo

A árvore canônica do `CLAUDE.md` (`## File Structure`) lista:

```
├── templates/       ← document templates (plan, backlog, ADR, etc.)
```

Realidade do filesystem:

```
$ ls templates/
plan-template.md
```

Os outros templates citados (ADR, backlog) **estão embutidos inline** em skills:

| Tipo | Onde mora |
|------|-----------|
| Plan | `templates/plan-template.md` ✅ |
| ADR (MADR) | inline em `skills/shared/adr/SKILL.md` linhas 21–57 |
| Backlog (overview / epic / sprint) | inline em `skills/shared/backlog-template/SKILL.md` |
| Docs (`project.md`, `architecture.md`, etc.) | inline em `skills/shared/docs-templates/SKILL.md` |

A documentação cria a expectativa de uma pasta de templates centralizada — a realidade é que cada formato vive na skill que o explica. Tem mérito (template + porquê juntos), mas o `CLAUDE.md` precisa contar essa história.

> **Fingerprint:** `ref-templates-folder-underutilized`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (corrigir CLAUDE.md)** | Contribuintes deixam de procurar `templates/adr-template.md` que não existe |
| **Positivo (consolidar em `templates/`)** | Templates ficam descobríveis fora do contexto da skill |
| **Negativo (consolidar)** | Quebra colocação template+rationale; risco de dessincronização entre `templates/` e a skill |

**Recomendação (mais leve):** atualizar a linha do `CLAUDE.md § File Structure` para refletir a realidade — `templates/` hospeda apenas plan-template; outros templates vivem nas skills correspondentes (`shared/adr`, `shared/backlog-template`, `shared/docs-templates`).

---

## 1.4 O dev-team-agents **não dogfooda** seu próprio dispatcher de Stop hook

`scripts/install.sh` (linhas 195–222) cria, em projetos do usuário, um `.claude/settings.json` com:

```json
{
  "hooks": {
    "PreToolUse": [{ "matcher": ".*", "hooks": [{ "command": "...hooks/pre-tool-use.sh" }] }],
    "Stop":       [{ "hooks": [{ "command": "...hooks/stop.sh" }] }]
  }
}
```

Já o `.claude/settings.json` **dentro do próprio repositório `dev-team-agents`** (15 linhas) registra apenas:

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "command": "scripts/orphan-skill-scan.sh --quiet" }] }]
  }
}
```

Ou seja:
- O repo **não tem** `PreToolUse` hook;
- O repo **não tem** `01-session-summary.sh` ativo, embora seja o lar do script;
- O repo **não tem** `01-check-updates.sh` ativo (faz sentido — não tem versão pra checar contra si mesmo, mas o `01-session-summary.sh` faz total sentido).

A consequência é que **as mesmas regras de "session summary obrigatório quando há commits do dia"** que vão ser empurradas em todos os projetos clientes não são aplicadas em quem desenha as regras.

> **Fingerprint:** `gov-dev-repo-no-stop-dispatcher`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (alinhar)** | `dev-team-agents` passa a sentir, em primeira mão, qualquer atrito do hook (ex.: ruído ao rodar 2x ao dia) |
| **Positivo (alinhar)** | A presença de `session-summary.md` no repo serve de exemplo vivo para contribuintes |
| **Negativo** | Hooks adicionam ~100ms ao Stop signal; mensurável em sessões curtas |
| **Negativo** | `01-session-summary.sh` exige decisão de o `session-summary.md` do repo ser commitado ou ignorado |

**Recomendação:** estender o `.claude/settings.json` do repo para registrar o dispatcher canônico em vez do `orphan-skill-scan.sh` direto (o dispatcher já roda `orphan-skill-scan.sh --quiet` via outros mecanismos do install.sh). Documentar em `CLAUDE.md` a decisão sobre versionamento do `session-summary.md` neste repo.

---

## 1.5 `setup-assistant.md` cria pasta `.claude/docs/audit/` que ninguém documenta

`agents/setup-assistant.md` Step 1b (linhas 51–77) instrui:

```bash
mkdir -p .claude/docs/audit
AUDIT_FILE=".claude/docs/audit/audit-$(date +%Y-%m-%d).md"
```

…e gera um relatório de auditoria estruturado. Mas:

- `CLAUDE.md § User Data Directory` lista apenas `.claude/dev-team-agents/` e `.claude/user-data/`;
- `README.md` e `README.pt-BR.md` não mencionam a pasta `audit/` em lugar algum;
- Não há orientação sobre se o `audit-YYYY-MM-DD.md` deve ser commitado ou ignorado.

Resultado: usuários veem uma pasta nova surgir em `.claude/docs/audit/` sem entender de onde veio nem pra que serve, e o repositório do projeto pode acumular um arquivo de auditoria por execução do `setup-assistant` em REFRESH (segundo o próprio agente, "All future audit reports… are also written to `.claude/docs/audit/`").

> **Fingerprint:** `docs-sync-setup-assistant-audit-folder`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | README documenta uma feature útil que hoje é invisível |
| **Positivo** | Decisão clara sobre versionamento evita acúmulo silencioso de arquivos no git |
| **Negativo** | Adicionar 5–10 linhas no README; mínimo |

**Recomendação:** adicionar entrada em `CLAUDE.md § User Data Directory` (ou em uma seção `Project Audit Reports`) explicando:
1. A pasta `.claude/docs/audit/` é criada pelo `setup-assistant` em modo FIRST_RUN e em re-runs de saúde;
2. Cada execução produz `audit-YYYY-MM-DD.md`;
3. Recomendação default: versionar (não gitignorar) — esses relatórios funcionam como diário institucional do projeto.

---

## 1.6 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `ref-check-updates-script-duplicate` | `scripts/check-updates.sh` é versão obsoleta de `01-check-updates.sh` |
| `docs-sync-update-flow-claude-md` | `CLAUDE.md` descreve fluxo `/devteam:update` que não existe mais |
| `ref-templates-folder-underutilized` | `templates/` tem 1 arquivo; outros templates vivem inline em skills |
| `gov-dev-repo-no-stop-dispatcher` | `dev-team-agents` não consome o próprio dispatcher de hooks |
| `docs-sync-setup-assistant-audit-folder` | `.claude/docs/audit/` é criada pelo agente mas não está documentada |
