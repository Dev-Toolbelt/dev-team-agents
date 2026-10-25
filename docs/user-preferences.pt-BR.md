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

Esse caminho vale para uma instalação v2 ainda não vinculada. **Num projeto vinculado com `devteam bind`**,
as preferências seguem a cascata defaults → global → projeto, a camada do projeto fica no store e os
agentes leem o arquivo gerado `.dev-team-agents/resolved/preferences.json`. Altere um valor com
`devteam prefs set <chave> <valor> --scope project` ou pelas configurações do projeto no app desktop. O
`bind` importa um `user-data/preferences.json` existente para a camada do projeto e move o arquivo para
a quarentena do store.

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
  "model_max_tokens": 200000,
  "session_no_commit_turns": 8,
  "telemetry": true,
  "worktree_active": true,
  "worktree_base_branch": null,
  "worktree_commit_action": "ask",
  "auto_learn_before_commit": true,
  "worktree_path": ".worktrees",
  "worktree_docker_isolate": true,
  "qa_browser": null,
  "review_gate_mode": "ask",
  "ci_cd_detected": null,
  "recall_active": true,
  "check_active": true,
  "repair_hints_active": true,
  "branch_overlap_active": true
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
| `model_max_tokens` | `200000` | number | Tamanho assumido da janela de contexto para warnings |
| `session_no_commit_turns` | `8` | number | Número de turns antes de avisar sobre sessão suja sem commit |
| `telemetry` | `true` | bool | Flag de opt-in para telemetria anônima |
| `worktree_active` | `true` | bool | Se tasks de codificação devem usar worktree isolada por padrão |
| `worktree_base_branch` | `null` | string ou null | Base branch preferida para novas worktrees |
| `worktree_commit_action` | `"ask"` | string | Comportamento padrão do `/devteam:commit` dentro de worktree ativa |
| `auto_learn_before_commit` | `true` | bool | Executa `/devteam:learn` silenciosamente antes de todo `/devteam:commit`, sem pedir aprovação (`false` = pula por padrão) |
| `worktree_path` | `".worktrees"` | string | Diretório-raiz onde as worktrees são criadas |
| `worktree_docker_isolate` | `true` | bool | Se Docker Compose deve ser isolado por worktree |
| `qa_browser` | `null` | string ou null | Navegador preferido quando o browser do app não está disponível — testes de QA e a conferência visual após trabalho de UI |
| `review_gate_mode` | `"ask"` | string | O que acontece quando um trabalho que alterou código termina: `ask` mostra a escolha de review, `auto` roda o review recomendado sem perguntar, `skip` vai direto para o hand-off de commit/PR |
| `ci_cd_detected` | `null` | bool ou null | Estado em cache da detecção de CI/CD |
| `recall_active` | `true` | bool | Ponteiros de recall por prompt a partir dos índices de ADR, wiki e reuso (ADR-0048) |
| `check_active` | `true` | bool | Pré-checagem `devteam check` que compara o diff da branch com as decisões da base em `/devteam:pr` e `/devteam:push` (ADR-0049) |
| `repair_hints_active` | `true` | bool | Dicas de reparo vindas do ledger local de reparos após falhas repetidas de comando (ADR-0051) |
| `branch_overlap_active` | `true` | bool | Avisos de edições sobrepostas em branches não mergeadas de colegas (ADR-0052) |

---

## Isolamento com Worktree

O comportamento de worktree é guiado principalmente por cinco preferências:

| Chave | Padrão | Efeito |
|-------|--------|--------|
| `worktree_active` | `true` | Cria uma worktree por task de codificação sem prompt nas instalações modernas |
| `worktree_base_branch` | `null` | Usa uma base branch fixa ou detecta a branch padrão do repositório |
| `worktree_commit_action` | `"ask"` | Controla se o fluxo de commit pergunta, faz rebase, finaliza ou apenas commita |
| `auto_learn_before_commit` | `true` | Executa `/devteam:learn` silenciosamente antes de cada commit — os docs gerados entram nos commits do trabalho; `false` pula por padrão |
| `worktree_path` | `".worktrees"` | Define onde as worktrees geradas ficam |
| `worktree_docker_isolate` | `true` | Cria namespace isolado para recursos Docker Compose por worktree quando houver Docker |

### Entrega de contexto

| Chave | Padrão | Efeito |
|-------|--------|--------|
| `recall_active` | `true` | Ponteiros de recall por prompt a partir dos índices de ADR, wiki e reuso (ADR-0048); `false` desliga |
| `check_active` | `true` | Pré-checagem `devteam check` que compara o diff da branch com as decisões da base em `/devteam:pr` e `/devteam:push` (ADR-0049); `false` desliga |
| `repair_hints_active` | `true` | Dicas de reparo vindas do ledger local de reparos após falhas repetidas de comando (ADR-0051); `false` desliga |
| `branch_overlap_active` | `true` | Avisos de edições sobrepostas em branches não mergeadas de colegas (ADR-0052); `false` desliga |

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

Três chaves são tratadas como configurações explícitas de consentimento:

| Chave | Significado |
|-------|-------------|
| `telemetry` | Relato anônimo de uso |
| `auto_update` | Aplicação automática de updates |
| `branch_overlap_active` | Fetch periódico para avisar sobre edições sobrepostas em branches de colegas |

Elas são especiais porque valores ausentes são tratados de forma conservadora em instalações já existentes. Na prática, ausência de consentimento é lida como desativado até o usuário registrar a escolha explicitamente. Exceção: num projeto v3 (store global), `branch_overlap_active` resolve para `true` a menos que você o defina — desligue com `devteam prefs set branch_overlap_active false --scope project`.

---

## Política de Idioma

As regras de idioma são separadas por tipo de saída:

| Tipo de saída | Política |
|---------------|----------|
| Conversa com o usuário | Usa `language` |
| Docs gerados, ADRs, changelogs, comentários de código | Sempre em inglês |

Essa separação mantém os artefatos do repositório estáveis, sem impedir que a sessão aconteça no idioma preferido do usuário.

Quando `language` não é inglês, o banner da sessão o declara como instrução, e um hook `UserPromptSubmit` o reforça a **cada prompt** (uma linha `[DEVTEAM:LANGUAGE]`), para que uma sessão longa não passe para o inglês depois de um commit ou session summary em inglês. Claude Code e Codex recebem a linha como contexto do prompt; no opencode, o plugin a adiciona ao system prompt. Com `language: en` nada é adicionado.

---

## Documentos Relacionados

- [README](../README.pt-BR.md)
- [Arquitetura do Harness](harness.pt-BR.md)
- [Opções de Instalação](installation.pt-BR.md)
- [Referência de Credentials](credentials.local.pt-BR.md)
