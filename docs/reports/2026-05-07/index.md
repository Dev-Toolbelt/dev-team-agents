# Relatório de Auditoria — `dev-team-agents`

**Data:** 2026-05-07
**Escopo:** Segunda passada de auditoria — áreas não exploradas em 2026-05-06
**Autor:** Tarefa agendada (execução autônoma)
**Tipo:** Auditoria temática — robustez de scripts, consistência de comandos, modelo de agente, novos vetores de economia de tokens
**Estratégia anti-repetição:** Os 22 fingerprints publicados em [`2026-05-06`](../2026-05-06/index.md) foram **excluídos da geração**. Cada sugestão deste relatório recebeu um fingerprint **novo**, registrado em [`docs/reports/_index.md`](../_index.md).

---

## Seções

- [1. Referências e Consistência (Comandos × Documentação × Instalador)](01-referencias-e-consistencia.md)
- [2. Fluxos e Comandos (Phase Gates, Paralelismo, Spawn Condicional)](02-fluxos-e-comandos.md)
- [3. Agentes e Skills (Modelo, Templates, Cobertura)](03-agentes-e-skills.md)
- [4. Economia de Tokens (Vetores Inéditos)](04-economia-tokens.md)
- [5. Robustez de Scripts (Hooks, Instalador, Atualizador)](05-robustez-scripts.md)

---

## Sumário Executivo

A passada anterior cobriu o "panorama" — sincronia README, tamanho de agentes, deduplicação do Foundational Rule. Esta passada **mergulha em camadas mais profundas**: o conteúdo dos comandos (que se mostraram inconsistentes em escopo de worktree e em documentação de `$ARGUMENTS`), a robustez dos scripts shell (faltando o `-e` em `set -uo pipefail` em ambos os dispatchers de hook, sem verificação de integridade SHA256 no `update.sh` e sem timeout em chamadas HTTP) e três novas frentes de economia de tokens (bloco de detecção de contexto repetido em **22 comandos**, prefixo redundante `.claude/agents/dev-team/` em todas as linhas de spawn, e a oportunidade de delegar à Graphify quando disponível).

A descoberta mais relevante operacionalmente é que o **`install.sh` strippa quatro arquivos a mais do tarball do que o `CLAUDE.md` documenta** — uma desincronia sutil que pode confundir contribuintes. A descoberta de maior impacto em qualidade é o **modelo `claude-sonnet-4-6` aplicado ao `setup-assistant`**, que executa decisões pesadas (tipo de projeto, configuração inicial, integração com tracker) e estaria melhor alocado em Opus.

---

## Lista Priorizada de Ações (Hoje)

| Prioridade | Sugestão | Esforço | Impacto |
|------------|----------|---------|---------|
| P0 | Corrigir `set -uo pipefail` → `set -euo pipefail` em ambos os dispatchers de hook | Baixo | Alto (estabilidade) |
| P0 | Atualizar `CLAUDE.md` para listar todos os arquivos efetivamente strippados pelo `install.sh` | Baixo | Médio (clareza para contribuintes) |
| P1 | Trocar `setup-assistant` para Opus | Baixo | Médio (qualidade da decisão de onboarding) |
| P1 | Adicionar timeout (`--connect-timeout 5 --max-time 10`) nas chamadas curl do `01-check-updates.sh` | Baixo | Alto (UX em rede ruim) |
| P1 | Adicionar checagem SHA256 do tarball no `update.sh` | Médio | Alto (segurança da cadeia de suprimento) |
| P1 | Padronizar bloco de "current working context" em todos os comandos via skill comum | Médio | Médio (token e manutenibilidade) |
| P2 | Tornar `database-specialist` condicional em `/devteam:plan` | Baixo | Médio (custo de planos UI-only) |
| P2 | Documentar `$ARGUMENTS` em todos os comandos no padrão de `commit.md` | Médio | Médio (UX do usuário) |
| P2 | `commit.md` deve respeitar a sessão de worktree atual | Baixo | Baixo |
| P2 | Adicionar checkpoint explícito "await all parallel agents" em `inherited-project.md` | Baixo | Baixo |
| P3 | Esclarecer no README que `test-pyramid` e `test-strategy` são complementares (não redundantes) | Baixo | Baixo |
| P3 | Avaliar `comments-policy` como skill universal carregada via `project-context` | Baixo | Baixo |
| P3 | Detecção de Graphify no `project-context` para roteamento token-eficiente | Médio | Médio |

---

## Conclusão

O projeto continua em estado maduro. Esta segunda passada **não encontrou defeitos críticos**, mas identificou três classes de risco que valem atenção: (a) **inconsistência sutil entre código e documentação** (install.sh × CLAUDE.md, comandos com worktree-context divergente), (b) **fragilidade silenciosa em scripts shell** que aparece apenas em condições adversas (rede ruim, falha de extração), e (c) **oportunidades de economia de tokens em duplicações que escapam ao olho** (bloco de worktree repetido 22 vezes, prefixo de path repetido em todas as listas de spawn).

A política de fingerprints continua eficaz: das **20+ sugestões** novas levantadas hoje, **nenhuma** sobrepõe ao registro de 2026-05-06.

---

**Próxima execução agendada:** 2026-05-08 (consultará `_index.md` com 42+ fingerprints registrados — combinação dos 22 de ontem + ~20 de hoje).
