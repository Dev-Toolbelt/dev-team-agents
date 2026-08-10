# Instalação — Opções Avançadas

Este documento cobre pin de versão, atualizações, configuração de idioma, atualizações automáticas e ajuste de notificações. Para o install de uma linha, veja o [README](../README.pt-BR.md#como-instalar).

> **Escopo — a instalação do Claude Code** (`scripts/install.sh`). Caminhos específicos do Claude como `.claude/` e `.claude/settings.json` estão corretos aqui e não são o único caminho de instalação. Para os demais CLIs suportados, veja [install-opencode.md](install-opencode.md) e [install-codex.md](install-codex.md).

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
.dev-team-agents/scripts/update.sh
```

O script baixa o tarball da versão mais recente, substitui o diretório do pacote e recria os symlinks. Seu diretório `user-data/` nunca é tocado durante atualizações.

---

## Pin de Versão Específica / Downgrade

```bash
.dev-team-agents/scripts/update.sh v1.0.0
```

Passe qualquer tag de versão para instalar exatamente aquela versão, independentemente do que está instalado atualmente.

---

## Atualizações Automáticas (opt-in)

Habilite atualizações automáticas para que a verificação diária aplique novas versões em vez de apenas notificar:

```bash
.dev-team-agents/scripts/update.sh --enable-auto
```

Desabilite a qualquer momento:

```bash
.dev-team-agents/scripts/update.sh --disable-auto
```

Você também pode alternar isso em `.dev-team-agents/user-data/preferences.json`:

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

Atualize a qualquer momento editando `.dev-team-agents/user-data/preferences.json`:

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

Configure em `.dev-team-agents/user-data/preferences.json`:

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
| `transcript_multiplier` | `1.8` | Descontinuado, não é mais aplicado (veja abaixo) |
| `model_max_tokens` | `200000` | Janela de contexto do modelo ativo |

Defina `suppress_notifications` como `true` para silenciar todas as notificações, ou como `["info"]` para suprimir apenas as dicas.

Os warnings de janela de contexto lêem a contagem de tokens de cache/input da última entrada de uso do transcript (do payload do hook Stop) — o tamanho exato do contexto enviado na última chamada à API, sem necessidade de multiplicador. `transcript_multiplier` permanece no schema por compatibilidade retroativa, mas não tem mais efeito. Defina `model_max_tokens` para corresponder à janela de contexto real do seu modelo caso troque por um modelo não-200k.

### Worktree e isolamento Docker

Controle como os agentes de codificação isolam o trabalho, no mesmo `preferences.json`:

```json
{
  "worktree_active": false,
  "worktree_base_branch": null,
  "worktree_commit_action": "ask",
  "worktree_path": ".worktrees",
  "worktree_docker_isolate": true
}
```

| Chave | Padrão | Propósito |
|-------|--------|-----------|
| `worktree_active` | `false` | Quando `true`, os agentes criam uma worktree por task **sem perguntar** |
| `worktree_base_branch` | `null` | Base branch para novas worktrees (`null` = auto-detectar a branch padrão do repo) |
| `worktree_commit_action` | `"ask"` | O que `/devteam:commit` faz em uma worktree ativa: `ask`, `finalize`, `rebase` ou `commit-only` |
| `worktree_path` | `".worktrees"` | Onde as worktrees são criadas (`<path>/<contexto>/<título>`) |
| `worktree_docker_isolate` | `true` | Com `worktree_active` e um projeto Docker Compose, sobe um stack isolado por worktree (containers/volumes/redes namespaceados, portas não publicadas) |

O arquivo de sessão `.dev-team-agents/.worktree-session` sobrepõe esses defaults para uma única task. No merge, os agentes fazem rebase na base branch, mergeiam e derrubam somente a worktree e seu stack Docker isolado. As quatro chaves são preenchidas automaticamente com esses defaults a cada sessão, se estiverem ausentes.

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
│   └── dev-team/           ← symlink → .dev-team-agents/agents/
├── skills/
│   ├── project-context/    ← symlink → diretório da skill
│   └── ...                 ← um symlink por skill
├── commands/
│   └── devteam/            ← symlink → commands/ (invoque como /devteam:plan etc.)
└── settings.json           ← dispatchers de hook configurados automaticamente
```

## Commitando a Instalação

Como o `install.sh` baixa um tarball (não faz git clone), `.dev-team-agents/` não tem pasta `.git` aninhada. **Commite diretamente** para que todo o time receba os agentes no `git pull`:

```bash
git add .dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

Se preferir que cada desenvolvedor instale localmente:

```gitignore
# Opcional: ignorar a instalação (cada desenvolvedor instala localmente)
.dev-team-agents/
.claude/agents/dev-team/
.claude/skills/
.claude/commands/devteam/
.dev-team-agents/.worktree-session
```

### Windows: symlinks em uma instalação commitada

`.claude/agents/dev-team`, `.claude/commands/devteam` e cada `.claude/skills/<nome>` são **symlinks** (modo git `120000`). Quando alguém do time no Windows clona ou faz checkout de um repo que os commitou, o git só cria symlinks reais se houver suporte nativo — **Modo Desenvolvedor ligado, processo elevado ou `core.symlinks=true`**. Caso contrário, o git/MSYS escreve o caminho de destino de cada link em um arquivo de texto comum de ~62 bytes.

Essa falha passa fácil despercebida: o `ls -la` do `git-bash` ainda mostra os links falsos como `lrwxrwxrwx` (emulação do MSYS), mas o Windows e o Claude Code enxergam arquivos comuns — então todo o dev-team falha silenciosamente ao carregar (`/devteam:*`, agentes e skills somem). Confirme o estado real com `test -L` em vez de `ls`:

```bash
test -L .claude/commands/devteam && echo "link" || echo "quebrado"
```

Repare com o helper incluído, que corrige automaticamente quando o SO permite e, caso contrário, imprime as três opções de remediação (Modo Desenvolvedor, terminal elevado ou rodar o Claude Code como administrador):

```bash
bash .dev-team-agents/scripts/fix-symlinks.sh
```

Reinicie o Claude Code após o reparo para que ele reindexe comandos, agentes e skills. Ligar o Modo Desenvolvedor é a correção duradoura — ela também cobre clones futuros deste e de outros repos, sem nenhum passo de administrador.

De dentro do Claude Code você pode rodar o mesmo reparo como comando — `/devteam:symlinks` — que detecta o SO, executa o helper e guia você pela correção do SO quando os symlinks nativos estão bloqueados. Se os links estiverem quebrados a ponto de os comandos `/devteam:` não carregarem, rode o script `fix-symlinks.sh` diretamente como mostrado acima.
