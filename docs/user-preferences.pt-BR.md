# Preferências do Usuário

Referência de `.dev-team-agents/user-data/preferences.json`, incluindo defaults, comportamento e como o isolamento com worktree é configurado.

---

## Índice

- [Resumo](#resumo)
- [Local do Arquivo](#local-do-arquivo)
- [Schema Padrão](#schema-padrão)
- [Referência das Preferências](#referência-das-preferências)
- [Isolamento com Worktree](#isolamento-com-worktree)
- [Controles de Notificação e Contexto](#controles-de-notificação-e-contexto)
- [Configurações Guiadas por Consentimento](#configurações-guiadas-por-consentimento)
- [Política de Idioma](#política-de-idioma)
- [Documentos Relacionados](#documentos-relacionados)

---

## Resumo

`preferences.json` é o arquivo de configuração local do usuário para o Dev Team Agents. Ele controla idioma de conversa, thresholds de notificação, comportamento de atualização, defaults de worktree e outras preferências locais de execução.

Esse arquivo não deve ser commitado e é preservado nas atualizações.

---

## Local do Arquivo

```text
.dev-team-agents/user-data/preferences.json
```

Os defaults canônicos ficam em:

```text
scripts/lib/preferences-defaults.json
```

---

## Schema Padrão

```json
{
  "language": "pt-BR",
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "session_summary_max_days": 30,
  "session_summary_max_entries": 30,
  "docs_stale_after_days": 30,
  "auto_update": true,
  "update_check_interval_hours": 24,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000,
  "session_no_commit_turns": 8,
  "telemetry": true,
  "worktree_active": true,
  "worktree_base_branch": null,
  "worktree_commit_action": "ask",
  "worktree_path": ".worktrees",
  "worktree_docker_isolate": true,
  "qa_browser": null,
  "ci_cd_detected": null
}
```

---

## Referência das Preferências

| Chave | Padrão | Tipo | O que controla |
|-------|--------|------|----------------|
| `language` | `"pt-BR"` | string | Idioma usado quando os agentes falam diretamente com o usuário |
| `context_window_percent_warning` | `55` | number | Threshold para warnings de uso de contexto |
| `context_window_percent_limit` | `60` | number | Threshold para alertas críticos de uso de contexto |
| `suppress_notifications` | `false` | bool ou array | Política de supressão de notificações |
| `session_summary_max_days` | `30` | number | Janela de retenção do resumo de sessão |
| `session_summary_max_entries` | `30` | number | Número máximo de entradas retidas no resumo |
| `docs_stale_after_days` | `30` | number | Limiar de desatualização para docs mantidos |
| `auto_update` | `true` | bool | Se a checagem de atualização pode aplicar updates automaticamente |
| `update_check_interval_hours` | `24` | number | Intervalo entre checagens de atualização |
| `transcript_multiplier` | `1.8` | number | Campo legado de compatibilidade; não é mais aplicado |
| `model_max_tokens` | `200000` | number | Tamanho assumido da janela de contexto para warnings |
| `session_no_commit_turns` | `8` | number | Número de turns antes de avisar sobre sessão suja sem commit |
| `telemetry` | `true` | bool | Flag de opt-in para telemetria anônima |
| `worktree_active` | `true` | bool | Se tasks de codificação devem usar worktree isolada por padrão |
| `worktree_base_branch` | `null` | string ou null | Base branch preferida para novas worktrees |
| `worktree_commit_action` | `"ask"` | string | Comportamento padrão do `/devteam:commit` dentro de worktree ativa |
| `worktree_path` | `".worktrees"` | string | Diretório-raiz onde as worktrees são criadas |
| `worktree_docker_isolate` | `true` | bool | Se Docker Compose deve ser isolado por worktree |
| `qa_browser` | `null` | string ou null | Navegador preferido para o agente de QA |
| `ci_cd_detected` | `null` | bool ou null | Estado em cache da detecção de CI/CD |

---

## Isolamento com Worktree

O comportamento de worktree é guiado principalmente por cinco preferências:

| Chave | Padrão | Efeito |
|-------|--------|--------|
| `worktree_active` | `true` | Cria uma worktree por task de codificação sem prompt nas instalações modernas |
| `worktree_base_branch` | `null` | Usa uma base branch fixa ou detecta a branch padrão do repositório |
| `worktree_commit_action` | `"ask"` | Controla se o fluxo de commit pergunta, faz rebase, finaliza ou apenas commita |
| `worktree_path` | `".worktrees"` | Define onde as worktrees geradas ficam |
| `worktree_docker_isolate` | `true` | Cria namespace isolado para recursos Docker Compose por worktree quando houver Docker |

### Cascata de decisão

Os agentes de codificação resolvem o isolamento nesta ordem:

1. `.dev-team-agents/.worktree-session`
2. `preferences.json`
3. Perguntar uma vez apenas em instalações legadas sem a chave de preferência

### Override de sessão

`.dev-team-agents/.worktree-session` é um override por sessão compartilhado por todos os agentes da task. Isso evita que fluxos com múltiplos agentes perguntem ou decidam diferente dentro da mesma task.

### Isolamento Docker

Quando `worktree_docker_isolate` é `true` e o projeto usa Docker Compose, os agentes podem criar um stack isolado específico da task. Containers, redes e volumes recebem namespace próprio, então o stack principal não é tocado.

### Finalização

Quando a task é finalizada, o agente faz rebase na base branch, resolve conflitos se necessário, mergeia e então derruba apenas a worktree isolada e seus recursos Docker isolados.

---

## Controles de Notificação e Contexto

Essas configurações afetam warnings de runtime e o nível de ruído local:

| Assunto | Chaves |
|---------|--------|
| Thresholds de uso de contexto | `context_window_percent_warning`, `context_window_percent_limit`, `model_max_tokens` |
| Supressão de notificações | `suppress_notifications` |
| Lembrete de sessão suja | `session_no_commit_turns` |
| Desatualização de docs mantidos | `docs_stale_after_days` |

`suppress_notifications` aceita:

- `false` para permitir todas as notificações
- `true` para suprimir todas as notificações
- arrays como `["info"]` ou `["warning", "critical"]` para suprimir níveis específicos

---

## Configurações Guiadas por Consentimento

Duas chaves são tratadas como configurações explícitas de consentimento:

| Chave | Significado |
|-------|-------------|
| `telemetry` | Relato anônimo de uso |
| `auto_update` | Aplicação automática de updates |

Elas são especiais porque valores ausentes são tratados de forma conservadora em instalações já existentes. Na prática, ausência de consentimento é lida como desativado até o usuário registrar a escolha explicitamente.

---

## Política de Idioma

As regras de idioma são separadas por tipo de saída:

| Tipo de saída | Política |
|---------------|----------|
| Conversa com o usuário | Usa `language` |
| Docs gerados, ADRs, changelogs, comentários de código | Sempre em inglês |

Essa separação mantém os artefatos do repositório estáveis, sem impedir que a sessão aconteça no idioma preferido do usuário.

---

## Documentos Relacionados

- [README](../README.pt-BR.md)
- [Arquitetura do Harness](harness.pt-BR.md)
- [Opções de Instalação](installation.pt-BR.md)
- [Referência de Credentials](credentials.local.pt-BR.md)
