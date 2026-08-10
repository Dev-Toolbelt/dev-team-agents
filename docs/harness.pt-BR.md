# Arquitetura do Harness

Como o Dev Team Agents funciona internamente: uma fonte canônica, múltiplos destinos de CLI, hooks compartilhados e adaptadores por provedor.

---

## Índice

- [Resumo](#resumo)
- [Fonte Canônica](#fonte-canônica)
- [Fluxo de Renderização e Instalação](#fluxo-de-renderização-e-instalação)
- [Saídas por Provedor](#saídas-por-provedor)
- [Commands, Agents e Skills](#commands-agents-e-skills)
- [Tiers de Modelo e Resolução](#tiers-de-modelo-e-resolução)
- [Hooks e Runtime Compartilhado](#hooks-e-runtime-compartilhado)
- [Por Que Essa Estrutura Existe](#por-que-essa-estrutura-existe)
- [Documentos Relacionados](#documentos-relacionados)

---

## Resumo

Dev Team Agents é um harness multi-provedor. O repositório não armazena três implementações independentes para Claude Code, opencode e Codex. Em vez disso, ele armazena uma única fonte canônica e renderiza as saídas específicas de cada provedor no momento da instalação.

Essa separação é deliberada:

- Conteúdo e comportamento vivem uma vez em `agents/`, `commands/`, `skills/`, `templates/` e `scripts/hooks/`.
- Adaptadores de provedor vivem em `scripts/lib/*.json`.
- Os instaladores materializam apenas a árvore de arquivos que cada CLI espera.
- Os hooks chamam os mesmos dispatchers shell independentemente do provedor.

---

## Fonte Canônica

Estes diretórios são a fonte da verdade:

| Caminho | Responsabilidade |
|---------|------------------|
| `agents/` | Prompts de papel e regras comportamentais dos agentes |
| `commands/` | Entrypoints dos commands e prompts de orquestração |
| `skills/` | Instruções compartilhadas e reutilizáveis |
| `templates/` | Templates de saída reutilizáveis |
| `scripts/hooks/` | Dispatchers de hooks de ciclo de vida e helpers |
| `scripts/lib/tiers.json` | Mapeamento de tier para modelo por provedor |
| `scripts/lib/tool-map.json` | Mapeamento de convenções de ferramentas por provedor |
| `scripts/lib/command-map.json` | Mapeamento de commands/entrypoints por provedor |
| `scripts/lib/commands.json` | Metadados dos commands, incluindo tiers |

Nada nesses diretórios-fonte deve ser duplicado por provedor.

---

## Fluxo de Renderização e Instalação

O fluxo interno tem duas fases:

1. `scripts/render-provider.sh` lê a fonte canônica e renderiza artefatos específicos do provedor.
2. O instalador de cada provedor posiciona ou linka esses artefatos onde o CLI espera encontrá-los.

Fluxo em alto nível:

```text
fonte canônica
  -> render-provider.sh
  -> arquivos específicos do provedor
  -> instalador do provedor
  -> integração local ao projeto
```

A etapa de renderização é propositalmente leve: Python puro com biblioteca padrão apenas.

---

## Saídas por Provedor

Cada provedor recebe uma forma diferente, mas com a mesma intenção:

| Provedor | Forma de saída |
|----------|----------------|
| Claude Code | `.claude/agents/`, `.claude/commands/devteam/`, `.claude/skills/`, `.claude/settings.json` |
| opencode | `.opencode/agents/`, `.opencode/skills/`, cola de plugin/runtime |
| Codex | `.codex/agents/*.toml`, `.codex/skills/devteam-*/SKILL.md`, `.codex/hooks.json` |

Ponto-chave: o fonte não é reescrito manualmente para cada CLI. A camada de render/instalação faz essa adaptação.

---

## Commands, Agents e Skills

O harness é dividido em três camadas de orquestração:

| Camada | Propósito |
|--------|-----------|
| Commands | Entrypoints voltados ao usuário como `/devteam:plan` ou `$devteam-plan` |
| Agents | Executores especializados como `backend-developer` ou `technical-writer` |
| Skills | Regras compartilhadas usadas por commands e agents |

É por isso que nomear papéis funciona nos CLIs suportados: os arquivos específicos de cada provedor são renderizados da mesma fonte canônica, então o comportamento permanece alinhado mesmo quando o formato do arquivo muda.

No Codex especificamente, o entrypoint local ao projeto é o caminho por skill gerado `$devteam-<name>` via `.codex/skills/devteam-*/SKILL.md`. Essa skill é apenas orquestração; os agentes renderizados em `.codex/agents/*.toml` são quem aplicam a política de modelo e esforço do lado do provedor.

---

## Tiers de Modelo e Resolução

Commands e agents não fixam modelos de provedor diretamente como fonte principal da verdade. Eles declaram tiers como `reasoning`, `backend-exec`, `frontend` e `repetitive`.

A resolução funciona assim:

| Etapa | Resultado |
|-------|-----------|
| O command ou agent declara um tier | A intenção é expressa de forma neutra ao provedor |
| `tiers.json` mapeia o tier por provedor | O provedor recebe um modelo concreto |
| A renderização/instalação aplica as convenções do provedor | O artefato final carrega a informação correta de modelo |

É assim que um mesmo comportamento pode mapear para modelos concretos diferentes em Claude Code, opencode e Codex sem editar o corpo de cada prompt.

### Seleção de modelo por command

Todo command declara um tier em `scripts/lib/commands.json`.

- Em opencode e Codex, esse tier vira um modelo concreto no momento da instalação.
- Em Claude Code, os corpos dos commands são symlinkados como estão, então a seleção de tier só chega até o command por uma chave `model:` no frontmatter.
- Essa chave `model:` é usada intencionalmente apenas nos commands `repetitive`, como `docs`, `pr`, `push`, `commit`, `learn`, `update`, `symlinks` e `health-check`.

O motivo é controle de custo. Um override `model:` em um command de planejamento substituiria silenciosamente o modelo escolhido na sessão atual. Um override barato em commands repetitivos só pode reduzir custo, nunca aumentá-lo inesperadamente.

---

## Hooks e Runtime Compartilhado

A integração por provedor difere, mas o comportamento de runtime converge para a mesma camada shell:

| Assunto | Implementação compartilhada |
|---------|-----------------------------|
| Início de sessão | `scripts/hooks/session-start.sh` |
| Lógica pré-tool | `scripts/hooks/pre-tool-use/` |
| Lógica de stop/fim de sessão | `scripts/hooks/stop/` |
| Utilitários auxiliares | `scripts/helpers/` e `scripts/lib/` |

A escolha importante de design é que os provedores chamam a mesma lógica de hook em vez de manter implementações duplicadas por CLI.

Isso também explica por que estado do usuário, como preferências, resumos de sessão e credenciais, é documentado como dado de runtime local ao projeto, e não como recurso específico de um provedor.

---

## Por Que Essa Estrutura Existe

Essa estrutura resolve quatro problemas:

- Consistência: o comportamento muda uma vez, não três.
- Portabilidade: um novo provedor precisa basicamente de metadados adaptadores e um instalador.
- Auditabilidade: política de modelo, política de hooks e roteamento de commands ficam centralizados.
- Custo de manutenção: correções aterrissam na fonte canônica em vez de derivarem em múltiplas cópias.

Na prática, Dev Team Agents é menos um pacote de prompts e mais uma camada de tradução entre um sistema autorado uma vez e várias superfícies de execução.

---

## Documentos Relacionados

- [README](../README.pt-BR.md)
- [Notas de Provedores](providers.md)
- [Referência de Agentes](agents.pt-BR.md)
- [Preferências do Usuário](user-preferences.pt-BR.md)
- [Referência de Credentials](credentials.local.pt-BR.md)
