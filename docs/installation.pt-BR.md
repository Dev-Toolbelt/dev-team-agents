# Instalação — Opções Avançadas

Este documento cobre pin de versão, atualizações, configuração de idioma, atualizações automáticas e ajuste de notificações. Para o install de uma linha, veja o [README](../README.pt-BR.md#como-instalar).

---

## Instalar uma Versão Específica

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash -s v1.0.0
```

Substitua `v1.0.0` por qualquer tag publicada. As tags disponíveis estão listadas na [página de releases do GitHub](https://github.com/Dev-Toolbelt/dev-team-agents/releases).

---

## Atualizar para a Versão Mais Recente

Após o primeiro install, atualize executando:

```bash
.claude/dev-team-agents/scripts/update.sh
```

O script baixa o tarball da versão mais recente, substitui o diretório do pacote e recria os symlinks. Seu diretório `user-data/` nunca é tocado durante atualizações.

---

## Pin de Versão Específica / Downgrade

```bash
.claude/dev-team-agents/scripts/update.sh v1.0.0
```

Passe qualquer tag de versão para instalar exatamente aquela versão, independentemente do que está instalado atualmente.

---

## Atualizações Automáticas (opt-in)

Habilite atualizações automáticas para que a verificação diária aplique novas versões em vez de apenas notificar:

```bash
.claude/dev-team-agents/scripts/update.sh --enable-auto
```

Desabilite a qualquer momento:

```bash
.claude/dev-team-agents/scripts/update.sh --disable-auto
```

Você também pode alternar isso em `.claude/user-data/preferences.json`:

```json
{ "auto_update": true }
```

A verificação de atualização executa uma vez por dia. O intervalo é configurável:

```json
{ "update_check_interval_hours": 24 }
```

---

## Preferência de Idioma

Durante a instalação, o instalador pergunta em qual idioma os agentes devem conversar com você. Planos apresentados para aprovação e todas as respostas diretas usam o idioma configurado. Documentos (ADRs, changelogs, comentários de código) permanecem sempre em inglês.

Atualize a qualquer momento editando `.claude/user-data/preferences.json`:

```json
{ "language": "pt-BR" }
```

Valores comuns: `en` · `pt-BR` · `es` · `fr` · `de` · `ja` · `zh-CN`

---

## Sistema de Notificações

Agentes e hooks emitem notificações no formato DEV TEAM AGENTS ao longo das suas sessões:

- **ℹ️ info** — dicas rotativas e boas práticas (uma por sessão)
- **⚠️ warning** — janela de contexto se aproximando do limite, docs desatualizados, config ausente
- **🚨 critical** — janela de contexto no limite, instalação quebrada

Configure em `.claude/user-data/preferences.json`:

```json
{
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000
}
```

| Chave | Padrão | Propósito |
|-------|--------|-----------|
| `context_window_percent_warning` | `55` | % a partir da qual um warning é emitido |
| `context_window_percent_limit` | `60` | % a partir da qual um alerta crítico é emitido |
| `suppress_notifications` | `false` | `false` / `true` / `["info"]` |
| `transcript_multiplier` | `1.8` | Multiplicador aplicado à contagem de tokens do transcript para estimar o contexto completo |
| `model_max_tokens` | `200000` | Janela de contexto do modelo ativo |

Defina `suppress_notifications` como `true` para silenciar todas as notificações, ou como `["info"]` para suprimir apenas as dicas.

Os warnings de janela de contexto usam contagens de tokens do transcript (do payload do hook Stop) multiplicadas por `transcript_multiplier`. Ajuste `transcript_multiplier` para cima se os warnings dispararem cedo demais, ou para baixo se dispararem tarde demais. Defina `model_max_tokens` para corresponder à janela de contexto real do seu modelo caso troque por um modelo não-200k.

---

## Versionamento

Este repositório usa versionamento semântico via git tags (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- Atualizações são lançadas como tags — sem auto-update a cada commit
- Um hook verifica novas versões uma vez por dia via GitHub API (configurado automaticamente pelo `install.sh`)
- Por padrão o sistema apenas notifica — execute `update.sh` para aplicar, ou habilite auto-updates conforme acima

**Política de bump de versão:**
- Mudanças quebradoras (alterações de comportamento de agente, skills removidas) → major
- Novos agentes ou skills → minor
- Correções e clarificações → patch

---

## Layout de Diretórios Após Instalação

```
.claude/
├── dev-team-agents/        ← extraído do tarball (sem .git — seguro para commit)
├── user-data/              ← estado e configuração do usuário (preservado nas atualizações)
│   ├── preferences.json        ← idioma, thresholds, configurações de notificação (gitignored)
│   ├── graphify.json           ← config do Graphify — faça commit deste
│   ├── session-summary.md      ← gitignored
│   ├── .installed-version      ← gitignored
│   └── .last-update-check      ← gitignored
├── agents/
│   └── dev-team/           ← symlink → .claude/dev-team-agents/agents/
├── skills/
│   ├── project-context/    ← symlink → diretório da skill
│   └── ...                 ← um symlink por skill
├── commands/
│   └── devteam/            ← symlink → commands/ (invoque como /devteam:plan etc.)
└── settings.json           ← dispatchers de hook configurados automaticamente
```

## Commitando a Instalação

Como o `install.sh` baixa um tarball (não faz git clone), `.claude/dev-team-agents/` não tem pasta `.git` aninhada. **Commite diretamente** para que todo o time receba os agentes no `git pull`:

```bash
git add .claude/dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

Se preferir que cada desenvolvedor instale localmente:

```gitignore
# Opcional: ignorar a instalação (cada desenvolvedor instala localmente)
.claude/dev-team-agents/
.claude/agents/dev-team/
.claude/skills/
.claude/commands/devteam/
.claude/.worktree-session
```
